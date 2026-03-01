"""
SVIP v1.0 — Acceleration Engine Tests

测试 A2 慢变量加速检测模块。
"""
import pytest
from src.acceleration_engine import (
    compute_growth_rate, compute_acceleration, smooth_series,
    score_proxy_indicator, classify_phase, compute_acceleration_score,
)
from src.models import PhaseState


def test_compute_growth_rate():
    """测试一阶导计算"""
    assert compute_growth_rate([100, 120]) == pytest.approx(0.2)
    assert compute_growth_rate([100, 100]) == pytest.approx(0.0)
    assert compute_growth_rate([100]) == 0.0


def test_compute_acceleration_positive():
    """测试正加速度"""
    # g1 = (120-100)/100 = 0.2, g2 = (150-120)/120 = 0.25, accel = 0.05
    accel = compute_acceleration([100, 120, 150])
    assert accel > 0


def test_compute_acceleration_negative():
    """测试负加速度（减速）"""
    # g1 = (120-100)/100 = 0.2, g2 = (130-120)/120 = 0.083, accel < 0
    accel = compute_acceleration([100, 120, 130])
    assert accel < 0


def test_smooth_series():
    """测试移动平均平滑"""
    result = smooth_series([10, 20, 30, 40, 50], window=3)
    assert len(result) == 3
    assert result[0] == pytest.approx(20.0)


def test_score_proxy_accelerating():
    """测试加速期代理指标评分"""
    # 加速增长序列
    series = [100, 120, 150, 190, 250]
    score = score_proxy_indicator(series)
    assert score > 60  # 应判定为加速


def test_score_proxy_decaying():
    """测试衰减期代理指标评分"""
    # 减速序列
    series = [250, 260, 265, 267, 268]
    score = score_proxy_indicator(series)
    assert score < 60  # 应判定为稳态或衰减


def test_classify_phase():
    """测试相位判定"""
    assert classify_phase(70) == PhaseState.ACCELERATING
    assert classify_phase(45) == PhaseState.STEADY
    assert classify_phase(20) == PhaseState.DECAYING


def test_compute_acceleration_score_with_data():
    """测试有数据时的完整加速检测"""
    result = compute_acceleration_score(
        symbol="TEST",
        theme="AI/算力密度",
        penetration_series=[0.10, 0.15, 0.22, 0.32, 0.45],
        cost_curve_series=[1.0, 0.8, 0.6, 0.4, 0.25],
        capex_series=[10, 15, 22, 33, 50],
    )
    assert result.symbol == "TEST"
    assert result.acceleration_score > 0
    assert result.phase in (PhaseState.ACCELERATING, PhaseState.STEADY, PhaseState.DECAYING)


def test_compute_acceleration_score_no_data():
    """测试无数据时默认稳态"""
    result = compute_acceleration_score(symbol="EMPTY", theme="")
    assert result.acceleration_score == 50.0
    assert result.phase == PhaseState.STEADY
    assert result.phase_factor == 1.0
