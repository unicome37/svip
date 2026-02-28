"""
SVIP v1.0 — A3 Weight Engine (组合权重引擎)

W_raw = Q × V × P（质量因子 × 估值因子 × 相位因子）
然后做归一化 + 约束投影（单票/行业/主题桶上限）。
"""
from typing import List, Dict
from config.settings import settings, WeightConfig
from src.models import (
    SVIPStock, SVILevel, ValuationTier, PhaseState, PoolAction,
)


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def quality_factor(svi_score: float, cfg: WeightConfig = None) -> float:
    """SVI → Q 因子 [0, 1]"""
    if cfg is None:
        cfg = settings.weight
    if svi_score <= cfg.q_floor:
        return 0.0
    if svi_score >= cfg.q_ceiling:
        return 1.0
    return (svi_score - cfg.q_floor) / (cfg.q_ceiling - cfg.q_floor)


def compute_raw_weights(stocks: List[SVIPStock], cfg: WeightConfig = None) -> List[SVIPStock]:
    """
    计算原始权重 W_raw = Q × V × P。
    只对 Core 池标的计算。
    """
    if cfg is None:
        cfg = settings.weight

    for s in stocks:
        if s.pool != SVILevel.CORE:
            s.raw_weight = 0.0
            continue

        q = quality_factor(s.svi.total if s.svi else 0, cfg)
        v = s.valuation.valuation_factor if s.valuation else 0.2
        p = s.acceleration.phase_factor if s.acceleration else 1.0
        s.raw_weight = q * v * p

    return stocks


def normalize_weights(
    stocks: List[SVIPStock],
    target_equity: float = 0.75,
) -> List[SVIPStock]:
    """归一化到目标仓位区间"""
    total_raw = sum(s.raw_weight for s in stocks)
    if total_raw <= 0:
        return stocks

    for s in stocks:
        if s.raw_weight > 0:
            s.target_weight = (s.raw_weight / total_raw) * target_equity
        else:
            s.target_weight = 0.0

    return stocks


def apply_constraints(
    stocks: List[SVIPStock],
    cfg: WeightConfig = None,
) -> List[SVIPStock]:
    """
    约束投影：按顺序执行。
    1. 单票上限 8%
    2. 单慢变量桶上限 30%
    3. 单行业上限 25%
    超出部分按比例缩放。
    """
    if cfg is None:
        cfg = settings.weight

    # 约束1：单票上限
    overflow = 0.0
    active_count = sum(1 for s in stocks if 0 < s.target_weight <= cfg.single_stock_max)
    for s in stocks:
        if s.target_weight > cfg.single_stock_max:
            overflow += s.target_weight - cfg.single_stock_max
            s.target_weight = cfg.single_stock_max
    # 溢出部分按比例分配给未超限标的
    if overflow > 0 and active_count > 0:
        for s in stocks:
            if 0 < s.target_weight < cfg.single_stock_max:
                s.target_weight += overflow / active_count

    # 约束2：慢变量桶上限
    _apply_group_cap(stocks, key="theme", cap=cfg.theme_bucket_max)

    # 约束3：行业上限
    _apply_group_cap(stocks, key="sector", cap=cfg.sector_max)

    return stocks


def _apply_group_cap(
    stocks: List[SVIPStock],
    key: str,
    cap: float,
) -> None:
    """对某个分组维度应用上限约束"""
    groups: Dict[str, float] = {}
    for s in stocks:
        group = getattr(s, key, "other")
        groups[group] = groups.get(group, 0) + s.target_weight

    for group, total in groups.items():
        if total > cap:
            ratio = cap / total
            for s in stocks:
                if getattr(s, key, "other") == group:
                    s.target_weight *= ratio


def determine_actions(
    stocks: List[SVIPStock],
    cfg: WeightConfig = None,
) -> List[SVIPStock]:
    """
    根据当前权重与目标权重确定行动。

    建仓/加仓/减仓/退出规则。
    """
    if cfg is None:
        cfg = settings.weight

    for s in stocks:
        if s.pool == SVILevel.BLOCK:
            s.action = PoolAction.EXIT
            continue

        # 无目标权重 → 退出
        if s.target_weight <= 0:
            if s.current_weight > 0:
                s.action = PoolAction.EXIT
            else:
                s.action = PoolAction.HOLD
            continue

        # 估值 C → 退出
        if s.valuation and s.valuation.tier == ValuationTier.C:
            s.action = PoolAction.EXIT if s.current_weight > 0 else PoolAction.HOLD
            continue

        # 衰减期 → 减仓
        if s.acceleration and s.acceleration.phase == PhaseState.DECAYING:
            if s.current_weight > 0:
                s.action = PoolAction.LIGHT_REDUCE
            continue

        # 新建仓
        if s.current_weight <= 0 and s.target_weight > 0:
            s.action = PoolAction.BUILD
            # 首次建仓只买目标的50%
            s.target_weight *= cfg.initial_position_ratio
            continue

        # 加仓条件：加速期 + 估值非C
        diff = s.target_weight - s.current_weight
        if diff > 0.005:  # 偏差 > 0.5% 才加仓
            if s.acceleration and s.acceleration.phase == PhaseState.ACCELERATING:
                s.action = PoolAction.ADD
            else:
                s.action = PoolAction.HOLD
        elif diff < -0.005:
            s.action = PoolAction.LIGHT_REDUCE
        else:
            s.action = PoolAction.HOLD

    return stocks


def compute_portfolio_weights(
    stocks: List[SVIPStock],
    target_equity: float = 0.75,
    macro_risk_factor: float = 1.0,
    tail_risk_factor: float = 1.0,
    cfg: WeightConfig = None,
) -> List[SVIPStock]:
    """
    完整组合权重计算流程。

    1. 计算原始权重 W_raw = Q × V × P
    2. 归一化到目标仓位
    3. 应用宏观/尾部风险修正
    4. 约束投影
    5. 确定行动
    """
    if cfg is None:
        cfg = settings.weight

    # 修正目标仓位
    adjusted_equity = target_equity * macro_risk_factor * tail_risk_factor
    adjusted_equity = clamp(adjusted_equity, 0, cfg.core_pool_max)

    # 流程
    stocks = compute_raw_weights(stocks, cfg)
    stocks = normalize_weights(stocks, adjusted_equity)
    stocks = apply_constraints(stocks, cfg)
    stocks = determine_actions(stocks, cfg)

    return stocks
