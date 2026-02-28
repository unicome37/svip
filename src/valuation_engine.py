"""
SVIP v1.0 — A1 Valuation Engine (估值安全垫模块)

两条核心规则：
  1. FCF Yield 底线 >= 3%
  2. Quality-Adjusted PEG (QPEG)

三个红旗：
  A: 估值分位过高（拥挤）
  B: 增长预期过度集中
  C: 再投资回报坍塌

输出：ValuationTier = A / B / C
"""
from config.settings import settings, ValuationConfig
from src.models import ValuationResult, ValuationTier


def compute_qpeg(
    pe_ratio: float,
    growth_rate: float,
    svi_score: float,
) -> float:
    """
    Quality-Adjusted PEG

    QPEG = (PE / g) / (1 + SVI/100)
    高质量慢变量（SVI高）可以"更贵一点"。
    """
    if growth_rate <= 0 or pe_ratio <= 0:
        return 999.0  # 无增长或负PE → 极高QPEG
    peg = pe_ratio / (growth_rate * 100)  # growth_rate 是小数，转百分比
    quality_adj = 1 + svi_score / 100
    return peg / quality_adj


def check_red_flags(
    valuation_percentile: float,
    growth_concentration: float,
    reinvestment_declining_years: int,
    cfg: ValuationConfig = None,
) -> tuple[bool, bool, bool, int]:
    """检查三个红旗"""
    if cfg is None:
        cfg = settings.valuation

    flag_a = valuation_percentile > cfg.valuation_percentile_max
    flag_b = growth_concentration > cfg.growth_concentration_max
    flag_c = reinvestment_declining_years >= cfg.reinvestment_decline_years
    count = sum([flag_a, flag_b, flag_c])
    return flag_a, flag_b, flag_c, count


def determine_tier(
    fcf_yield: float,
    qpeg: float,
    red_flag_count: int,
    cfg: ValuationConfig = None,
) -> ValuationTier:
    """
    确定估值等级。

    A: 满足规则1 & 规则2，且无红旗 → 可入核心池
    B: 满足规则1，但QPEG在观察区或有1个红旗 → 观察/小仓
    C: 不满足规则1 或 QPEG>1.8 或 >=2红旗 → 限仓/剔除
    """
    if cfg is None:
        cfg = settings.valuation

    # 规则1不满足 → C
    if fcf_yield < cfg.fcf_yield_min:
        return ValuationTier.C

    # >= 2 红旗 → C
    if red_flag_count >= 2:
        return ValuationTier.C

    # QPEG 过高 → C
    if qpeg > cfg.qpeg_tier_b_max:
        return ValuationTier.C

    # QPEG 在 A 区间且无红旗 → A
    if qpeg <= cfg.qpeg_tier_a_max and red_flag_count == 0:
        return ValuationTier.A

    # 其余 → B
    return ValuationTier.B


def compute_valuation(
    symbol: str,
    fcf_yield: float,
    pe_ratio: float,
    growth_rate: float,
    svi_score: float,
    valuation_percentile: float = 0.5,
    growth_concentration: float = 0.3,
    reinvestment_declining_years: int = 0,
    cfg: ValuationConfig = None,
) -> ValuationResult:
    """
    计算完整 A1 估值安全垫。

    Args:
        symbol: 股票代码
        fcf_yield: FCF收益率 (如 0.05 = 5%)
        pe_ratio: 市盈率
        growth_rate: 保守内生增长率 (如 0.12 = 12%)
        svi_score: SVI总分 (0-100)
        valuation_percentile: 历史估值分位 (0-1)
        growth_concentration: 增长预期集中度 (0-1)
        reinvestment_declining_years: 再投资回报连续下降年数
    """
    if cfg is None:
        cfg = settings.valuation

    result = ValuationResult(symbol=symbol)
    result.fcf_yield = fcf_yield
    result.pe_ratio = pe_ratio
    result.growth_rate = growth_rate
    result.valuation_percentile = valuation_percentile

    # QPEG
    result.qpeg = compute_qpeg(pe_ratio, growth_rate, svi_score)

    # 红旗检测
    result.red_flag_a, result.red_flag_b, result.red_flag_c, result.red_flag_count = (
        check_red_flags(
            valuation_percentile, growth_concentration,
            reinvestment_declining_years, cfg,
        )
    )

    # 确定 Tier
    result.tier = determine_tier(fcf_yield, result.qpeg, result.red_flag_count, cfg)

    # 估值因子
    factor_map = {
        ValuationTier.A: cfg.tier_a_factor,
        ValuationTier.B: cfg.tier_b_factor,
        ValuationTier.C: cfg.tier_c_factor,
    }
    result.valuation_factor = factor_map[result.tier]

    return result
