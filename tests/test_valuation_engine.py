"""
SVIP v1.0 — Valuation Engine Tests

测试 A1 估值安全垫模块。
"""
import pytest
from src.valuation_engine import (
    compute_qpeg, check_red_flags, determine_tier, compute_valuation,
)
from src.models import ValuationTier


def test_compute_qpeg():
    """测试 QPEG 计算"""
    # PE=30, g=15%, SVI=80 → QPEG = (30/15) / (1+0.8) = 2/1.8 ≈ 1.11
    qpeg = compute_qpeg(pe_ratio=30, growth_rate=0.15, svi_score=80)
    assert 1.0 < qpeg < 1.2


def test_compute_qpeg_no_growth():
    """测试零增长情况"""
    qpeg = compute_qpeg(pe_ratio=30, growth_rate=0.0, svi_score=80)
    assert qpeg > 100  # 应该返回极高值


def test_check_red_flags_none():
    """测试无红旗"""
    a, b, c, count = check_red_flags(
        valuation_percentile=0.60,
        growth_concentration=0.30,
        reinvestment_declining_years=0,
    )
    assert count == 0


def test_check_red_flags_all():
    """测试全部红旗"""
    a, b, c, count = check_red_flags(
        valuation_percentile=0.85,  # > 80%
        growth_concentration=0.65,  # > 60%
        reinvestment_declining_years=2,  # >= 2
    )
    assert count == 3
    assert a is True
    assert b is True
    assert c is True


def test_determine_tier_a():
    """测试 Tier A"""
    tier = determine_tier(
        fcf_yield=0.04,  # >= 3%
        qpeg=1.1,        # <= 1.2
        red_flag_count=0,
    )
    assert tier == ValuationTier.A


def test_determine_tier_b():
    """测试 Tier B"""
    tier = determine_tier(
        fcf_yield=0.04,
        qpeg=1.5,        # 1.2 < QPEG <= 1.8
        red_flag_count=0,
    )
    assert tier == ValuationTier.B


def test_determine_tier_c_low_fcf():
    """测试 Tier C（FCF Yield 不达标）"""
    tier = determine_tier(
        fcf_yield=0.02,  # < 3%
        qpeg=1.1,
        red_flag_count=0,
    )
    assert tier == ValuationTier.C


def test_determine_tier_c_high_qpeg():
    """测试 Tier C（QPEG 过高）"""
    tier = determine_tier(
        fcf_yield=0.04,
        qpeg=2.0,        # > 1.8
        red_flag_count=0,
    )
    assert tier == ValuationTier.C


def test_determine_tier_c_red_flags():
    """测试 Tier C（红旗过多）"""
    tier = determine_tier(
        fcf_yield=0.04,
        qpeg=1.1,
        red_flag_count=2,  # >= 2
    )
    assert tier == ValuationTier.C


def test_compute_valuation_tier_a():
    """测试完整估值计算 - Tier A"""
    result = compute_valuation(
        symbol="MSFT",
        fcf_yield=0.04,
        pe_ratio=30,
        growth_rate=0.15,
        svi_score=80,
        valuation_percentile=0.60,
        growth_concentration=0.30,
        reinvestment_declining_years=0,
    )
    assert result.tier == ValuationTier.A
    assert result.valuation_factor == 1.0
    assert result.red_flag_count == 0


def test_compute_valuation_tier_c():
    """测试完整估值计算 - Tier C"""
    result = compute_valuation(
        symbol="EXPENSIVE",
        fcf_yield=0.015,  # 不达标
        pe_ratio=60,
        growth_rate=0.10,
        svi_score=75,
        valuation_percentile=0.90,
        growth_concentration=0.70,
        reinvestment_declining_years=2,
    )
    assert result.tier == ValuationTier.C
    assert result.valuation_factor == 0.2
    assert result.red_flag_count >= 2
