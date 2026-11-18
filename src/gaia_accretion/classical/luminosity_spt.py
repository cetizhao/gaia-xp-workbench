"""光谱型证据积分和联合抽样。"""
import numpy as np
from scipy.special import logsumexp
from .case_fitting import trapezoid_weights

def spt_prior_mass(nodes, center, sigma):
    nodes=np.asarray(nodes,float)
    if nodes.ndim!=1 or not len(nodes) or not np.isfinite(nodes).all() or sigma<=0:
        raise ValueError('光谱型节点与先验宽度非法')
    if len(nodes)==1:return np.ones(1)
    if np.any(np.diff(nodes)<=0):raise ValueError('光谱型节点必须严格递增')
    weight=trapezoid_weights(nodes)*np.exp(-.5*((nodes-center)/sigma)**2)
    return weight/weight.sum()

def joint_mass(grids, prior_mass, zero_prior):
    """返回SpT与零/正分支的联合概率；先验作用于证据，不能平均已归一后验。"""
    prior=np.asarray(prior_mass,float)
    if len(grids)!=len(prior) or np.any(prior<=0) or not np.isclose(prior.sum(),1) or not 0<zero_prior<1:
        raise ValueError('节点/分支先验非法')
    evidence=np.array([[g['logz_zero'],g['logz_positive']] for g in grids])
    log_joint=evidence+np.log(prior[:,None])+np.log([zero_prior,1-zero_prior])
    logz=float(logsumexp(log_joint));mass=np.exp(log_joint-logz)
    return {'mass':mass,'p_zero':float(mass[:,0].sum()),'logz_total':logz,
            'logz_zero':float(logsumexp(evidence[:,0]+np.log(prior))),
            'logz_positive':float(logsumexp(evidence[:,1]+np.log(prior)))}

def sample_joint(model, nodes, contexts, grids, joint, count, seed):
    rng=np.random.default_rng(seed);choice=rng.choice(len(nodes)*2,count,p=joint['mass'].ravel())
    theta=np.empty((count,3));shape=np.empty(count,int);spt=np.asarray(nodes)[choice//2];physical={}
    for i,ctx in enumerate(contexts):
        for branch in (0,1):
            selected=np.flatnonzero(choice==2*i+branch)
            if not len(selected):continue
            theta[selected],shape[selected]=model.draw_grid(ctx,grids[i],len(selected),rng,zero=branch==0)
            values=model.physical_samples(ctx,theta[selected],shape[selected])
            for key,value in values.items():
                if key not in physical:physical[key]=np.empty(count)
                physical[key][selected]=value
    return {'theta':theta,'shape_index':shape,'spt':spt,**physical}
