"""
SVIP v1.0 — A4 Macro Filter (宏观慢变量过滤器)

只看三个宏观慢变量：
  1. 利率结构（10Y-2Y利差、实际利率、信用利差）
  2. 流动性（M2同比、FCI、银行信贷增长）
  3. 盈利周期（标普500盈利同比、ISM新订单）

输出：MacroRiskFactor (0.75 - 1.10)
不是择时，只是回答：资金地形是否允许慢变量释放能量？
"""
from typing import Optional
from config.settings import settings, MacroConfig
from src.models import MacroState, MacroWind


def score_interest_rate(
    yield_spread: Optional[float] = None,
    real_yield: Optional[float] = None,
    credit_spread: Optional[float] = None,
) -> int:
    """
    利率结构评分。
    +1 顺风：利差正常、实际利率低、信用利差窄
    -1 逆风：倒挂、实际利率高、信用利差宽
    """
    signals = []

    if yield_spread is not None:
        if yield_spread > 0.5:
            signals.append(1)
        elif yield_spread < -0.2:
            signals.append(-1)
        else:
            signals.append(0)

    if real_yield is not None:
        if real_yield < 0.5:
            signals.append(1)
        elif real_yield > 2.0:
            signals.append(-1)
        else:
            signals.append(0)

    if credit_spread is not None:
        if credit_spread < 3.5:
            signals.append(1)
        elif credit_spread > 5.0:
            signals.append(-1)
        else:
            signals.append(0)

    if not signals:
        return 0
    avg = sum(signals) / len(signals)
    if avg > 0.3:
        return 1
    if avg < -0.3:
        return -1
    return 0


def score_liquidity(
    m2_yoy: Optional[float] = None,
    fci: Optional[float] = None,
    credit_growth: Optional[float] = None,
) -> int:
    """
    流动性评分。
    +1 顺风：M2扩张、金融条件宽松
    -1 逆风：M2收缩、金融条件紧缩
    """
    signals = []

    if m2_yoy is not None:
        if m2_yoy > 0.06:
            signals.append(1)
        elif m2_yoy < 0.02:
            signals.append(-1)
        else:
            signals.append(0)

    if fci is not None:
        # FCI 越低越宽松（不同指数定义不同，这里假设低=宽松）
        if fci < -0.5:
            signals.append(1)
        elif fci > 0.5:
            signals.append(-1)
        else:
            signals.append(0)

    if credit_growth is not None:
        if credit_growth > 0.05:
            signals.append(1)
        elif credit_growth < 0.0:
            signals.append(-1)
        else:
            signals.append(0)

    if not signals:
        return 0
    avg = sum(signals) / len(signals)
    if avg > 0.3:
        return 1
    if avg < -0.3:
        return -1
    return 0


def score_earnings_cycle(
    earnings_yoy: Optional[float] = None,
    ism_new_orders: Optional[float] = None,
) -> int:
    """
    盈利周期评分。
    +1 顺风：盈利增长、ISM扩张
    -1 逆风：盈利下行、ISM收缩
    """
    signals = []

    if earnings_yoy is not None:
        if earnings_yoy > 0.05:
            signals.append(1)
        elif earnings_yoy < -0.05:
            signals.append(-1)
        else:
            signals.append(0)

    if ism_new_orders is not None:
        if ism_new_orders > 52:
            signals.append(1)
        elif ism_new_orders < 48:
            signals.append(-1)
        else:
            signals.append(0)

    if not signals:
        return 0
    avg = sum(signals) / len(signals)
    if avg > 0.3:
        return 1
    if avg < -0.3:
        return -1
    return 0


def compute_macro_state(
    yield_spread: Optional[float] = None,
    real_yield: Optional[float] = None,
    credit_spread: Optional[float] = None,
    m2_yoy: Optional[float] = None,
    fci: Optional[float] = None,
    credit_growth: Optional[float] = None,
    earnings_yoy: Optional[float] = None,
    ism_new_orders: Optional[float] = None,
    cfg: MacroConfig = None,
) -> MacroState:
    """计算完整宏观慢变量状态"""
    if cfg is None:
        cfg = settings.macro

    state = MacroState()
    state.yield_spread_10y2y = yield_spread
    state.real_yield = real_yield
    state.credit_spread = credit_spread
    state.m2_yoy = m2_yoy

    state.interest_rate_score = score_interest_rate(yield_spread, real_yield, credit_spread)
    state.liquidity_score = score_liquidity(m2_yoy, fci, credit_growth)
    state.earnings_cycle_score = score_earnings_cycle(earnings_yoy, ism_new_orders)

    state.total_score = (
        state.interest_rate_score
        + state.liquidity_score
        + state.earnings_cycle_score
    )

    # 风向判定
    if state.total_score >= 2:
        state.wind = MacroWind.TAILWIND
    elif state.total_score <= -2:
        state.wind = MacroWind.HEADWIND
    else:
        state.wind = MacroWind.NEUTRAL

    # MacroRiskFactor
    state.macro_risk_factor = cfg.factor_map.get(state.total_score, 0.90)

    return state
