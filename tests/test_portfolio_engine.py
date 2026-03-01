"""
SVIP v1.0 — Portfolio Engine Tests

测试组合编排引擎。
"""
import pytest
from src.portfolio_engine import (
    classify_pools, determine_cash_level, build_allocation,
    apply_rotation_adjustments, generate_report,
)
from src.models import (
    SVIPStock, SVIScore, ValuationResult, AccelerationResult,
    SVILevel, ValuationTier, PhaseState, RotationSignal, MacroState, MacroWind,
)


def _make_stock(
    symbol: str,
    svi_total: float = 80.0,
    svi_level: SVILevel = SVILevel.CORE,
    val_tier: ValuationTier = ValuationTier.A,
    val_factor: float = 1.0,
    phase: PhaseState = PhaseState.STEADY,
    phase_factor: float = 1.0,
    theme: str = "AI/算力密度",
    sector: str = "Tech",
) -> SVIPStock:
    svi = SVIScore(symbol=symbol, market="US", total=svi_total, level=svi_level, passed_hard_screen=True)
    val = ValuationResult(symbol=symbol, tier=val_tier, valuation_factor=val_factor)
    accel = AccelerationResult(symbol=symbol, theme=theme, acceleration_score=50, phase=phase, phase_factor=phase_factor)
    return SVIPStock(
        symbol=symbol, name=symbol, market="US",
        sector=sector, theme=theme,
        svi=svi, valuation=val, acceleration=accel,
    )


def test_classify_pools_core():
    """测试 Core 池分类：高质量 + 非C估值 + 非衰减"""
    stock = _make_stock("A", svi_level=SVILevel.CORE, val_tier=ValuationTier.A, phase=PhaseState.STEADY)
    core, watch, block = classify_pools([stock])
    assert len(core) == 1
    assert core[0].pool == SVILevel.CORE


def test_classify_pools_watch_due_to_tier_c():
    """测试 ValuationTier.C 应进入 Watch 池而非 Core"""
    stock = _make_stock("B", svi_level=SVILevel.CORE, val_tier=ValuationTier.C, phase=PhaseState.STEADY)
    core, watch, block = classify_pools([stock])
    assert len(core) == 0
    assert len(watch) == 1
    assert watch[0].pool == SVILevel.WATCH


def test_classify_pools_watch_due_to_decaying():
    """测试衰减期应进入 Watch 池而非 Core"""
    stock = _make_stock("C", svi_level=SVILevel.CORE, val_tier=ValuationTier.A, phase=PhaseState.DECAYING)
    core, watch, block = classify_pools([stock])
    assert len(core) == 0
    assert len(watch) == 1


def test_classify_pools_block():
    """测试 Block 池"""
    stock = _make_stock("D", svi_level=SVILevel.BLOCK)
    core, watch, block = classify_pools([stock])
    assert len(block) == 1


def test_apply_rotation_adjustments():
    """测试轮动调整应用"""
    stock = _make_stock("A", theme="AI/算力密度")
    stock.target_weight = 0.05
    signals = [RotationSignal(theme="AI/算力密度", avg_acceleration=80, z_score=1.5, weight_adjustment=0.10)]
    result = apply_rotation_adjustments([stock], signals)
    assert result[0].target_weight == pytest.approx(0.055)


def test_apply_rotation_no_negative():
    """测试轮动调整不产生负权重"""
    stock = _make_stock("A", theme="Declining")
    stock.target_weight = 0.01
    signals = [RotationSignal(theme="Declining", avg_acceleration=20, z_score=-2.0, weight_adjustment=-0.10)]
    result = apply_rotation_adjustments([stock], signals)
    assert result[0].target_weight >= 0.0


def test_build_allocation_basic():
    """测试基本组合构建"""
    stocks = [
        _make_stock("A", theme="AI/算力密度", sector="Tech"),
        _make_stock("B", theme="金融制度/支付清算", sector="Fin"),
    ]
    alloc = build_allocation(stocks)
    assert alloc.total_equity > 0
    assert alloc.cash_weight >= 0
    assert alloc.total_equity + alloc.cash_weight <= 1.0 + 0.01


def test_generate_report():
    """测试报告生成"""
    stocks = [
        _make_stock("A", theme="AI/算力密度", sector="Tech"),
        _make_stock("B", theme="金融制度/支付清算", sector="Fin"),
    ]
    report = generate_report(stocks, market="US")
    assert report.market == "US"
    assert report.allocation is not None
