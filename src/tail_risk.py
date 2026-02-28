"""
SVIP v1.0 — A7 Tail Risk Module (极端风险与黑天鹅模块)

三类极端风险：
  1. 流动性型（市场冻结、融资收缩）
  2. 制度型（监管突变、牌照失效）
  3. 技术范式型（新技术彻底替代旧结构）

输出：TailRiskFactor (0.6 - 1.0)
危机状态下自动压缩仓位。
"""
from typing import Optional
from config.settings import settings, TailRiskConfig
from src.models import TailRiskResult, TailRiskState


def assess_liquidity_risk(
    vix: Optional[float] = None,
    credit_spread_change: Optional[float] = None,
    cfg: TailRiskConfig = None,
) -> float:
    """
    流动性压力评估 (0-100)。
    VIX > 35 → 紧张；VIX > 45 → 危机
    """
    if cfg is None:
        cfg = settings.tail_risk

    score = 0.0
    if vix is not None:
        if vix >= cfg.vix_crisis:
            score += 80
        elif vix >= cfg.vix_tense:
            score += 60
        elif vix >= cfg.vix_alert:
            score += 40
        else:
            score += 10

    if credit_spread_change is not None:
        # 信用利差急剧扩大（月度变化 > 1%）
        if credit_spread_change > 1.5:
            score += 20
        elif credit_spread_change > 0.5:
            score += 10

    return min(score, 100)


def assess_regime_risk(
    regulatory_intensity: float = 0.0,
) -> float:
    """
    制度风险评估 (0-100)。
    基于监管公告频率异常度。
    """
    return min(max(regulatory_intensity, 0), 100)


def assess_disruption_risk(
    industry_revenue_decline_years: int = 0,
    market_share_erosion: float = 0.0,
) -> float:
    """
    技术替代风险评估 (0-100)。
    行业收入连续负增长 + 市场份额被侵蚀。
    """
    score = 0.0
    if industry_revenue_decline_years >= 3:
        score += 60
    elif industry_revenue_decline_years >= 2:
        score += 30

    score += min(market_share_erosion * 100, 40)
    return min(score, 100)


def determine_tail_risk_state(
    liquidity_risk: float,
    regime_risk: float,
    disruption_risk: float,
) -> TailRiskState:
    """综合判定尾部风险状态"""
    max_risk = max(liquidity_risk, regime_risk, disruption_risk)
    if max_risk >= 70:
        return TailRiskState.CRISIS
    if max_risk >= 50:
        return TailRiskState.TENSE
    if max_risk >= 30:
        return TailRiskState.ALERT
    return TailRiskState.NORMAL


def compute_tail_risk(
    vix: Optional[float] = None,
    credit_spread_change: Optional[float] = None,
    regulatory_intensity: float = 0.0,
    industry_revenue_decline_years: int = 0,
    market_share_erosion: float = 0.0,
    cfg: TailRiskConfig = None,
) -> TailRiskResult:
    """计算完整尾部风险评估"""
    if cfg is None:
        cfg = settings.tail_risk

    result = TailRiskResult()
    result.vix = vix
    result.credit_spread_change = credit_spread_change

    result.liquidity_risk = assess_liquidity_risk(vix, credit_spread_change, cfg)
    result.regime_risk = assess_regime_risk(regulatory_intensity)
    result.disruption_risk = assess_disruption_risk(
        industry_revenue_decline_years, market_share_erosion
    )

    result.state = determine_tail_risk_state(
        result.liquidity_risk, result.regime_risk, result.disruption_risk
    )

    # TailRiskFactor 映射
    factor_map = {
        TailRiskState.NORMAL: cfg.normal_factor,
        TailRiskState.ALERT: cfg.alert_factor,
        TailRiskState.TENSE: cfg.tense_factor,
        TailRiskState.CRISIS: cfg.crisis_factor,
    }
    result.tail_risk_factor = factor_map[result.state]

    return result
