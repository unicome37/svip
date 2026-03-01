"""
SVIP v1.0 — Macro Filter Tests

测试 A4 宏观慢变量过滤器。
"""
import pytest
from src.macro_filter import (
    score_interest_rate, score_liquidity, score_earnings_cycle,
    compute_macro_state,
)
from src.models import MacroWind


def test_interest_rate_tailwind():
    """测试利率结构顺风"""
    score = score_interest_rate(yield_spread=1.0, real_yield=0.3, credit_spread=3.0)
    assert score == 1


def test_interest_rate_headwind():
    """测试利率结构逆风"""
    score = score_interest_rate(yield_spread=-0.5, real_yield=2.5, credit_spread=5.5)
    assert score == -1


def test_interest_rate_neutral():
    """测试利率结构中性"""
    score = score_interest_rate(yield_spread=0.3, real_yield=1.0, credit_spread=4.0)
    assert score == 0


def test_liquidity_tailwind():
    """测试流动性顺风"""
    score = score_liquidity(m2_yoy=0.08, fci=-0.8, credit_growth=0.06)
    assert score == 1


def test_liquidity_headwind():
    """测试流动性逆风"""
    score = score_liquidity(m2_yoy=0.01, fci=0.8, credit_growth=-0.02)
    assert score == -1


def test_earnings_cycle_tailwind():
    """测试盈利周期顺风"""
    score = score_earnings_cycle(earnings_yoy=0.10, ism_new_orders=55)
    assert score == 1


def test_earnings_cycle_headwind():
    """测试盈利周期逆风"""
    score = score_earnings_cycle(earnings_yoy=-0.10, ism_new_orders=45)
    assert score == -1


def test_compute_macro_state_tailwind():
    """测试综合顺风"""
    state = compute_macro_state(
        yield_spread=1.0, real_yield=0.3, credit_spread=3.0,
        m2_yoy=0.08, fci=-0.8, credit_growth=0.06,
        earnings_yoy=0.10, ism_new_orders=55,
    )
    assert state.total_score >= 2
    assert state.wind == MacroWind.TAILWIND
    assert state.macro_risk_factor >= 1.0


def test_compute_macro_state_headwind():
    """测试综合逆风"""
    state = compute_macro_state(
        yield_spread=-0.5, real_yield=2.5, credit_spread=5.5,
        m2_yoy=0.01, fci=0.8, credit_growth=-0.02,
        earnings_yoy=-0.10, ism_new_orders=45,
    )
    assert state.total_score <= -2
    assert state.wind == MacroWind.HEADWIND
    assert state.macro_risk_factor <= 0.85


def test_compute_macro_state_no_data():
    """测试无数据时默认中性"""
    state = compute_macro_state()
    assert state.total_score == 0
    assert state.wind == MacroWind.NEUTRAL
