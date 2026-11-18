"""含精确零分支的后验分位数。"""
import numpy as np

def zero_mixture_quantiles(positive_values, p_zero, levels=(.16, .5, .84, .95)):
    """精确保留已积分的零概率；正分支分位数仍有有限抽样误差。"""
    values = np.asarray(positive_values, float)
    if not 0 <= p_zero <= 1 or not len(values) or np.any(values <= 0) or not np.isfinite(values).all():
        raise ValueError('需要严格正的条件样本及合法零概率')
    answer = np.zeros(len(levels))
    levels = np.asarray(levels)
    mask = levels > p_zero
    if mask.any():
        answer[mask] = np.quantile(values, (levels[mask]-p_zero)/(1-p_zero), method='inverted_cdf')
    return answer
