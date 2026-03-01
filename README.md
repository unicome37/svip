# SVIP v1.0

[![GitHub](https://img.shields.io/badge/GitHub-unicome37%2Fsvip-blue?logo=github)](https://github.com/unicome37/svip)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.0.0-orange.svg)](https://github.com/unicome37/svip/releases)

> **慢变量投资池系统 (Slow Variable Investment Pool)**  
> 基于 A1-A11 理论体系的结构化投资框架

📚 [完整文档](MANUAL.md) | 🚀 [快速开始](#快速开始) | 📖 [使用指南](USAGE.md) | 🎯 [快速参考](QUICK_REFERENCE.md)

## 系统定位

SVIP 不是选股系统，不是择时系统，不是预测系统。

SVIP 是：

> **在慢变量主导的存在流形中，选择高稳定结构并与之共振的投资框架。**

## 核心理念

### 三条公理

1. **慢变量役使快变量** — 快变量是噪音，慢变量决定长期分布
2. **存在优先于价格** — 价格波动不改变存在本体，结构破坏才改变存在
3. **结构稳定性决定价值** — 价值来自结构的持续性，而非短期增长率

### 慢变量是地形，价格是水流

大多数人盯着水流（涨跌、波动、成交量），但水流的方向早已由地形决定。真正的资本智慧不是预测下一次浪头，而是识别河流的走向。

## 系统架构

### 完整流程（A0-A11）

```
SVI 结构筛选 → A1 估值安全垫 → A2 加速检测 → A3 组合权重
    ↓              ↓              ↓              ↓
  质量因子Q      估值因子V      相位因子P    W=Q×V×P
                                                ↓
                                          约束投影
                                                ↓
                                    A4 宏观过滤 × A7 尾部风险
                                                ↓
                                          最终组合
                                                ↓
                                    A8 主题轮动（季度）
```

### 核心模块

| 模块 | 功能 | 输出 |
|------|------|------|
| **SVI** | 慢变量绑定度评分 | 0-100分，Core/Watch/Block |
| **A1** | 估值安全垫 | ValuationTier A/B/C |
| **A2** | 慢变量加速检测 | PhaseState 加速/稳态/衰减 |
| **A3** | 组合权重引擎 | 目标权重 + 行动 |
| **A4** | 宏观慢变量过滤 | MacroRiskFactor 0.75-1.10 |
| **A7** | 极端风险模块 | TailRiskFactor 0.6-1.0 |
| **A8** | 主题轮动 | 权重调整信号 |

## 快速开始

### 1. 安装

```bash
cd project/svip
pip install -e .
```

### 2. 运行示例

#### YAML模式（原有方式）

```bash
python run_svip.py
```

#### 数据库模式（推荐）

```bash
# A股分析
python run_svip_db.py --stocks-list data/stocks_list_example.txt --market CN

# 美股分析
python run_svip_db.py --stocks-list stocks_us.txt --market US --theme-map data/theme_map_example.yaml
```

### 3. 查看报告

报告保存在 `reports/` 目录，Markdown 格式。

## 使用指南

### YAML模式（原有方式）

```bash
# 使用默认示例数据
python run_svip.py

# 指定股票数据文件
python run_svip.py --stocks data/my_stocks.yaml

# 指定市场（美股/港股/A股）
python run_svip.py --market CN

# 不保存报告（仅控制台输出）
python run_svip.py --no-save
```

### 数据库模式（新增）

```bash
# 从本地数据库加载A股
python run_svip_db.py --stocks-list stocks_cn.txt --market CN --theme-map themes.yaml

# 从本地数据库加载美股
python run_svip_db.py --stocks-list stocks_us.txt --market US --theme-map themes.yaml

# 自定义数据库路径
python run_svip_db.py \
  --stocks-list stocks.txt \
  --market CN \
  --china-db /path/to/china_a_stocks.db \
  --us-db /path/to/us_stocks_financial_data.db
```

**数据库模式优势**：
- ✅ 自动从数据库提取10年历史财务数据
- ✅ 自动计算ROIC、FCF转化率、毛利率波动等指标
- ✅ 支持批量处理大量股票
- ✅ 数据一致性更好，减少人工输入错误

详细说明请参考 [DATABASE_MODE_GUIDE.md](DATABASE_MODE_GUIDE.md)

### 数据文件格式

#### 股票数据 (YAML)

```yaml
stocks:
  - symbol: "MSFT"
    name: "Microsoft"
    market: "US"
    sector: "Tech"
    theme: "AI/算力密度"
    financials:
      roic_10y_median: 0.30      # 10年ROIC中位数
      fcf_conversion: 0.95       # FCF转化率
      gross_margin_std: 0.02     # 毛利率标准差
      debt_to_equity: 0.45       # 资产负债率
      market_share: 0.25         # 市场份额
      cr4: 0.65                  # 行业CR4
      moat_rating: 90            # 护城河评分 (0-100)
      demand_rigidity_rating: 85 # 需求刚性 (0-100)
      substitution_risk_rating: 15 # 替代风险 (0-100)
    valuation:
      fcf_yield: 0.035           # FCF收益率
      pe_ratio: 32               # 市盈率
      growth_rate: 0.14          # 保守内生增长率
      valuation_percentile: 0.70 # 历史估值分位
      growth_concentration: 0.35 # 增长预期集中度
      reinvestment_declining_years: 0 # 再投资回报下降年数
```

#### 宏观数据 (YAML)

```yaml
macro:
  # 利率结构
  yield_spread_10y2y: 0.35    # 10Y-2Y利差
  real_yield: 1.8             # 实际利率
  credit_spread: 3.2          # 信用利差
  
  # 流动性
  m2_yoy: 0.04               # M2同比
  fci: 0.1                   # 金融条件指数
  credit_growth: 0.03         # 信贷增长
  
  # 盈利周期
  earnings_yoy: 0.08          # 盈利同比
  ism_new_orders: 53.5        # ISM新订单

tail_risk:
  vix: 18.5
  credit_spread_change: 0.2
  regulatory_intensity: 10.0
```

## 投资池结构

### 三池分类

| 池 | 条件 | 行动 |
|----|------|------|
| **Core 核心池** | SVI≥75 + 估值非C + 相位非衰减 | 可持有、加仓 |
| **Watch 观察池** | SVI≥60 但估值B或相位稳态 | 等待价格/等待相位 |
| **Block 禁入池** | SVI<60 或估值C或结构破坏 | 不碰/退出 |

### 约束规则

- 单票上限：8%
- 单慢变量主题上限：30%
- 单行业上限：25%
- 核心池总仓位：60%-85%
- 现金下限：10%（机会少时可到30%）

## 调仓协议

### 建仓规则

满足条件：SVI≥75 + 估值非C + 相位非衰减

首次建仓：目标仓位的 50%，剩余 50% 等待加速期或估值下修

### 加仓规则

允许条件：相位进入加速期 + 估值非C

节奏：每月最多 +1%，单季度最多 +3%

### 减仓规则

触发条件：
- 轻度减仓（-30%）：相位→衰减期 或 估值降级
- 重度减仓（-50%）：ROIC连续2年下降 或 毛利结构恶化
- 清仓：行业结构被颠覆 或 牌照壁垒失效 或 SVI<65

### 检查频率

- 季度检查：结构稳定性（ROIC、FCF、毛利）
- 半年检查：估值安全垫
- 年度检查：慢变量方向是否改变

## 跨市场适配

| 参数 | 美股 | 港股 | A股 |
|------|------|------|------|
| SVI阈值 | ≥75 | ≥80 | ≥80 |
| 单票上限 | 8% | 6% | 5% |
| 主题桶上限 | 30% | 25% | 20% |
| QPEG上限 | 1.8 | 1.5 | 1.3 |
| 年换手率目标 | <40% | <50% | <60% |

**关键差异**：A股和港股中，相位权重 > 估值权重；美股相反。

## 慢变量主题桶

系统预设五大主题桶：

1. **AI/算力密度** — AI、云计算、半导体设备、数据中心
2. **老龄化/医疗支付** — 医疗服务、慢病药物、医疗保险
3. **金融制度/支付清算** — 支付网络、信用评级、交易清算
4. **品牌/代际消费** — 高端消费品牌、零售平台
5. **能源转型/电气化** — 可再生能源、电动车、储能

每家公司只能归入一个主桶。

## 项目结构

```
svip/
├── config/
│   └── settings.py          # 所有阈值、权重、约束（禁止随意修改）
├── src/
│   ├── models.py            # 数据结构定义
│   ├── svi_engine.py        # SVI 慢变量指数计算
│   ├── valuation_engine.py  # A1 估值安全垫
│   ├── acceleration_engine.py # A2 慢变量加速检测
│   ├── weight_engine.py     # A3 组合权重引擎
│   ├── macro_filter.py      # A4 宏观慢变量过滤器
│   ├── tail_risk.py         # A7 极端风险模块
│   ├── rotation_engine.py   # A8 慢变量主题轮动
│   ├── portfolio_engine.py  # 组合编排引擎
│   └── report_generator.py  # Markdown 报告生成
├── data/
│   ├── slow_variables.yaml  # 慢变量清单（年度更新）
│   ├── theme_buckets.yaml   # 主题桶定义
│   ├── sample_stocks.yaml   # 示例股票数据
│   └── macro_inputs.yaml    # 宏观数据输入
├── reports/                 # 报告输出目录
├── tests/                   # 单元测试
├── run_svip.py             # 主入口
├── pyproject.toml
└── README.md
```

## MVP 最小可运行版本

如果觉得完整版本太复杂，可以只运行 MVP 四模块：

1. **M1 结构筛选**（年更新）— ROIC≥15%、FCF≥0.8、毛利稳定
2. **M2 估值过滤**（半年更新）— FCF Yield≥3%、QPEG≤1.8
3. **M3 相位判断**（季度更新）— 慢变量代理指标是否仍在扩张
4. **M4 宏观过滤**（月度观察）— 实际利率、流动性、盈利方向

全年只需 4 次操作，维护 4 张表。

## 核心风险（必须承认）

1. SVI 只是结构质量筛选，**不预测收益**
2. 高质量公司在稳态期不会有超额收益
3. 慢变量识别可能滞后或错误
4. 估值安全垫不能防止系统性崩盘
5. 系统会限制极端仓位、抑制短期爆发

## 慢变量统一投资框架

SVIP 是三系统协同框架的 **Stage 1（慢变量筛选）**：

| 阶段 | 系统 | 仓库 | 定位 |
|------|------|------|------|
| **Stage 1** | **SVIP** | [unicome37/svip](https://github.com/unicome37/svip) | 慢变量宇宙筛选 → Core/Watch/Block 池 |
| **Stage 2** | **AIRS-X** | [unicome37/airs-x](https://github.com/unicome37/airs-x) | 深度结构分析 + 存在性审计 → SPUD 评分 + Grade |
| **Stage 3** | **SPUD-INVEST** | [unicome37/spud-invest](https://github.com/unicome37/spud-invest) | 仓位边界约束 → SMI×MTI → 允许风险暴露 |

数据流：
```
SVIP Core 池 → AIRS-X 深度分析 → SPUD-INVEST 仓位约束 → 最终执行组合
```

协同规则：
- **SVIP** 决定"买什么"（结构质量 + 估值 + 相位）
- **AIRS-X** 决定"值不值得买"（SPUD 四维评分 + 存在性审计）
- **SPUD-INVEST** 决定"买多少"（仓位上限 + Core/Overlay 结构）
- 任何一个系统说"不"，都不能建仓

## 理论基础

完整理论体系见：`理论区/理论体系综述与知识脉络_v5.8_20260228.md`

- 第六十八章：慢变量理论体系与识别方法
- 第六十九章：慢变量存在论投资学——从SVIP框架到文明资本论

## 开发与测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/
```

## 许可

本系统基于 SPUD 理论体系构建，仅供学习研究使用。

---

> **投资不是预测未来。投资不是捕捉波动。投资不是追逐热点。**  
> **投资是：在慢变量构成的存在地形中，寻找稳定结构，并与之共振。**  
> **这不是技巧，这是世界观。**

*SVIP v1.0 — 2026年2月28日*
