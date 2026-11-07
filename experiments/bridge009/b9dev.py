import json
import time
from pathlib import Path

import modal

HERE = Path(__file__).parent
app = modal.App("cable-b9dev")
volume = modal.Volume.from_name("cable-data")
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("numpy==2.2.6", "scipy==1.18.1")
         .add_local_file(HERE / "b9lib.py", "/root/b9lib.py")
         .add_local_file(HERE / "b9c3.py", "/root/b9c3.py")
         .add_local_file(HERE / "b9mel.py", "/root/b9mel.py")
         .add_local_file(HERE / "b9confirm.py", "/root/b9confirm.py")
         .add_local_file(HERE / "results" / "c3_folds.json", "/root/c3_folds.json"))

L = dict(n_lags=30, lag0=2, winsor=3.0)
BATCHES = {
    "base": {
        "b5_50": dict(fams=["b5"], pca_k=50, **L),
        "f30": dict(fams=["fine"], pca_k=30, **L),
        "fc7_60": dict(fams=["fine", "cov7"], pca_k=60, **L),
        "fc4_40": dict(fams=["fine", "cov4"], pca_k=40, **L),
        "c7_40": dict(fams=["cov7"], pca_k=40, **L),
        "fc7_60_roi": dict(fams=["fine", "cov7"], pca_k=60, per_roi=True, **L),
        "fc7_60_y64": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", **L),
    },
    "b2": {
        "fc7_60_y64": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", **L),
        "fc7_60_rrr3": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", rrr=3, **L),
        "fc7_60_rrr6": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", rrr=6, **L),
        "fc7_60_rrr12": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", rrr=12, **L),
        "fc7_60_rrr24": dict(fams=["fine", "cov7"], pca_k=60, ykey="Yall", rrr=24, **L),
        "fc7_60_hp005": dict(fams=["fine", "cov7"], pca_k=60, hp=0.005, **L),
        "fc7_60_hp02": dict(fams=["fine", "cov7"], pca_k=60, hp=0.02, **L),
        "fc7_60_lp20": dict(fams=["fine", "cov7"], pca_k=60, lp=0.20, **L),
        "fc7_60_lp10": dict(fams=["fine", "cov7"], pca_k=60, lp=0.10, **L),
        "fc7_100": dict(fams=["fine", "cov7"], pca_k=100, **L),
        "fc7_40": dict(fams=["fine", "cov7"], pca_k=40, **L),
        "fc7b5_60": dict(fams=["fine", "cov7", "b5"], pca_k=60, **L),
        "fc7_60_l40": dict(fams=["fine", "cov7"], pca_k=60, n_lags=40, lag0=2, winsor=3.0),
        "fc7_60_nowin": dict(fams=["fine", "cov7"], pca_k=60, n_lags=30, lag0=2),
        "c7_60": dict(fams=["cov7"], pca_k=60, **L),
        "c4_40": dict(fams=["cov4"], pca_k=40, **L),
        "c47_60": dict(fams=["cov4", "cov7"], pca_k=60, **L),
    },
    "filt": {
        "fc7_hp005_nolp": dict(fams=["fine", "cov7"], pca_k=60, hp=0.005, lp=None, **L),
        "fc7_hp005_lp25": dict(fams=["fine", "cov7"], pca_k=60, hp=0.005, lp=0.25, **L),
        "fc7_hp003_lp15": dict(fams=["fine", "cov7"], pca_k=60, hp=0.003, lp=0.15, **L),
        "fc7_hp002_nolp": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, **L),
        "fc7_nofilt": dict(fams=["fine", "cov7"], pca_k=60, hp=None, lp=None, **L),
        "fc7_hp005_o1": dict(fams=["fine", "cov7"], pca_k=60, hp=0.005, lp=0.15, order=1, **L),
        "c7_hp005_nolp": dict(fams=["cov7"], pca_k=40, hp=0.005, lp=None, **L),
        "f30_hp005_nolp": dict(fams=["fine"], pca_k=30, hp=0.005, lp=None, **L),
        "fc4_hp005_nolp": dict(fams=["fine", "cov4"], pca_k=40, hp=0.005, lp=None, **L),
        "c7_hp005": dict(fams=["cov7"], pca_k=40, hp=0.005, **L),
        "f30_hp005": dict(fams=["fine"], pca_k=30, hp=0.005, **L),
        "fc4_hp005": dict(fams=["fine", "cov4"], pca_k=40, hp=0.005, **L),
    },
    "nf": {
        "nf_fc7_40": dict(fams=["fine", "cov7"], pca_k=40, hp=0.002, lp=None, **L),
        "nf_fc7_80": dict(fams=["fine", "cov7"], pca_k=80, hp=0.002, lp=None, **L),
        "nf_fc7_120": dict(fams=["fine", "cov7"], pca_k=120, hp=0.002, lp=None, **L),
        "nf_fc7_60_w2": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=2, winsor=2.0),
        "nf_fc7_60_l20": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, n_lags=20, lag0=2, winsor=3.0),
        "nf_fc7_60_l38": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, n_lags=38, lag0=2, winsor=3.0),
        "nf_fc7_60_rrr4": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, ykey="Yall", rrr=4, **L),
        "nf_fc7_60_roi": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, per_roi=True, **L),
        "nf_c7_60": dict(fams=["cov7"], pca_k=60, hp=0.002, lp=None, **L),
        "nf_c7_30": dict(fams=["cov7"], pca_k=30, hp=0.002, lp=None, **L),
        "nf_f20": dict(fams=["fine"], pca_k=20, hp=0.002, lp=None, **L),
        "nf_f45": dict(fams=["fine"], pca_k=45, hp=0.002, lp=None, **L),
        "nf_c4_40": dict(fams=["cov4"], pca_k=40, hp=0.002, lp=None, **L),
        "nf_fc4_40": dict(fams=["fine", "cov4"], pca_k=40, hp=0.002, lp=None, **L),
        "nf_f30": dict(fams=["fine"], pca_k=30, hp=0.002, lp=None, **L),
        "nf_c7_40": dict(fams=["cov7"], pca_k=40, hp=0.002, lp=None, **L),
        "nf_b5_30": dict(fams=["b5"], pca_k=30, hp=0.002, lp=None, **L),
        "nf_fc47_80": dict(fams=["fine", "cov4", "cov7"], pca_k=80, hp=0.002, lp=None, **L),
    },
    "phys": {
        "p_fc7": dict(fams=["fine", "cov7"], pca_k=60, hp=0.002, lp=None, **L),
        "p_fc7_slow": dict(fams=["fine", "cov7", "slow"], pca_k=60, hp=0.002, lp=None, **L),
        "p_fc7_slow80": dict(fams=["fine", "cov7", "slow"], pca_k=80, hp=0.002, lp=None, **L),
        "p_slow": dict(fams=["slow"], pca_k=20, hp=0.002, lp=None, **L),
        "p_fc4_slow": dict(fams=["fine", "cov4", "slow"], pca_k=40, hp=0.002, lp=None, **L),
        "p_c7_slow": dict(fams=["cov7", "slow"], pca_k=40, hp=0.002, lp=None, **L),
        "p_f_slow": dict(fams=["fine", "slow"], pca_k=30, hp=0.002, lp=None, **L),
        "p_ecg": dict(fams=["ecg"], pca_k=4, hp=0.002, lp=None, **L),
        "p_eogemg": dict(fams=["eogemg"], pca_k=15, hp=0.002, lp=None, **L),
        "p_fc7_slow_ecg": dict(fams=["fine", "cov7", "slow", "ecg"], pca_k=60, hp=0.002, lp=None, **L),
        "p_fc7_all": dict(fams=["fine", "cov7", "slow", "ecg", "eogemg"], pca_k=60, hp=0.002, lp=None, **L),
    },
    "c2": {
        "c2_cf2_30_l1": dict(fams=["cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf2_30_l2": dict(fams=["cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=2, winsor=3.0),
        "c2_cf1_30": dict(fams=["cf1"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf4_30": dict(fams=["cf4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cc72_40": dict(fams=["cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cc74_40": dict(fams=["cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf2cc72_60": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf2cc74_60": dict(fams=["cf2", "cc7_4"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf4cc74_60": dict(fams=["cf4", "cc7_4"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf124_45": dict(fams=["cf1", "cf2", "cf4"], pca_k=45, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_all_80": dict(fams=["cf2", "cf4", "cc7_2", "cc7_4"], pca_k=80, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cb5_30": dict(fams=["cb5_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c2_cf2cc72_60_nf": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=None, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "c3": {
        "c3_cc72_40": dict(fams=["cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cc72_30": dict(fams=["cc7_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cc74_40": dict(fams=["cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2cc72_60": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2cc74_60": dict(fams=["cf2", "cc7_4"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf4cc74_60": dict(fams=["cf4", "cc7_4"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2cc72_60_nf": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=None, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2_30_nf": dict(fams=["cf2"], pca_k=30, hp=None, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cc72_40_nf": dict(fams=["cc7_2"], pca_k=40, hp=None, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "c3_cf2cc72_60_pa": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0, pca_all=True),
        "c3_cf2cc72_60_l36": dict(fams=["cf2", "cc7_2"], pca_k=60, hp=0.002, lp=None, n_lags=36, lag0=1, winsor=3.0),
    },
    "diag_cov": {
        "d_zpfir": dict(fams=["dc7_zpfir"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "d_zpfir_l2": dict(fams=["dc7_zpfir"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=2, winsor=3.0),
        "d_butter8": dict(fams=["dc7_butter8"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "d_zpbutter": dict(fams=["dc7_zpbutter"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "d_oldc7": dict(fams=["cov7"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "k1": {
        "k_cf2_20": dict(fams=["cf2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2_30": dict(fams=["cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2_45": dict(fams=["cf2"], pca_k=45, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_50": dict(fams=["cf2", "cc7_2"], pca_k=50, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf4_20": dict(fams=["cf4"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf1_20": dict(fams=["cf1"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf24cc72_50": dict(fams=["cf2", "cf4", "cc7_2"], pca_k=50, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2_30_ema": dict(fams=["cf2"], pca_k=30, ema=[20, 60, 150], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_40_ema": dict(fams=["cf2", "cc7_2"], pca_k=40, ema=[20, 60, 150], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2_30_bag": dict(fams=["cf2"], pca_k=30, bags=8, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_40_bag": dict(fams=["cf2", "cc7_2"], pca_k=40, bags=8, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_40_rrr4": dict(fams=["cf2", "cc7_2"], pca_k=40, ykey="Yall", rrr=4, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf2cc72_40_roi": dict(fams=["cf2", "cc7_2"], pca_k=40, per_roi=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cb5_20": dict(fams=["cb5_2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cc74_30": dict(fams=["cc7_4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "rob": {
        "r_cf2_20_g1": dict(fams=["cf2"], pca_k=20, robust=1.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "r_cf2_20_g2": dict(fams=["cf2"], pca_k=20, robust=2.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "r_cf2cc72_40_g1": dict(fams=["cf2", "cc7_2"], pca_k=40, robust=1.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "r_cf2cc72_40_g2": dict(fams=["cf2", "cc7_2"], pca_k=40, robust=2.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "r_cc72_30_g1": dict(fams=["cc7_2"], pca_k=30, robust=1.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "r_cf4cc74_40_g1": dict(fams=["cf4", "cc7_4"], pca_k=40, robust=1.0, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cc72_30": dict(fams=["cc7_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "k_cf4cc74_40": dict(fams=["cf4", "cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "phys2": {
        "q_ecg": dict(fams=["ecg"], pca_k=4, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "q_eogemg": dict(fams=["eogemg"], pca_k=15, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "q_slow": dict(fams=["slow"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "q_ecg_eogemg": dict(fams=["ecg", "eogemg"], pca_k=19, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "q_physall": dict(fams=["ecg", "eogemg", "slow"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "wh": {
        "w_cf2_20_w3": dict(fams=["cf2"], pca_k=20, whiten=0.3, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "w_cf2cc72_40_w3": dict(fams=["cf2", "cc7_2"], pca_k=40, whiten=0.3, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "w_cf2cc72_40_w7": dict(fams=["cf2", "cc7_2"], pca_k=40, whiten=0.7, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "chs": {
        "ch0_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[0, 1, 2, 3, 4, 7, 8, 11, 13, 14, 15, 17, 18, 20, 21, 22, 23, 24], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch1_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[0, 2, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 17, 20, 22, 24, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch2_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 14, 16, 17, 18, 19, 21, 22, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch3_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 17, 18, 19, 20, 22, 23, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch4_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[2, 3, 4, 5, 6, 7, 8, 10, 15, 16, 17, 18, 20, 21, 22, 23, 24, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch5_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[1, 2, 3, 6, 7, 8, 10, 12, 13, 15, 16, 17, 19, 20, 22, 23, 24, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch6_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[0, 1, 2, 4, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 25], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ch7_cf2cc72": dict(fams=["cf2", "cc7_2"], pca_k=40, channels=[0, 1, 2, 4, 5, 8, 10, 12, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23], hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "ma": {
        "ma3_cf2_20": dict(fams=["cf2"], pca_k=20, ma=3, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ma5_cf2_20": dict(fams=["cf2"], pca_k=20, ma=5, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ma3_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, ma=3, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ma5_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, ma=5, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pma3_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, post_ma=3, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pma5_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, post_ma=5, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ma3_cf2cc72_40_l0": dict(fams=["cf2", "cc7_2"], pca_k=40, ma=3, hp=0.002, lp=None, n_lags=31, lag0=0, winsor=3.0),
    },
    "ea": {
        "ea_cf2_20": dict(fams=["ea_cf2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cc72_30": dict(fams=["ea_cc7_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2cc72_40": dict(fams=["ea_cf2", "ea_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf4cc74_40": dict(fams=["ea_cf4", "ea_cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "eamix_cf2_eacc72_40": dict(fams=["cf2", "ea_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "ea2": {
        "rc_cc72_30": dict(fams=["rc_cc7_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "rc_cc72_40": dict(fams=["rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "rc_cc74_30": dict(fams=["rc_cc7_4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2_rc72_40": dict(fams=["ea_cf2", "rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf4_rc74_40": dict(fams=["ea_cf4", "rc_cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea4_cf2cc72_40": dict(fams=["ea4_cf2", "ea4_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea30_cf2cc72_40": dict(fams=["ea30_cf2", "ea30_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf1_20": dict(fams=["ea_cf1"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cb5_20": dict(fams=["ea_cb5_2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2_30": dict(fams=["ea_cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2_12": dict(fams=["ea_cf2"], pca_k=12, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2cc72_60": dict(fams=["ea_cf2", "ea_cc7_2"], pca_k=60, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ea_cf2cc72_25": dict(fams=["ea_cf2", "ea_cc7_2"], pca_k=25, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "eaw_cf2_cf2": dict(fams=["ea_cf2", "cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "fa": {
        "fa_cf2_20": dict(fams=["fa_cf2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf4_20": dict(fams=["fa_cf4"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa1_cf4_25": dict(fams=["fa1_cf4"], pca_k=25, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_cc72_40": dict(fams=["fa_cf2", "ea_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_rc72_40": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf4_rc74_40": dict(fams=["fa_cf4", "rc_cc7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_ea_cf2_30": dict(fams=["fa_cf2", "ea_cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "fa2": {
        "fa_s2_20": dict(fams=["fa_cf2_s2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_s1_20": dict(fams=["fa_cf2_s1"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_h120_20": dict(fams=["fa_cf2_h120"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_h300_20": dict(fams=["fa_cf2_h300"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "faf_cc4_30": dict(fams=["faf_cc4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "faf_cc4_50": dict(fams=["faf_cc4"], pca_k=50, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_faf_40": dict(fams=["fa_cf2", "faf_cc4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_rc72_30": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_rc72_50": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=50, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_rc72_40_roi": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, per_roi=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_cf2_rc72_40_hp0": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, hp=None, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "iaf": {
        "iaf4_20": dict(fams=["iaf_fa4"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "iaf2_20": dict(fams=["iaf_fa2"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "iaf4_rc72_40": dict(fams=["iaf_fa4", "rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "iaf2_rc72_40": dict(fams=["iaf_fa2", "rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "iaf4_fa2_30": dict(fams=["iaf_fa4", "fa_cf2"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "pool": {
        "pl_fa_rc72_40": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_fa_cc72_40": dict(fams=["fa_cf2", "ea_cc7_2"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_ea_rc72_40": dict(fams=["ea_cf2", "rc_cc7_2"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_fa4_rc74_40": dict(fams=["fa_cf4", "rc_cc7_4"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_fa_s2_20": dict(fams=["fa_cf2_s2"], pca_k=20, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_ea_cc72_40": dict(fams=["ea_cf2", "ea_cc7_2"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_fa1_cf4_25": dict(fams=["fa1_cf4"], pca_k=25, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_ea_cf4cc74_40": dict(fams=["ea_cf4", "ea_cc7_4"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_cf4cc74_40": dict(fams=["cf4", "cc7_4"], pca_k=40, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_cf2_20": dict(fams=["cf2"], pca_k=20, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pl_cc72_30": dict(fams=["cc7_2"], pca_k=30, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "fm": {
        "lab4_20": dict(fams=["lab4"], pca_k=20, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "lab4_40": dict(fams=["lab4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "lab8_30": dict(fams=["lab8"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ealab4_30": dict(fams=["ea_lab4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "lab4_fa_40": dict(fams=["lab4", "fa_cf2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "ealab4_rc72_40": dict(fams=["ea_lab4", "rc_cc7_2"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "lab48_40": dict(fams=["lab4", "lab8"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "f3": {
        "ap4_15": dict(fams=["ap4"], pca_k=15, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "aec_30": dict(fams=["aec7_4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "eaaec_30": dict(fams=["ea_aec7_4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_ap_30": dict(fams=["fa_cf2", "ap4"], pca_k=30, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_rc_ap_40": dict(fams=["fa_cf2", "rc_cc7_2", "ap4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_eaaec_40": dict(fams=["fa_cf2", "ea_aec7_4"], pca_k=40, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "fa_rc_eaaec_50": dict(fams=["fa_cf2", "rc_cc7_2", "ea_aec7_4"], pca_k=50, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
    "pooldg": {
        "pd_fa_rc72_40": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, pool_dg=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pd_fa_cc72_40": dict(fams=["fa_cf2", "ea_cc7_2"], pca_k=40, pool_dg=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pd_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, pool_dg=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pd_cf2_20": dict(fams=["cf2"], pca_k=20, pool_dg=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pde_fa_rc72_40": dict(fams=["fa_cf2", "rc_cc7_2"], pca_k=40, pool_dg=True, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pde_fa_cc72_40": dict(fams=["fa_cf2", "ea_cc7_2"], pca_k=40, pool_dg=True, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pde_cf2cc72_40": dict(fams=["cf2", "cc7_2"], pca_k=40, pool_dg=True, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
        "pde_cf2_20": dict(fams=["cf2"], pca_k=20, pool_dg=True, pool_ext=True, hp=0.002, lp=None, n_lags=30, lag0=1, winsor=3.0),
    },
}


@app.function(image=image, cpu=16.0, memory=98304, timeout=7200, volumes={"/evidence": volume}, max_containers=60)
def run_cfg(name: str, cfg: dict) -> dict:
    import numpy as np
    import b9lib
    t0 = time.time()
    runs = [r for r in b9lib.load_cache() if r["sub"] not in b9lib.NB_TEST_SUBS]
    subs = sorted({r["sub"] for r in runs})
    if cfg.get("pool_ext"):
        import b9c3
        allowed = set(json.loads(Path("/root/c3_folds.json").read_text())["runs"])
        for r in b9c3.load_ext("v26_"):
            if r["run"] in allowed:
                r["sub"] = "ext_" + r["sub"]; r["run"] = "ext_" + r["run"]; r["extra"] = True
                r["Yall"] = r["Y7"]
                runs.append(r)
    if cfg.get("pool_dg"):
        import numpy as np
        for f in sorted(Path("/evidence/bridge009/dg").glob("*.npz")):
            z = np.load(f)
            if z["valid"].mean() < 0.5:
                continue
            r = {k: z[k] for k in z.files}
            r["run"] = "dg_" + f.stem; r["sub"] = "dg_" + f.stem.split("_")[0]; r["extra"] = True; r["Yall"] = r["Y7"]
            runs.append(r)
    preds = b9lib.loso_dev(runs, cfg, subs, ykey=cfg.get("ykey", "Y7"))
    preds = {k: v for k, v in preds.items() if not k.startswith(("ext_", "dg_"))}
    out = Path("/evidence/bridge009/dev"); out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"{name}.npz", **{f"{k}__{f}": v[f] for k, v in preds.items() for f in ("P", "Y", "rows")})
    volume.commit()
    sc = b9lib.score(preds)
    alphas = sorted({str(v["alpha"]) for v in preds.values()})
    return {"name": name, "cfg": cfg, **sc, "alphas": alphas, "sec": round(time.time() - t0, 1)}


@app.function(image=image, cpu=2.0, memory=8192, timeout=1200, volumes={"/evidence": volume})
def eval_ens(members: list, weights: list = None) -> dict:
    import numpy as np
    import b9lib
    volume.reload()
    pl = []
    for m in members:
        z = np.load(f"/evidence/bridge009/dev/{m}.npz")
        d = {}
        for key in z.files:
            run, f = key.split("__"); d.setdefault(run, {})[f] = z[key]
        pl.append(d)
    common = set.intersection(*[set(p) for p in pl])
    pl = [{k: p[k] for k in common} for p in pl]
    return {"name": "ENS[" + "+".join(members) + "]", **b9lib.score(b9lib.ensemble(pl, weights))}


@app.function(image=image, cpu=2.0, memory=8192, timeout=1200, volumes={"/evidence": volume})
def eval_stack(members: list) -> dict:
    import numpy as np
    from scipy.optimize import nnls
    import b9lib
    volume.reload()
    pl = []
    for m in members:
        z = np.load(f"/evidence/bridge009/dev/{m}.npz"); d = {}
        for key in z.files:
            run, f = key.split("__"); d.setdefault(run, {})[f] = z[key]
        pl.append(d)
    runs = sorted(set.intersection(*[set(p) for p in pl]))
    Z = {}
    for r in runs:
        n = min(len(p[r]["P"]) for p in pl)
        Z[r] = (np.stack([b9lib._zs(p[r]["P"][:n]) for p in pl], 2), b9lib._zs(pl[0][r]["Y"][:n]))
    out, W_all = {}, []
    for r in runs:
        s = r.split("-scan")[0]
        oth = [q for q in runs if q.split("-scan")[0] != s]
        P = np.zeros_like(Z[r][1])
        for j in range(7):
            A = np.concatenate([Z[q][0][:, j, :] for q in oth]); b = np.concatenate([Z[q][1][:, j] for q in oth])
            w, _ = nnls(A, b); W_all.append(w / (w.sum() + 1e-9))
            P[:, j] = Z[r][0][:, j, :] @ w
        out[r] = {"P": P, "Y": Z[r][1], "rows": pl[0][r]["rows"]}
    return {"name": "STACK[" + "+".join(members) + "]", **b9lib.score(out),
            "mean_weights": np.round(np.mean(W_all, 0), 3).tolist()}


@app.function(image=image, cpu=2.0, memory=8192, timeout=1200, volumes={"/evidence": volume})
def causality_test(cfg: dict) -> dict:
    import numpy as np
    import b9lib
    runs = b9lib.load_cache({"sub06-scan01"})
    r = runs[0]; t = 700
    f1 = b9lib.featurize(r, cfg)
    r2 = dict(r)
    for fam in cfg["fams"]:
        x = r[fam].copy(); x[t + 1:] += np.random.default_rng(0).normal(0, 5, x[t + 1:].shape).astype(x.dtype); r2[fam] = x
    f2 = b9lib.featurize(r2, cfg)
    V = np.random.default_rng(1).normal(size=(f1.shape[1], 10))
    z1 = b9lib.lag_design(b9lib.causal_zs(f1 @ V), range(2, 32)); z2 = b9lib.lag_design(b9lib.causal_zs(f2 @ V), range(2, 32))
    return {"feat_maxdiff_upto_t": float(np.abs(f1[:t + 1] - f2[:t + 1]).max()),
            "design_maxdiff_upto_t": float(np.abs(z1[:t + 1] - z2[:t + 1]).max()),
            "feat_maxdiff_after_t": float(np.abs(f1[t + 1:] - f2[t + 1:]).max())}


@app.local_entrypoint()
def main(batch: str = "", ens: str = "", stack: str = "", test: bool = False):
    log = HERE / "results" / "dev_log.jsonl"; log.parent.mkdir(exist_ok=True)
    if test:
        print(causality_test.remote(dict(fams=["fine", "cov7", "b5"])))
    res = []
    if batch:
        items = list(BATCHES[batch].items())
        res += [r for r in run_cfg.starmap(items, return_exceptions=True)]
    if ens:
        for group in ens.split(";"):
            res.append(eval_ens.remote(group.split(",")))
    if stack:
        for group in stack.split(";"):
            res.append(eval_stack.remote(group.split(",")))
    with log.open("a", encoding="utf-8") as fh:
        for r in res:
            if isinstance(r, dict):
                r["logged"] = time.strftime("%Y-%m-%d %H:%M"); fh.write(json.dumps(r) + "\n")
                print(f"{r['name']:<40} {r['mean']:.4f}  roi {r['by_roi']}")
            else:
                print("ERROR", repr(r)[:400])
