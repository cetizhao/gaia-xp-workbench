"""梯形积分权重。"""
import numpy as np

def trapezoid_weights(values):
    x = np.asarray(values, float)
    if x.ndim != 1 or len(x) < 2 or np.any(np.diff(x) <= 0):
        raise ValueError('积分网格必须递增')
    result = np.r_[np.diff(x)[0], x[2:] - x[:-2], np.diff(x)[-1]] / 2
    return result / result.sum()
