"""
SVIP v1.0 Data Models

慢变量投资池系统 — 所有数据结构定义。
基于 A0-A11 理论体系。
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum


# ============================================================================
# 枚举类型
# ============================================================================

class Market(str, Enum):
    """市场"""
    US = "US"
    HK = "HK"
    CN = "CN"


class SVILevel(str, Enum):
    """SVI 分级"""
    CORE = "core"       # >= 75 核心池
    WATCH = "watch"     # 60-75 观察池
    BLOCK = "block"     # < 60 禁入池


class ValuationTier(str, Enum):
    """A1 估值等级"""
    A = "A"   # 好公司+好价格 → 可入核心池
    B = "B"   # 好公司+合理/略贵 → 观察/小仓
    C = "C"   # 好公司+极贵/脆弱 → 限仓/剔除


class PhaseState(str, Enum):
    """A2 慢变量相位状态"""
    ACCELERATING = "accelerating"  # 加速期
    STEADY = "steady"              # 稳态期
    DECAYING = "decaying"          # 衰减期


class MacroWind(str, Enum):
    """A4 宏观风向"""
    TAILWIND = "tailwind"    # 顺风
    NEUTRAL = "neutral"      # 中性
    HEADWIND = "headwind"    # 逆风


class TailRiskState(str, Enum):
    """A7 尾部风险状态"""
    NORMAL = "normal"        # 正常
    ALERT = "alert"          # 警戒
    TENSE = "tense"          # 紧张
    CRISIS = "crisis"        # 危机


class ThemeBucket(str, Enum):
    """慢变量主题桶"""
    AI_COMPUTE = "AI/算力密度"
    AGING_HEALTH = "老龄化/医疗支付"
    FINANCIAL_INFRA = "金融制度/支付清算"
    BRAND_CONSUMER = "品牌/代际消费"
    ENERGY_TRANSITION = "能源转型/电气化"
    OTHER = "其他"


class PoolAction(str, Enum):
    """组合行动"""
    BUILD = "build"          # 建仓
    ADD = "add"              # 加仓
    HOLD = "hold"            # 持有
    LIGHT_REDUCE = "light_reduce"    # 轻度减仓
    HEAVY_REDUCE = "heavy_reduce"    # 重度减仓
    EXIT = "exit"            # 清仓


# ============================================================================
# 核心数据结构
# ============================================================================

@dataclass
class SVIScore:
    """SVI 慢变量指数评分结果"""
    symbol: str
    market: str
    # 硬筛选通过
    passed_hard_screen: bool = False
    # 各维度评分 (0-100)
    roic_score: float = 0.0
    fcf_score: float = 0.0
    margin_stability_score: float = 0.0
    concentration_score: float = 0.0
    moat_score: float = 0.0
    demand_rigidity_score: float = 0.0
    substitution_risk_score: float = 0.0
    # 总分
    total: float = 0.0
    level: SVILevel = SVILevel.BLOCK
    # 原始财务数据
    roic_10y_median: float = 0.0
    fcf_conversion: float = 0.0
    gross_margin_std: float = 0.0


@dataclass
class ValuationResult:
    """A1 估值安全垫评估结果"""
    symbol: str
    fcf_yield: float = 0.0
    pe_ratio: float = 0.0
    growth_rate: float = 0.0       # 保守内生增长率
    qpeg: float = 0.0             # Quality-Adjusted PEG
    valuation_percentile: float = 0.0  # 历史估值分位
    # 红旗
    red_flag_a: bool = False       # 估值分位过高
    red_flag_b: bool = False       # 增长预期过度集中
    red_flag_c: bool = False       # 再投资回报坍塌
    red_flag_count: int = 0
    # 输出
    tier: ValuationTier = ValuationTier.C
    valuation_factor: float = 0.2  # 估值折扣系数


@dataclass
class AccelerationResult:
    """A2 慢变量加速检测结果"""
    symbol: str
    theme: str = ""
    # 代理指标得分
    penetration_score: float = 0.0
    cost_curve_score: float = 0.0
    capex_score: float = 0.0
    policy_score: float = 0.0
    # 综合
    acceleration_score: float = 0.0  # 0-100
    phase: PhaseState = PhaseState.STEADY
    phase_factor: float = 1.0


@dataclass
class SVIPStock:
    """SVIP 投资池中的单只股票完整画像"""
    symbol: str
    name: str = ""
    market: str = "US"
    sector: str = ""
    theme: str = ""                    # 慢变量主题桶
    # 三层评分
    svi: Optional[SVIScore] = None
    valuation: Optional[ValuationResult] = None
    acceleration: Optional[AccelerationResult] = None
    # 组合权重
    raw_weight: float = 0.0            # W_raw = Q × V × P
    target_weight: float = 0.0         # 约束投影后的目标权重
    current_weight: float = 0.0        # 当前实际权重
    # 池分类
    pool: SVILevel = SVILevel.BLOCK
    action: PoolAction = PoolAction.HOLD


@dataclass
class MacroState:
    """A4 宏观慢变量状态"""
    # 三个宏观慢变量评分 (+1/0/-1)
    interest_rate_score: int = 0       # 利率结构
    liquidity_score: int = 0           # 流动性
    earnings_cycle_score: int = 0      # 盈利周期
    # 汇总
    total_score: int = 0               # -3 到 +3
    wind: MacroWind = MacroWind.NEUTRAL
    macro_risk_factor: float = 0.90    # 0.75 - 1.10
    # 原始数据
    yield_spread_10y2y: Optional[float] = None
    real_yield: Optional[float] = None
    credit_spread: Optional[float] = None
    m2_yoy: Optional[float] = None


@dataclass
class TailRiskResult:
    """A7 极端风险评估结果"""
    # 三类风险评分
    liquidity_risk: float = 0.0        # 流动性型
    regime_risk: float = 0.0           # 制度型
    disruption_risk: float = 0.0       # 技术范式型
    # 汇总
    state: TailRiskState = TailRiskState.NORMAL
    tail_risk_factor: float = 1.0
    # 原始数据
    vix: Optional[float] = None
    credit_spread_change: Optional[float] = None


@dataclass
class PortfolioAllocation:
    """组合配置输出"""
    timestamp: datetime = field(default_factory=datetime.now)
    # 持仓
    stocks: List[SVIPStock] = field(default_factory=list)
    # 汇总
    total_equity: float = 0.0
    cash_weight: float = 0.0
    core_pool_weight: float = 0.0
    watch_pool_weight: float = 0.0
    # 主题暴露
    theme_exposure: Dict[str, float] = field(default_factory=dict)
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    # 宏观与风险
    macro: Optional[MacroState] = None
    tail_risk: Optional[TailRiskResult] = None
    # 最终仓位修正因子
    macro_risk_factor: float = 1.0
    tail_risk_factor: float = 1.0
    final_equity_ceiling: float = 0.85
    # 违规
    violations: List[str] = field(default_factory=list)


@dataclass
class RotationSignal:
    """A8 慢变量主题轮动信号"""
    theme: str
    avg_acceleration: float = 0.0
    z_score: float = 0.0
    weight_adjustment: float = 0.0     # +10%, +5%, 0, -5%, -10%


@dataclass
class SVIPReport:
    """SVIP 完整报告"""
    timestamp: datetime = field(default_factory=datetime.now)
    market: str = "US"
    # 投资池
    core_pool: List[SVIPStock] = field(default_factory=list)
    watch_pool: List[SVIPStock] = field(default_factory=list)
    # 组合
    allocation: Optional[PortfolioAllocation] = None
    # 轮动信号
    rotation_signals: List[RotationSignal] = field(default_factory=list)
    # 系统状态
    macro: Optional[MacroState] = None
    tail_risk: Optional[TailRiskResult] = None
