"""
SVIP v1.0 — SVI Engine Tests

测试 SVI 慢变量指数计算。
"""
import pytest
from src.svi_engine import (
    hard_screen, compute_svi, score_roic, score_fcf,
    score_margin_stability, classify_svi,
)
from src.models import SVILevel


def test_hard_screen_pass():
    """测试硬筛选通过"""
    result = hard_screen(
        roic_10y_median=0.20,
        fcf_conversion=0.85,
        gross_margin_std=0.03,
        debt_to_equity=1.0,
    )
    assert result is True


def test_hard_screen_fail_roic():
    """测试 ROIC 不达标"""
    result = hard_screen(
        roic_10y_median=0.10,  # < 15%
        fcf_conversion=0.85,
        gross_margin_std=0.03,
        debt_to_equity=1.0,
    )
    assert result is False


def test_hard_screen_fail_fcf():
    """测试 FCF 转化率不达标"""
    result = hard_screen(
        roic_10y_median=0.20,
        fcf_conversion=0.70,  # < 80%
        gross_margin_std=0.03,
        debt_to_equity=1.0,
    )
    assert result is False


def test_score_roic():
    """测试 ROIC 评分"""
    assert score_roic(0.10) == 0.0
    assert score_roic(0.35) == 100.0
    assert 40 < score_roic(0.20) < 60


def test_score_fcf():
    """测试 FCF 评分"""
    assert score_fcf(0.5) == 0.0
    assert score_fcf(1.0) == 100.0
    assert 40 < score_fcf(0.75) < 60


def test_score_margin_stability():
    """测试毛利稳定性评分"""
    assert score_margin_stability(0.01) == 100.0
    assert score_margin_stability(0.15) == 0.0
    assert 40 < score_margin_stability(0.05) < 80


def test_classify_svi():
    """测试 SVI 分级"""
    assert classify_svi(80) == SVILevel.CORE
    assert classify_svi(65) == SVILevel.WATCH
    assert classify_svi(50) == SVILevel.BLOCK


def test_compute_svi_high_quality():
    """测试高质量公司 SVI 计算"""
    result = compute_svi(
        symbol="MSFT",
        market="US",
        roic_10y_median=0.30,
        fcf_conversion=0.95,
        gross_margin_std=0.02,
        debt_to_equity=0.45,
        market_share=0.25,
        cr4=0.65,
        moat_rating=90,
        demand_rigidity_rating=85,
        substitution_risk_rating=15,
    )
    assert result.passed_hard_screen is True
    assert result.total > 70
    assert result.level == SVILevel.CORE


def test_compute_svi_fail_hard_screen():
    """测试未通过硬筛选"""
    result = compute_svi(
        symbol="WEAK",
        market="US",
        roic_10y_median=0.08,  # 不达标
        fcf_conversion=0.95,
        gross_margin_std=0.02,
        debt_to_equity=0.45,
    )
    assert result.passed_hard_screen is False
    assert result.level == SVILevel.BLOCK
    assert result.total == 0.0
