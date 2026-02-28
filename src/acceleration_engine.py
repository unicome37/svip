"""
SVIP v1.0 — A2 Acceleration Engine (慢变量加速检测模块)

检测慢变量的"二阶导"——超额收益来自加速期。

代理指标：渗透率、单位成本曲线、资本开支、政策/制度变化
输出：AccelerationScore (0-100) + PhaseState
"""
import numpy as np
from typing import List, Optional
from config.settings import settings, AccelerationConfig
from src.models import AccelerationResult, PhaseState


def compute_growth_rate(series: List[float]) -> float:
    """计算一阶导（增长率），使用最近两期"""
    if len(series) < 2 or series[-2] == 0:
        return 0.0
    return (series[-1] - series[-2]) / abs(series[-2])


def compute_acceleration(series: List[float]) -> float:
    """计算二阶导（加速度），使用最近三期"""
    if len(series) < 3:
        return 0.0
    g1 = (series[-2] - series[-3]) / abs(series[-3]) if series[-3] != 0 else 0
    g2 = (series[-1] - series[-2]) / abs(series[-2]) if series[-2] != 0 else 0
    return g2 - g1


def smooth_series(series: List[float], window: int = 3) -> List[float]:
    """3期移动平均平滑（防噪音）"""
    if len(series) < window:
        return series
    arr = np.array(series)
    kernel = np.ones(window) / window
    smoothed = np.convolve(arr, kernel, mode='valid')
    return smoothed.tolist()


def score_proxy_indicator(
    series: List[float],
    smoothing: int = 3,
) -> float:
    """
    对单个代理指标计算加速度评分 (0-100)。

    正加速度 → 高分（加速期）
    零加速度 → 中分（稳态期）
    负加速度 → 低分（衰减期）
    """
    if len(series) < 3:
        return 50.0  # 数据不足，默认稳态

    smoothed = smooth_series(series, smoothing)
    if len(smoothed) < 3:
        return 50.0

    accel = compute_acceleration(smoothed)
    growth = compute_growth_rate(smoothed)

    # 综合评分：增长率权重40% + 加速度权重60%
    # 增长率映射：-20%→0, 0→50, +20%→100
    growth_score = max(0, min(100, 50 + growth * 250))
    # 加速度映射：-0.1→0, 0→50, +0.1→100
    accel_score = max(0, min(100, 50 + accel * 500))

    return growth_score * 0.4 + accel_score * 0.6


def classify_phase(
    score: float,
    cfg: AccelerationConfig = None,
) -> PhaseState:
    """相位判定"""
    if cfg is None:
        cfg = settings.acceleration
    if score >= cfg.accelerating_threshold:
        return PhaseState.ACCELERATING
    if score >= cfg.steady_threshold:
        return PhaseState.STEADY
    return PhaseState.DECAYING


def compute_acceleration_score(
    symbol: str,
    theme: str = "",
    penetration_series: Optional[List[float]] = None,
    cost_curve_series: Optional[List[float]] = None,
    capex_series: Optional[List[float]] = None,
    policy_series: Optional[List[float]] = None,
    cfg: AccelerationConfig = None,
) -> AccelerationResult:
    """
    计算完整 A2 慢变量加速检测。

    Args:
        symbol: 股票代码
        theme: 慢变量主题桶
        penetration_series: 渗透率时间序列
        cost_curve_series: 单位成本曲线时间序列
        capex_series: 资本开支时间序列
        policy_series: 政策/制度变化时间序列
    """
    if cfg is None:
        cfg = settings.acceleration

    result = AccelerationResult(symbol=symbol, theme=theme)
    smoothing = cfg.smoothing_periods

    # 各代理指标评分
    scores = []
    weights = []

    if penetration_series and len(penetration_series) >= 3:
        result.penetration_score = score_proxy_indicator(penetration_series, smoothing)
        scores.append(result.penetration_score)
        weights.append(cfg.penetration_weight)

    if cost_curve_series and len(cost_curve_series) >= 3:
        # 成本下降是好事，所以反转序列
        inverted = [-x for x in cost_curve_series]
        result.cost_curve_score = score_proxy_indicator(inverted, smoothing)
        scores.append(result.cost_curve_score)
        weights.append(cfg.cost_curve_weight)

    if capex_series and len(capex_series) >= 3:
        result.capex_score = score_proxy_indicator(capex_series, smoothing)
        scores.append(result.capex_score)
        weights.append(cfg.capex_weight)

    if policy_series and len(policy_series) >= 3:
        result.policy_score = score_proxy_indicator(policy_series, smoothing)
        scores.append(result.policy_score)
        weights.append(cfg.policy_weight)

    # 加权平均
    if scores and sum(weights) > 0:
        total_w = sum(weights)
        result.acceleration_score = sum(
            s * w for s, w in zip(scores, weights)
        ) / total_w
    else:
        result.acceleration_score = 50.0  # 无数据默认稳态

    # 相位判定
    result.phase = classify_phase(result.acceleration_score, cfg)

    # 相位因子
    phase_factors = {
        PhaseState.ACCELERATING: cfg.accelerating_factor,
        PhaseState.STEADY: cfg.steady_factor,
        PhaseState.DECAYING: cfg.decaying_factor,
    }
    result.phase_factor = phase_factors[result.phase]

    return result
