"""单源数值积分；保持既定节点、似然、先验和收敛阈值。"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from gaia_accretion.classical.fang_xp_broad import photo_context
from gaia_accretion.classical.luminosity_spt import joint_mass, spt_prior_mass, sample_joint
from gaia_accretion.classical.luminosity_boundary import zero_mixture_quantiles

def sha256(path):
    with open(path,"rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def infer_supported(model,anchor,center,dest,seed,support):
    dest.mkdir(parents=True,exist_ok=True)
    cache=dest/'grid';cache.mkdir(exist_ok=True)
    contexts={};grids={};checks=[]
    def compute_grid(item):
        key,ctx,path=item
        coarse=model.grid(ctx)
        for refinement in (2,4,8,16,32):
            fine=model.grid(ctx,refinement)
            change=max(abs(fine[z]-coarse[z]) for z in ('logz_zero','logz_positive'))
            if change<.05:break
            coarse=fine
        else:raise RuntimeError(f'r/Av积分未稳定: SpT={ctx.spt}, delta lnZ={change}')
        fine.update(refinement=refinement,grid_log_evidence_change=change)
        np.savez_compressed(path,**fine)
        return key,fine
    for divisions in (32,64,128,256):
        nodes=np.linspace(support[0],support[1],divisions+1)
        jobs=[]
        for sp in nodes:
            key=f'{sp:.7f}'
            if key in grids:continue
            ctx=photo_context(model,anchor,sp);contexts[key]=ctx
            path=cache/f'{key}.npz'
            if path.exists():
                with np.load(path) as z:grids[key]={k:z[k] for k in z.files}
                continue
            jobs.append((key,ctx,path))
        # 一个进程、两个数值工作线程；各BLAS库单线程。未改变节点或似然。
        with ThreadPoolExecutor(max_workers=2) as pool:
            for key,fine in pool.map(compute_grid,jobs):grids[key]=fine
        keys=[f'{sp:.7f}' for sp in nodes];gs=[grids[k] for k in keys]
        prior=spt_prior_mass(nodes,center,.5)
        joint=joint_mass(gs,prior,.5)
        coarse_joint=joint_mass(gs[::2],spt_prior_mass(nodes[::2],center,.5),.5)
        zchange=max(abs(joint[z]-coarse_joint[z]) for z in ('logz_zero','logz_positive'))
        mchange=abs(nodes@joint['mass'].sum(axis=1)-nodes[::2]@coarse_joint['mass'].sum(axis=1))
        checks.append(dict(nodes=len(nodes),maximum_branch_logz_change=zchange,mean_spt_change=mchange,
            max_r_av_logz_change=max(float(g['grid_log_evidence_change']) for g in gs)))
        print('QUADRATURE',dest.name,checks[-1],flush=True)
        if zchange<.05 and mchange<.02:break
    else:raise RuntimeError('SpT积分未稳定')
    contexts=[contexts[k] for k in keys]
    draws=sample_joint(model,nodes,contexts,gs,joint,8000,seed)
    pj={'mass':np.c_[np.zeros(len(nodes)),joint['mass'][:,1]/joint['mass'][:,1].sum()]}
    positive=sample_joint(model,nodes,contexts,gs,pj,8000,seed+100)
    np.savez_compressed(dest/'posterior.npz',**draws,**{'positive_'+k:v for k,v in positive.items()})
    np.savez_compressed(dest/'spt_evidence.npz',nodes=nodes,prior_mass=prior,joint_mass=joint['mass'])
    levels=np.array([.00135,.025,.16,.5,.84,.95,.975,.99865])
    quant=lambda x:np.quantile(x,[.16,.5,.84,.95],method='inverted_cdf').tolist()
    pq={k:zero_mixture_quantiles(positive[k],joint['p_zero']).tolist() for k in ('lacc_over_lstar','facc_w_m2','r_red')}
    shape=positive['shape_index'];p=model.shape_parameters[shape]
    result=dict(p_zero=joint['p_zero'],logz_zero=joint['logz_zero'],logz_positive=joint['logz_positive'],
        log_bayes_factor_positive_over_zero=joint['logz_positive']-joint['logz_zero'],q_quantiles=pq['lacc_over_lstar'],
        interval_levels=levels.tolist(),q_interval_quantiles=zero_mixture_quantiles(positive['lacc_over_lstar'],joint['p_zero'],levels).tolist(),
        spt_quantiles=quant(draws['spt']),physical_quantiles={k:pq[k] if k in pq else quant(draws[k]) for k in ('facc_w_m2','r_red','av_mag','fstar_bol_w_m2')},
        boundary_probabilities_positive=dict(T5000=float(np.mean(p[:,0]==5000)),T11000=float(np.mean(p[:,0]==11000)),
            ne_upper=float(np.mean(p[:,1]==16)),tau20=float(np.mean(p[:,2]==20)),thick_family=float(np.mean(model.shape_family[shape]==1))),
        checks=checks,red_snr=anchor.red_snr,posterior_sha256=sha256(dest/'posterior.npz'))
    return result
