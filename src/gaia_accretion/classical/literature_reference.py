"""作者 slab 原表读取与单位约定。"""
import re
from pathlib import Path
import numpy as np

def slab_file(path):
    a = np.loadtxt(path, skiprows=9)
    # 作者ASCII在区间拼接处有完全相同的重复行；去重不改变梯形积分。
    duplicate = np.diff(a[:,0]) == 0
    if np.any(duplicate):
        np.testing.assert_array_equal(a[:-1][duplicate], a[1:][duplicate])
        a = a[np.r_[True, ~duplicate]]
    if np.any(np.diff(a[:,0]) <= 0) or np.any(a[:,1] < 0):
        raise ValueError(f'slab原表格式异常: {path}')
    pattern = r'continuum_tot_T(\d+)_ne(.+)tau(.+)\.out'
    t, ne, tau = re.fullmatch(pattern, Path(path).name).groups()
    return a[:,0], a[:,1], (float(t), np.log10(float(ne)), float(tau))
