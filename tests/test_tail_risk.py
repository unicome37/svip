"""
SVIP v1.0 — Tail Risk Tests

测试 A7 极端风险模块。
"""
import pytest
from src.tail_risk import (
    assess_liquidity_risk, assess_regime_risk, assess_disruption_risk,
    determine_tail_risk_state, compute_tail_risk,
)
from src.models import TailRiskState


def test_liquidity_risk_crisis():
    """测试流动性危机"""
    score = assess_liquidity_risk(vix=50, credit_spread_change=2.0)
    assert score >= 70


def test_liquidity_risk_normal():
    """测试流动性正常"""
    score = assess_liquidity_risk(vix=15, credit_spread_change=0.1)
    assert score < 30


def test_regime_risk():
    """测试制度风险"""
    assert assess_regime_risk(80) == 80
    assert assess_regime_risk(0) == 0
    assert assess_regime_risk(120) == 100  # capped


def test_disruption_risk_high():
    """测试高技术替代风险"""
    score = assess_disruption_risk(industry_revenue_decline_years=3, market_share_erosion=0.3)
    assert score >= 60


def test_disruption_risk_low():
    """测试低技术替代风险"""
    score = assess_disruption_risk(industry_revenue_decline_years=0, market_share_erosion=0.0)
    assert score == 0


def test_determine_state_crisis():
    """测试危机状态判定"""
    assert determine_tail_risk_state(80, 20, 10) == TailRiskState.CRISIS


def test_determine_state_normal():
    """测试正常状态判定"""
    assert determine_tail_risk_state(10, 10, 10) == TailRiskState.NORMAL


def test_compute_tail_risk_normal():
    """测试完整尾部风险计算 - 正常"""
    result = compute_tail_risk(vix=15, credit_spread_change=0.1)
    assert result.state == TailRiskState.NORMAL
    assert result.tail_risk_factor == 1.0


def test_compute_tail_risk_crisis():
    """测试完整尾部风险计算 - 危机"""
    result = compute_tail_risk(vix=50, credit_spread_change=2.0)
    assert result.state in (TailRiskState.TENSE, TailRiskState.CRISIS)
    assert result.tail_risk_factor < 1.0
