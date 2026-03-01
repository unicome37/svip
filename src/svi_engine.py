"""
SVIP v1.0 — SVI Engine (Slow Variable Index)

SVI = 慢变量绑定度指数
基于10年财务数据的结构质量筛选。

Step 1: 硬筛选（ROIC、FCF、毛利稳定性、负债）
Step 2: 多维评分（7个维度加权）
Step 3: 分级（Core / Watch / Block）
"""
import numpy as np
from typing import Optional, Dict
from config.settings import settings, SVIConfig, MARKET_PARAMS
from src.models import SVIScore, SVILevel


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def hard_screen(
    roic_10y_median: float,
    fcf_conversion: float,
    gross_margin_std: float,
    debt_to_equity: float,
    cfg: SVIConfig = None,
) -> bool:
    """
    硬筛选：必须全部满足才能进入评分阶段。
    过滤掉周期股、商品股、高杠杆依赖型公司。
    """
    if cfg is None:
        cfg = settings.svi
    return (
        roic_10y_median >= cfg.roic_10y_min
        and fcf_conversion >= cfg.fcf_conversion_min
        and gross_margin_std <= cfg.gross_margin_volatility_max
        and debt_to_equity <= cfg.debt_to_equity_max
    )


def score_roic(roic_10y_median: float) -> float:
    """ROIC稳定度评分 (0-100)：高且稳定→得分高"""
    if roic_10y_median <= 0.10:
        return 0.0
    if roic_10y_median >= 0.35:
        return 100.0
    return clamp((roic_10y_median - 0.10) / (0.35 - 0.10) * 100)


def score_fcf(fcf_conversion: float) -> float:
    """FCF转化率评分 (0-100)：真实现金流才算慢变量"""
    if fcf_conversion <= 0.5:
        return 0.0
    if fcf_conversion >= 1.0:
        return 100.0
    return clamp((fcf_conversion - 0.5) / (1.0 - 0.5) * 100)


def score_margin_stability(gross_margin_std: float) -> float:
    """毛利稳定性评分 (0-100)：波动越小越好"""
    if gross_margin_std <= 0.01:
        return 100.0
    if gross_margin_std >= 0.15:
        return 0.0
    return clamp((1 - (gross_margin_std - 0.01) / (0.15 - 0.01)) * 100)


def score_concentration(market_share: float, cr4: float = 0.0) -> float:
    """行业集中度评分 (0-100)：寡头加分"""
    share_score = clamp(market_share / 0.30 * 100)
    cr4_score = clamp(cr4 / 0.80 * 100)
    return (share_score * 0.5 + cr4_score * 0.5)


def score_moat(moat_rating: float) -> float:
    """网络/牌照壁垒评分 (0-100)：直接输入评分"""
    return clamp(moat_rating)


def score_demand_rigidity(rigidity_rating: float) -> float:
    """需求刚性评分 (0-100)：直接输入评分"""
    return clamp(rigidity_rating)


def score_substitution_risk(risk_rating: float) -> float:
    """替代风险评分 (0-100)：风险越低分越高（反向）"""
    return clamp(100 - risk_rating)


def classify_svi(total: float, cfg: SVIConfig = None, market: str = "US") -> SVILevel:
    """SVI 分级（支持跨市场阈值）"""
    if cfg is None:
        cfg = settings.svi
    mp = MARKET_PARAMS.get(market)
    core_thresh = mp.svi_threshold if mp else cfg.core_threshold
    if total >= core_thresh:
        return SVILevel.CORE
    if total >= cfg.watch_threshold:
        return SVILevel.WATCH
    return SVILevel.BLOCK


def compute_svi(
    symbol: str,
    market: str,
    roic_10y_median: float,
    fcf_conversion: float,
    gross_margin_std: float,
    debt_to_equity: float,
    market_share: float = 0.0,
    cr4: float = 0.0,
    moat_rating: float = 50.0,
    demand_rigidity_rating: float = 50.0,
    substitution_risk_rating: float = 50.0,
    cfg: SVIConfig = None,
) -> SVIScore:
    """
    计算完整 SVI 慢变量指数。

    Args:
        symbol: 股票代码
        market: 市场 (US/HK/CN)
        roic_10y_median: 10年ROIC中位数
        fcf_conversion: FCF/净利润
        gross_margin_std: 毛利率标准差
        debt_to_equity: 资产负债率
        market_share: 市场份额 (0-1)
        cr4: 行业CR4集中度 (0-1)
        moat_rating: 护城河评分 (0-100)
        demand_rigidity_rating: 需求刚性评分 (0-100)
        substitution_risk_rating: 替代风险评分 (0-100，越高风险越大)
    """
    if cfg is None:
        cfg = settings.svi

    result = SVIScore(
        symbol=symbol,
        market=market,
        roic_10y_median=roic_10y_median,
        fcf_conversion=fcf_conversion,
        gross_margin_std=gross_margin_std,
    )

    # Step 1: 硬筛选
    result.passed_hard_screen = hard_screen(
        roic_10y_median, fcf_conversion, gross_margin_std, debt_to_equity, cfg
    )
    if not result.passed_hard_screen:
        result.level = SVILevel.BLOCK
        return result

    # Step 2: 多维评分
    result.roic_score = score_roic(roic_10y_median)
    result.fcf_score = score_fcf(fcf_conversion)
    result.margin_stability_score = score_margin_stability(gross_margin_std)
    result.concentration_score = score_concentration(market_share, cr4)
    result.moat_score = score_moat(moat_rating)
    result.demand_rigidity_score = score_demand_rigidity(demand_rigidity_rating)
    result.substitution_risk_score = score_substitution_risk(substitution_risk_rating)

    # 加权总分
    result.total = clamp(
        result.roic_score * cfg.roic_weight
        + result.fcf_score * cfg.fcf_weight
        + result.margin_stability_score * cfg.margin_stability_weight
        + result.concentration_score * cfg.concentration_weight
        + result.moat_score * cfg.moat_weight
        + result.demand_rigidity_score * cfg.demand_rigidity_weight
        + result.substitution_risk_score * cfg.substitution_risk_weight
    )

    # Step 3: 分级（使用市场特定阈值）
    result.level = classify_svi(result.total, cfg, market)
    return result
