"""
SVIP v1.0 Configuration

慢变量投资池系统 — 所有阈值、权重、约束集中管理。
基于 A1-A11 理论体系。
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# SVI 慢变量指数 配置（结构质量筛选）
# ============================================================================

@dataclass(frozen=True)
class SVIConfig:
    """SVI = Slow Variable Index 慢变量绑定度评分"""

    # 硬筛选阈值
    roic_10y_min: float = 0.15          # 10年ROIC中位数 >= 15%
    fcf_conversion_min: float = 0.80    # FCF/净利润 >= 0.8
    gross_margin_volatility_max: float = 0.05  # 毛利率波动 < ±5%
    debt_to_equity_max: float = 1.5     # 资产负债率上限

    # SVI评分权重
    roic_weight: float = 0.20           # 10年ROIC中位数
    fcf_weight: float = 0.15            # FCF转化率
    margin_stability_weight: float = 0.15  # 毛利稳定性
    concentration_weight: float = 0.15  # 行业集中度
    moat_weight: float = 0.15           # 网络/牌照壁垒
    demand_rigidity_weight: float = 0.10  # 需求刚性
    substitution_risk_weight: float = 0.10  # 替代风险（反向）

    # SVI 分区阈值
    core_threshold: float = 75.0        # >= 75 进入核心池
    watch_threshold: float = 60.0       # 60-75 观察池
    # < 60 不入池


# ============================================================================
# A1 估值安全垫 配置
# ============================================================================

@dataclass(frozen=True)
class ValuationConfig:
    """A1 估值安全垫模块参数"""

    # 规则1：FCF Yield 底线
    fcf_yield_min: float = 0.03         # FCF Yield >= 3%

    # 规则2：Quality-Adjusted PEG
    qpeg_tier_a_max: float = 1.2        # QPEG <= 1.2 → Tier A
    qpeg_tier_b_max: float = 1.8        # QPEG <= 1.8 → Tier B
    # QPEG > 1.8 → Tier C

    # 红旗阈值
    valuation_percentile_max: float = 0.80  # 红旗A：估值分位 > 80%
    growth_concentration_max: float = 0.60  # 红旗B：增长预期集中度
    reinvestment_decline_years: int = 2     # 红旗C：再投资回报连续下降年数

    # 估值因子映射
    tier_a_factor: float = 1.0
    tier_b_factor: float = 0.6
    tier_c_factor: float = 0.2


# ============================================================================
# A2 慢变量加速检测 配置
# ============================================================================

@dataclass(frozen=True)
class AccelerationConfig:
    """A2 慢变量趋势加速检测参数"""

    # 平滑窗口
    smoothing_periods: int = 3          # 3期移动平均

    # AccelerationScore 阈值
    accelerating_threshold: float = 60.0  # >= 60 加速期
    steady_threshold: float = 30.0        # 30-60 稳态期
    # < 30 衰减期

    # 相位因子映射
    accelerating_factor: float = 1.2
    steady_factor: float = 1.0
    decaying_factor: float = 0.5

    # 代理指标权重
    penetration_weight: float = 0.40    # 渗透率类
    cost_curve_weight: float = 0.30     # 单位成本曲线
    capex_weight: float = 0.20          # 资本开支/投入强度
    policy_weight: float = 0.10         # 政策/制度变化


# ============================================================================
# A3 组合权重引擎 配置
# ============================================================================

@dataclass(frozen=True)
class WeightConfig:
    """A3 组合权重与约束参数"""

    # 质量因子映射（SVI → Q）
    q_floor: float = 65.0              # SVI=65 → Q=0
    q_ceiling: float = 90.0            # SVI=90 → Q=1

    # 约束
    single_stock_max: float = 0.08     # 单票上限 8%
    theme_bucket_max: float = 0.30     # 单慢变量桶上限 30%
    sector_max: float = 0.25           # 单行业上限 25%
    core_pool_min: float = 0.60        # 核心池最低仓位
    core_pool_max: float = 0.85        # 核心池最高仓位
    cash_min: float = 0.10             # 现金最低 10%
    cash_high_when_few_a: float = 0.20  # ValuationTier=A标的<6时
    cash_high_when_all_c: float = 0.30  # 全市场估值脆弱时
    cash_low_when_accel: float = 0.10   # 加速期标的>=4时

    # 调仓节奏
    initial_position_ratio: float = 0.50  # 首次建仓：目标仓位的50%
    monthly_add_max: float = 0.01      # 每月最多加仓 +1%
    quarterly_add_max: float = 0.03    # 单季度最多加仓 +3%
    monthly_adjust_max: float = 0.03   # 每月最多调整总资产的3%

    # 减仓规则
    light_reduce_ratio: float = 0.30   # 轻度减仓 -30%
    heavy_reduce_ratio: float = 0.50   # 重度减仓 -50%


# ============================================================================
# A4 宏观慢变量过滤器 配置
# ============================================================================

@dataclass(frozen=True)
class MacroConfig:
    """A4 宏观慢变量过滤器参数"""

    # MacroRiskFactor 映射
    factor_map: Dict[int, float] = field(default_factory=lambda: {
        3: 1.10,    # 强顺风
        2: 1.05,
        1: 1.00,
        0: 0.90,
        -1: 0.85,
        -2: 0.80,
        -3: 0.75,   # 强逆风
    })

    # FRED series IDs（美股宏观数据）
    fred_10y: str = "DGS10"
    fred_2y: str = "DGS2"
    fred_real_yield: str = "DFII10"
    fred_hy_spread: str = "BAMLH0A0HYM2"
    fred_m2: str = "M2SL"


# ============================================================================
# A7 极端风险模块 配置
# ============================================================================

@dataclass(frozen=True)
class TailRiskConfig:
    """A7 极端风险与黑天鹅模块参数"""

    # TailRiskFactor 映射
    normal_factor: float = 1.0
    alert_factor: float = 0.9
    tense_factor: float = 0.8
    crisis_factor: float = 0.6

    # 流动性压力阈值
    vix_alert: float = 25.0
    vix_tense: float = 35.0
    vix_crisis: float = 45.0

    # 危机状态约束
    crisis_svi_min: float = 85.0       # 危机时只保留 SVI >= 85
    crisis_single_stock_max: float = 0.05  # 危机时单票上限 5%
    crisis_cash_min: float = 0.40      # 危机时现金 >= 40%


# ============================================================================
# A6 跨市场适配 配置
# ============================================================================

@dataclass(frozen=True)
class MarketParams:
    """单市场参数"""
    svi_threshold: float = 75.0
    single_stock_max: float = 0.08
    theme_bucket_max: float = 0.30
    qpeg_max: float = 1.8
    macro_weight: str = "medium"       # low / medium / high
    turnover_target: float = 0.40

MARKET_PARAMS: Dict[str, MarketParams] = {
    "US": MarketParams(
        svi_threshold=75.0, single_stock_max=0.08,
        theme_bucket_max=0.30, qpeg_max=1.8,
        macro_weight="medium", turnover_target=0.40,
    ),
    "HK": MarketParams(
        svi_threshold=80.0, single_stock_max=0.06,
        theme_bucket_max=0.25, qpeg_max=1.5,
        macro_weight="high", turnover_target=0.50,
    ),
    "CN": MarketParams(
        svi_threshold=80.0, single_stock_max=0.05,
        theme_bucket_max=0.20, qpeg_max=1.3,
        macro_weight="high", turnover_target=0.60,
    ),
}


# ============================================================================
# A8 慢变量主题轮动 配置
# ============================================================================

@dataclass(frozen=True)
class RotationConfig:
    """A8 慢变量主题轮动参数"""
    z_strong_positive: float = 1.0     # Z >= +1 → +10%
    z_mild_positive: float = 0.5       # +0.5 <= Z < +1 → +5%
    z_mild_negative: float = -0.5      # -1 <= Z <= -0.5 → -5%
    z_strong_negative: float = -1.0    # Z < -1 → -10%
    max_bucket_weight: float = 0.30    # 单桶最大30%


# ============================================================================
# 全局设置
# ============================================================================

@dataclass
class Settings:
    """SVIP 主配置"""
    svi: SVIConfig = field(default_factory=SVIConfig)
    valuation: ValuationConfig = field(default_factory=ValuationConfig)
    acceleration: AccelerationConfig = field(default_factory=AccelerationConfig)
    weight: WeightConfig = field(default_factory=WeightConfig)
    macro: MacroConfig = field(default_factory=MacroConfig)
    tail_risk: TailRiskConfig = field(default_factory=TailRiskConfig)
    rotation: RotationConfig = field(default_factory=RotationConfig)

    # API Keys
    fred_api_key: str = field(
        default_factory=lambda: os.getenv("FRED_API_KEY", "")
    )

    # 数据库路径
    china_db_path: str = field(
        default_factory=lambda: os.getenv(
            "CHINA_DB_PATH", os.path.join("..", "database", "china_a_stocks.db")
        )
    )
    us_db_path: str = field(
        default_factory=lambda: os.getenv(
            "US_DB_PATH", os.path.join("..", "database", "us_stocks_financial_data.db")
        )
    )

    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    @classmethod
    def load(cls) -> "Settings":
        return cls()


settings = Settings.load()
