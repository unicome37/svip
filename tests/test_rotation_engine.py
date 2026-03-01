"""
SVIP v1.0 — Rotation Engine Tests

测试 A8 慢变量主题轮动。
"""
import pytest
from src.rotation_engine import compute_theme_acceleration, compute_rotation_signals
from src.models import SVIPStock, SVIScore, AccelerationResult, SVILevel, PhaseState


def _make_stock(symbol: str, theme: str, accel_score: float) -> SVIPStock:
    svi = SVIScore(symbol=symbol, market="US", total=80, level=SVILevel.CORE, passed_hard_screen=True)
    accel = AccelerationResult(symbol=symbol, theme=theme, acceleration_score=accel_score)
    return SVIPStock(symbol=symbol, name=symbol, theme=theme, svi=svi, acceleration=accel)


def test_compute_theme_acceleration():
    """测试主题桶平均加速度"""
    stocks = [
        _make_stock("A", "AI", 80),
        _make_stock("B", "AI", 60),
        _make_stock("C", "Healthcare", 40),
    ]
    result = compute_theme_acceleration(stocks)
    assert result["AI"] == pytest.approx(70.0)
    assert result["Healthcare"] == pytest.approx(40.0)


def test_compute_rotation_signals_divergent():
    """测试桶间分化时产生轮动信号"""
    stocks = [
        _make_stock("A", "AI", 90),
        _make_stock("B", "AI", 85),
        _make_stock("C", "Healthcare", 30),
        _make_stock("D", "Healthcare", 25),
    ]
    signals = compute_rotation_signals(stocks)
    assert len(signals) == 2
    ai_sig = next(s for s in signals if s.theme == "AI")
    hc_sig = next(s for s in signals if s.theme == "Healthcare")
    assert ai_sig.z_score > 0
    assert hc_sig.z_score < 0
    assert ai_sig.weight_adjustment >= 0
    assert hc_sig.weight_adjustment <= 0


def test_compute_rotation_signals_empty():
    """测试空列表"""
    signals = compute_rotation_signals([])
    assert signals == []


def test_compute_rotation_signals_single_theme():
    """测试单一主题不产生分化"""
    stocks = [_make_stock("A", "AI", 70), _make_stock("B", "AI", 70)]
    signals = compute_rotation_signals(stocks)
    assert len(signals) == 1
    assert signals[0].weight_adjustment == 0.0
