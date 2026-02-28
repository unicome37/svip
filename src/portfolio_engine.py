"""
SVIP v1.0 — Portfolio Engine (组合编排引擎)

整合所有模块：SVI → A1 → A2 → A3 → A4 → A7 → A8
输出完整的 PortfolioAllocation。
"""
from typing import List, Optional, Dict
from datetime import datetime

from config.settings import settings
from src.models import (
    SVIPStock, SVILevel, PortfolioAllocation, MacroState,
    TailRiskResult, RotationSignal, SVIPReport,
)
from src.weight_engine import compute_portfolio_weights
from src.rotation_engine import compute_rotation_signals


def classify_pools(stocks: List[SVIPStock]) -> tuple[list, list, list]:
    """将股票分入 Core / Watch / Block 池"""
    core, watch, block = [], [], []
    for s in stocks:
        if s.svi is None:
            block.append(s)
            continue

        # 池分类规则
        svi_level = s.svi.level
        val_tier = s.valuation.tier if s.valuation else None
        phase = s.acceleration.phase if s.acceleration else None

        if (svi_level == SVILevel.CORE
                and val_tier != "C"
                and phase != "decaying"):
            s.pool = SVILevel.CORE
            core.append(s)
        elif svi_level in (SVILevel.CORE, SVILevel.WATCH):
            s.pool = SVILevel.WATCH
            watch.append(s)
        else:
            s.pool = SVILevel.BLOCK
            block.append(s)

    return core, watch, block


def determine_cash_level(
    stocks: List[SVIPStock],
) -> float:
    """根据市场状态确定现金水平"""
    cfg = settings.weight

    # 统计 ValuationTier=A 的标的数量
    tier_a_count = sum(
        1 for s in stocks
        if s.valuation and s.valuation.tier.value == "A"
        and s.pool == SVILevel.CORE
    )

    # 统计加速期标的
    accel_count = sum(
        1 for s in stocks
        if s.acceleration and s.acceleration.phase.value == "accelerating"
        and s.pool == SVILevel.CORE
        and (s.valuation is None or s.valuation.tier.value != "C")
    )

    # 统计估值脆弱标的
    tier_c_ratio = 0.0
    total = len([s for s in stocks if s.svi and s.svi.level == SVILevel.CORE])
    if total > 0:
        tier_c_count = sum(
            1 for s in stocks
            if s.valuation and s.valuation.tier.value == "C"
        )
        tier_c_ratio = tier_c_count / total

    # 现金规则
    if tier_c_ratio > 0.6:
        return cfg.cash_high_when_all_c  # 30%
    if tier_a_count < 6:
        return cfg.cash_high_when_few_a  # 20%
    if accel_count >= 4:
        return cfg.cash_low_when_accel   # 10%
    return 0.15  # 默认 15%


def check_violations(
    allocation: PortfolioAllocation,
) -> List[str]:
    """检查组合违规"""
    violations = []
    cfg = settings.weight

    # 总仓位检查
    if allocation.total_equity > allocation.final_equity_ceiling + 0.01:
        violations.append(
            f"⚠️ 总仓位 {allocation.total_equity:.0%} 超过上限 "
            f"{allocation.final_equity_ceiling:.0%}"
        )

    # 主题暴露检查
    for theme, weight in allocation.theme_exposure.items():
        if weight > cfg.theme_bucket_max + 0.01:
            violations.append(
                f"⚠️ 主题 [{theme}] 暴露 {weight:.0%} 超过上限 "
                f"{cfg.theme_bucket_max:.0%}"
            )

    # 行业暴露检查
    for sector, weight in allocation.sector_exposure.items():
        if weight > cfg.sector_max + 0.01:
            violations.append(
                f"⚠️ 行业 [{sector}] 暴露 {weight:.0%} 超过上限 "
                f"{cfg.sector_max:.0%}"
            )

    # 单票检查
    for s in allocation.stocks:
        if s.target_weight > cfg.single_stock_max + 0.01:
            violations.append(
                f"⚠️ {s.symbol} 权重 {s.target_weight:.1%} 超过单票上限 "
                f"{cfg.single_stock_max:.0%}"
            )

    return violations


def build_allocation(
    stocks: List[SVIPStock],
    macro: Optional[MacroState] = None,
    tail_risk: Optional[TailRiskResult] = None,
) -> PortfolioAllocation:
    """
    构建完整组合配置。

    完整流程：
    1. 分池（Core / Watch / Block）
    2. 确定现金水平
    3. 计算目标权重（含宏观/尾部风险修正）
    4. 计算暴露
    5. 违规检查
    """
    # 1. 分池
    core, watch, block = classify_pools(stocks)

    # 2. 现金水平
    cash_level = determine_cash_level(stocks)
    target_equity = 1.0 - cash_level

    # 3. 宏观/尾部风险因子
    mrf = macro.macro_risk_factor if macro else 1.0
    trf = tail_risk.tail_risk_factor if tail_risk else 1.0

    # 4. 计算权重
    all_stocks = core + watch  # Block 不参与权重计算
    all_stocks = compute_portfolio_weights(
        all_stocks,
        target_equity=target_equity,
        macro_risk_factor=mrf,
        tail_risk_factor=trf,
    )

    # 5. 汇总
    allocation = PortfolioAllocation(
        timestamp=datetime.now(),
        stocks=all_stocks + block,
        macro=macro,
        tail_risk=tail_risk,
        macro_risk_factor=mrf,
        tail_risk_factor=trf,
    )

    # 计算暴露
    allocation.total_equity = sum(s.target_weight for s in all_stocks)
    allocation.cash_weight = 1.0 - allocation.total_equity
    allocation.core_pool_weight = sum(
        s.target_weight for s in all_stocks if s.pool == SVILevel.CORE
    )
    allocation.watch_pool_weight = sum(
        s.target_weight for s in all_stocks if s.pool == SVILevel.WATCH
    )
    allocation.final_equity_ceiling = target_equity * mrf * trf

    # 主题暴露
    for s in all_stocks:
        if s.theme and s.target_weight > 0:
            allocation.theme_exposure[s.theme] = (
                allocation.theme_exposure.get(s.theme, 0) + s.target_weight
            )
    # 行业暴露
    for s in all_stocks:
        if s.sector and s.target_weight > 0:
            allocation.sector_exposure[s.sector] = (
                allocation.sector_exposure.get(s.sector, 0) + s.target_weight
            )

    # 6. 违规检查
    allocation.violations = check_violations(allocation)

    return allocation


def generate_report(
    stocks: List[SVIPStock],
    macro: Optional[MacroState] = None,
    tail_risk: Optional[TailRiskResult] = None,
    market: str = "US",
) -> SVIPReport:
    """生成完整 SVIP 报告"""
    allocation = build_allocation(stocks, macro, tail_risk)
    rotation_signals = compute_rotation_signals(stocks)

    core = [s for s in allocation.stocks if s.pool == SVILevel.CORE]
    watch = [s for s in allocation.stocks if s.pool == SVILevel.WATCH]

    return SVIPReport(
        timestamp=datetime.now(),
        market=market,
        core_pool=core,
        watch_pool=watch,
        allocation=allocation,
        rotation_signals=rotation_signals,
        macro=macro,
        tail_risk=tail_risk,
    )
