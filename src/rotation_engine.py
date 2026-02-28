"""
SVIP v1.0 — A8 Rotation Engine (慢变量主题轮动)

SVRA = Slow Variable Relative Acceleration
在慢变量桶之间做"结构再分配"，不碰个股。

轮动频率：每季度一次。
"""
import numpy as np
from typing import List, Dict
from config.settings import settings, RotationConfig
from src.models import SVIPStock, RotationSignal, AccelerationResult


def compute_theme_acceleration(
    stocks: List[SVIPStock],
) -> Dict[str, float]:
    """计算每个主题桶的平均 AccelerationScore"""
    theme_scores: Dict[str, List[float]] = {}

    for s in stocks:
        if s.acceleration and s.theme:
            theme_scores.setdefault(s.theme, []).append(
                s.acceleration.acceleration_score
            )

    return {
        theme: np.mean(scores) if scores else 50.0
        for theme, scores in theme_scores.items()
    }


def compute_rotation_signals(
    stocks: List[SVIPStock],
    cfg: RotationConfig = None,
) -> List[RotationSignal]:
    """
    计算慢变量主题轮动信号。

    1. 每个桶计算平均 AccelerationScore
    2. 计算相对强度（Z-score）
    3. 根据 Z 值确定权重调整
    """
    if cfg is None:
        cfg = settings.rotation

    theme_avg = compute_theme_acceleration(stocks)
    if not theme_avg:
        return []

    # 全局均值和标准差
    values = list(theme_avg.values())
    global_mean = np.mean(values)
    global_std = np.std(values) if len(values) > 1 else 1.0
    if global_std < 1e-6:
        global_std = 1.0

    signals = []
    for theme, avg_score in theme_avg.items():
        z = (avg_score - global_mean) / global_std

        # 权重调整
        if z >= cfg.z_strong_positive:
            adj = 0.10
        elif z >= cfg.z_mild_positive:
            adj = 0.05
        elif z <= cfg.z_strong_negative:
            adj = -0.10
        elif z <= cfg.z_mild_negative:
            adj = -0.05
        else:
            adj = 0.0

        signals.append(RotationSignal(
            theme=theme,
            avg_acceleration=round(avg_score, 1),
            z_score=round(z, 2),
            weight_adjustment=adj,
        ))

    return sorted(signals, key=lambda s: s.z_score, reverse=True)
