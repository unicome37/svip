"""
SVIP v1.0 — Weight Engine Tests

测试 A3 组合权重引擎。
"""
import pytest
from src.weight_engine import (
    quality_factor, compute_raw_weights, normalize_weights,
    apply_constraints, determine_actions, compute_portfolio_weights,
)
from src.models import (
    SVIPStock, SVIScore, ValuationResult, AccelerationResult,
    SVILevel, ValuationTier, PhaseState, PoolAction,
)


def _make_stock(
    symbol: str,
    svi_total: float = 80.0,
    val_tier: ValuationTier = ValuationTier.A,
    val_factor: float = 1.0,
    phase: PhaseState = PhaseState.STEADY,
    phase_factor: float = 1.0,
    pool: SVILevel = SVILevel.CORE,
    theme: str = "AI/算力密度",
    sector: str = "Tech",
) -> SVIPStock:
    svi = SVIScore(symbol=symbol, market="US", total=svi_total, level=pool, passed_hard_screen=True)
    val = ValuationResult(symbol=symbol, tier=val_tier, valuation_factor=val_factor)
    accel = AccelerationResult(symbol=symbol, phase=phase, phase_factor=phase_factor)
    return SVIPStock(
        symbol=symbol, name=symbol, market="US",
        sector=sector, theme=theme,
        svi=svi, valuation=val, acceleration=accel,
        pool=pool,
    )


def test_quality_factor():
    """测试 SVI → Q 映射"""
    assert quality_factor(65) == pytest.approx(0.0)
    assert quality_factor(90) == pytest.approx(1.0)
    assert 0.3 < quality_factor(75) < 0.5


def test_compute_raw_weights():
    """测试原始权重计算"""
    stocks = [
        _make_stock("A", svi_total=90, val_factor=1.0, phase_factor=1.2),
        _make_stock("B", svi_total=75, val_factor=0.6, phase_factor=1.0),
    ]
    result = compute_raw_weights(stocks)
    assert result[0].raw_weight > result[1].raw_weight
    assert result[0].raw_weight > 0


def test_normalize_weights():
    """测试归一化"""
    stocks = [
        _make_stock("A"), _make_stock("B"),
    ]
    stocks[0].raw_weight = 0.6
    stocks[1].raw_weight = 0.4
    result = normalize_weights(stocks, target_equity=0.80)
    total = sum(s.target_weight for s in result)
    assert total == pytest.approx(0.80, abs=0.01)


def test_apply_constraints_single_stock_cap():
    """测试单票上限约束"""
    stocks = [_make_stock(f"S{i}", theme=f"T{i}", sector=f"Sec{i}") for i in range(3)]
    stocks[0].target_weight = 0.15  # 超限
    stocks[1].target_weight = 0.04
    stocks[2].target_weight = 0.03
    result = apply_constraints(stocks)
    assert all(s.target_weight <= 0.08 + 0.001 for s in result)


def test_apply_constraints_theme_cap():
    """测试主题桶上限约束"""
    stocks = [_make_stock(f"S{i}", theme="same_theme", sector=f"Sec{i}") for i in range(5)]
    for s in stocks:
        s.target_weight = 0.07  # 合计 35% > 30%
    result = apply_constraints(stocks)
    theme_total = sum(s.target_weight for s in result)
    assert theme_total <= 0.30 + 0.001


def test_determine_actions_build():
    """测试新建仓行动"""
    stock = _make_stock("NEW", phase=PhaseState.ACCELERATING, phase_factor=1.2)
    stock.current_weight = 0.0
    stock.target_weight = 0.06
    result = determine_actions([stock])
    assert result[0].action == PoolAction.BUILD
    assert result[0].target_weight < 0.06  # 首次建仓只50%


def test_determine_actions_exit_block():
    """测试 Block 池退出"""
    stock = _make_stock("BLOCK", pool=SVILevel.BLOCK)
    stock.pool = SVILevel.BLOCK
    stock.target_weight = 0.0
    result = determine_actions([stock])
    assert result[0].action == PoolAction.EXIT


def test_compute_portfolio_weights_full():
    """测试完整权重计算流程"""
    stocks = [
        _make_stock("A", svi_total=85, val_factor=1.0, phase_factor=1.2,
                     theme="AI/算力密度", sector="Tech"),
        _make_stock("B", svi_total=80, val_factor=0.6, phase_factor=1.0,
                     theme="金融制度/支付清算", sector="Fin"),
    ]
    result = compute_portfolio_weights(stocks, target_equity=0.80)
    total = sum(s.target_weight for s in result)
    assert total <= 0.85 + 0.001
    assert all(s.target_weight <= 0.08 + 0.001 for s in result)
