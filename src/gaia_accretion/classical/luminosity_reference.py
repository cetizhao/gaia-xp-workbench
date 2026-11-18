"""作者 slab 网格与已核验的联合连续谱积分。"""
from functools import lru_cache
from itertools import product
import numpy as np
from scipy.special import gammaln, logsumexp, stdtr
from gaia_accretion.assets import asset_path
from gaia_accretion.accretion_slab_v2 import compute_slab_spectrum
from .literature_reference import slab_file
from .case_fitting import trapezoid_weights
from .luminosity import LuminosityModel

@lru_cache(maxsize=1)
def author_library():
    """作者非均匀网格用参数单元体积积分；保留原20%厚slab支持。"""
    raw=asset_path('slab_grid')
    paths=sorted(raw.glob('*.out'))
    if len(paths)!=1620:raise ValueError('作者网格不完整')
    records=[slab_file(p) for p in paths]
    wave=records[0][0]
    if not all(np.array_equal(wave,r[0]) for r in records):raise ValueError('作者波长网格不一致')
    params=np.array([r[2] for r in records])
    weights=np.ones(len(records))
    for dim in range(3):
        values=np.unique(params[:,dim]);x=np.log10(values) if dim==2 else values
        weights *= trapezoid_weights(x)[np.searchsorted(values,params[:,dim])]
    weights=.8*weights/weights.sum()
    flux=[r[1]*.001 for r in records]
    extension=list(product([5000.,7000.,9000.,10000.],[11.,13.,15.],[10.,20.]))
    for t,n,tau in extension:
        flux.append(compute_slab_spectrum(wave,t,n,tau)*.01)
    params=np.r_[params,np.asarray(extension)]
    weights=np.r_[weights,np.full(len(extension),.2/len(extension))]
    return wave,np.asarray(flux),params,weights,np.r_[np.zeros(1620,int),np.ones(len(extension),int)]

class ReferenceLuminosityModel(LuminosityModel):
    """保留零/正吸积混合、共同尺度积分与作者 slab 先验。"""
    def make_context(self,*args,**kwargs):
        # 保留既定5%特征误差近似，不人为放大到能覆盖文献值。
        self._quadratic_cache.clear()
        return LuminosityModel.make_context(self,*args,**kwargs)

    def grid(self,context,refinement=1):
        cfg=self.settings['grid']
        av=np.linspace(context.av_nodes[0],context.av_nodes[-1],(cfg['av_nodes']-1)*refinement+1)
        lr=np.linspace(*self.logr_bounds,(cfg['r_nodes']-1)*refinement+1)
        aw=trapezoid_weights(av)*np.exp(-.5*(av/self.sigma_av)**2);aw/=aw.sum()
        rw=trapezoid_weights(lr)
        photo=self.interpolate_nodes(context.av_nodes,context.photo_nodes,av)
        cache_key=(id(context.slab_nodes),id(context.precision),refinement)
        if cache_key not in self._quadratic_cache:
            slab=self.interpolate_nodes(context.av_nodes,context.slab_nodes,av)
            sp=slab@context.precision
            self._quadratic_cache[cache_key]=(slab,np.sum(sp*slab,axis=2),sp@context.observed)
        slab,c,v=self._quadratic_cache[cache_key]
        pp=photo@context.precision
        a=np.sum(pp*photo,axis=1);b=np.einsum('ni,nki->nk',pp,slab);u=pp@context.observed
        alpha=1/(1+10**lr);beta=1-alpha;df=self.nu+len(self.indices)-1
        log_pdf_zero=gammaln((df+1)/2)-gammaln(df/2)-.5*np.log(df*np.pi)
        oq=context.observed@context.precision@context.observed
        answers=[]
        for start in range(0,len(av),4):
            ix=slice(start,start+4)
            norm=a[ix,None,None]*alpha[None,:,None]**2+2*b[ix,None,:]*(alpha*beta)[None,:,None]+c[ix,None,:]*beta[None,:,None]**2
            cross=u[ix,None,None]*alpha[None,:,None]+v[ix,None,:]*beta[None,:,None]
            center=cross/norm;minimum=np.maximum(oq-cross**2/norm,0.)
            width=np.sqrt((self.nu+minimum)/(norm*df))
            low=(self.amplitude_bounds[0]-center)/width;high=(self.amplitude_bounds[1]-center)/width
            mass=np.ones_like(low)
            # 两端均超过30个尺度时，省略CDF的绝对误差上界为2*t_cdf(-30)。
            needed=(low>-30)|(high<30)
            right=needed & (low>0);left=needed & ~right
            mass[right]=stdtr(df,-low[right])-stdtr(df,-high[right])
            mass[left]=stdtr(df,high[left])-stdtr(df,low[left])
            ll=context.log_normalization-(df+1)/2*np.log1p(minimum/self.nu)+np.log(width)-log_pdf_zero+np.log(np.maximum(mass,np.finfo(float).tiny))-np.log(self.amplitude_bounds[1])
            answers.append(logsumexp(ll+self.shape_log_prior,axis=2))
        lm=np.concatenate(answers)+np.log(aw[:,None]*rw)
        zp=float(logsumexp(lm))
        z=self.amplitude_distribution(context,np.zeros(len(av)),av,zero=True)[0][:,0]+np.log(aw)
        zz=float(logsumexp(z));prior=self.settings['zero_prior_weight']
        total=np.logaddexp(np.log(prior)+zz,np.log1p(-prior)+zp)
        lx,dv=np.meshgrid(lr,av)
        return dict(points=np.c_[lx.ravel(),dv.ravel()],weight=np.exp(lm.ravel()-zp),av_zero=av,
                    weight_zero=np.exp(z-zz),logz_positive=zp,logz_zero=zz,p_zero=float(np.exp(np.log(prior)+zz-total)))

    def draw_grid(self,context,grid,count,rng,zero=False):
        if not count:return np.empty((0,3)),np.empty(0,int)
        batches=[LuminosityModel.draw_grid(self,context,grid,min(192,count-i),rng,zero=zero) for i in range(0,count,192)]
        return np.concatenate([b[0] for b in batches]),np.concatenate([b[1] for b in batches])

    def amplitude_distribution(self,context,logr,delta,zero=False):
        """重复消光节点先合并，再展开二次型；与原尺度积分代数等价。"""
        av,index=np.unique(delta,return_inverse=True)
        photo=self.interpolate_nodes(context.av_nodes,context.photo_nodes,av)
        pp=photo@context.precision
        a=np.sum(pp*photo,axis=1);u=pp@context.observed
        if zero:
            norm=a[index,None];cross=u[index,None]
        else:
            slab=self.interpolate_nodes(context.av_nodes,context.slab_nodes,av)
            sp=slab@context.precision
            b=np.einsum('ni,nki->nk',pp,slab);c=np.sum(sp*slab,axis=2);v=sp@context.observed
            alpha=1/(1+10**np.asarray(logr));beta=1-alpha
            norm=a[index,None]*alpha[:,None]**2+2*b[index]*(alpha*beta)[:,None]+c[index]*beta[:,None]**2
            cross=u[index,None]*alpha[:,None]+v[index]*beta[:,None]
        center=cross/norm
        minimum=np.maximum(context.observed@context.precision@context.observed-cross**2/norm,0.)
        df=self.nu+len(self.indices)-1;width=np.sqrt((self.nu+minimum)/(norm*df))
        low,high=(self.amplitude_bounds[:,None,None]-center)/width
        right=low>0;mass=np.empty_like(low)
        mass[right]=stdtr(df,-low[right])-stdtr(df,-high[right])
        mass[~right]=stdtr(df,high[~right])-stdtr(df,low[~right])
        log_pdf_zero=gammaln((df+1)/2)-gammaln(df/2)-.5*np.log(df*np.pi)
        ll=context.log_normalization-(df+1)/2*np.log1p(minimum/self.nu)+np.log(width)-log_pdf_zero+np.log(np.maximum(mass,np.finfo(float).tiny))-np.log(self.amplitude_bounds[1])
        return ll,center,width,low,high

    def physical_samples(self,*args,**kwargs):
        result=LuminosityModel.physical_samples(self,*args,**kwargs)
        result['facc_w_m2']=result.pop('facc_50_2500nm_w_m2')
        return result

    def spectrum(self,context,theta,shape_index):
        from gaia_accretion.support.p2.templates import apply_ccm89_extinction
        lr,dv,amp=theta;av=context.base_av+dv;r=10**lr
        photo=apply_ccm89_extinction(self.wave,self.photosphere(context.spt),av,self.rv)['flux']
        photo/=photo@self.projection[:,0]
        slab=np.zeros_like(photo)
        if shape_index>=0:
            ext=apply_ccm89_extinction(self.dense_wave,self.dense_slab[shape_index],av,self.rv)['flux']
            slab=self.response@ext;slab/=slab@self.projection[:,0]
        scale=context.flux_unit*amp/(1+r)
        return photo*scale,slab*scale*r
