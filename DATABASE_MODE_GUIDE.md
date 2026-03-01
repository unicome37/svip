# SVIP 数据库模式使用指南

## 概述

SVIP v1.0 现在支持两种数据输入方式：

1. **YAML模式**（原有方式）：手动编写YAML文件，包含完整的财务和估值数据
2. **数据库模式**（新增）：从本地SQLite数据库自动提取财务数据

数据库模式参考了AIRS-X的数据访问架构，实现了与慢变量统一投资框架的无缝集成。

## 数据库模式优势

- ✅ 自动从数据库提取10年历史财务数据
- ✅ 自动计算ROIC、FCF转化率、毛利率波动等指标
- ✅ 支持A股和美股两个数据库
- ✅ 批量处理大量股票
- ✅ 数据一致性更好，减少人工输入错误

## 快速开始

### 1. 准备数据库

确保以下数据库文件存在：

```
project/
├── database/
│   ├── china_a_stocks.db          # A股数据库（5,692家公司）
│   └── us_stocks_financial_data.db # 美股数据库（27,846家公司）
```

### 2. 创建股票列表文件

创建一个文本文件，每行一个股票代码：

```txt
# stocks_cn.txt
000001
600519
000858
600036
```

或美股：

```txt
# stocks_us.txt
AAPL
MSFT
NVDA
V
UNH
```

### 3. 创建主题映射文件（可选）

如果需要指定慢变量主题桶，创建YAML映射文件：

```yaml
# theme_map.yaml
stocks:
  "000001": "金融制度/支付清算"
  "600519": "品牌/代际消费"
  "AAPL": "AI/算力密度"
  "MSFT": "AI/算力密度"
```

### 4. 运行SVIP

```bash
# A股分析
python run_svip_db.py --stocks-list stocks_cn.txt --market CN --theme-map theme_map.yaml

# 美股分析
python run_svip_db.py --stocks-list stocks_us.txt --market US --theme-map theme_map.yaml

# 不保存报告（仅控制台输出）
python run_svip_db.py --stocks-list stocks_cn.txt --market CN --no-save
```

## 命令行参数

### 数据源选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `--yaml` | 使用YAML文件（原有模式） | `--yaml data/sample_stocks.yaml` |
| `--stocks-list` | 使用股票代码列表文件（数据库模式） | `--stocks-list stocks.txt` |

### 数据库选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--china-db` | A股数据库路径 | `../database/china_a_stocks.db` |
| `--us-db` | 美股数据库路径 | `../database/us_stocks_financial_data.db` |

### 其他选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--theme-map` | 股票-主题映射文件 | 无 |
| `--macro` | 宏观数据YAML文件 | `data/macro_inputs.yaml` |
| `--market` | 目标市场（US/CN/HK） | `US` |
| `--no-save` | 不保存Markdown报告 | False |

## 数据库字段映射

### A股数据库 → SVIP指标

| SVIP指标 | 数据库来源 | 计算方法 |
|---------|-----------|---------|
| roic_10y_median | financial_data表 | 10年净利润/投入资本的中位数 |
| fcf_conversion | financial_data表 | (经营现金流 - 资本开支) / 净利润 |
| gross_margin_std | financial_data表 | 营业利润率的标准差 |
| debt_to_equity | financial_data表 | 总负债 / (总资产 - 总负债) |
| fcf_yield | market_data表 | FCF / 市值 |
| pe_ratio | market_data表 | pe_ratio_ttm字段 |
| growth_rate | financial_data表 | 最近3年营收CAGR |

### 美股数据库 → SVIP指标

| SVIP指标 | Compustat字段 | 说明 |
|---------|--------------|------|
| roic_10y_median | ni, at, lt | 净利润 / (总资产 - 总负债) |
| fcf_conversion | oancf, capx, ni | (经营现金流 - 资本开支) / 净利润 |
| gross_margin_std | revt, oiadp | 营业利润率标准差 |
| debt_to_equity | at, lt | 总负债 / 权益 |
| fcf_yield | oancf, capx, prcc_f, csho | FCF / 市值 |
| pe_ratio | prcc_f, epsfi | 价格 / 每股收益 |
| growth_rate | revt | 营收CAGR |

## 数据限制与注意事项

### 自动计算的指标

数据库模式可以自动计算以下指标：
- ✅ ROIC 10年中位数
- ✅ FCF转化率
- ✅ 毛利率波动
- ✅ 资产负债率
- ✅ FCF Yield
- ✅ PE Ratio
- ✅ 营收增长率
- ✅ 资本开支时间序列

### 需要额外数据的指标

以下指标需要额外数据源或人工评估，数据库模式使用默认值：

| 指标 | 默认值 | 说明 |
|------|--------|------|
| market_share | 0.0 | 需要行业数据 |
| cr4 | 0.0 | 需要行业集中度数据 |
| moat_rating | 50 | 需要定性评估 |
| demand_rigidity_rating | 50 | 需要定性评估 |
| substitution_risk_rating | 50 | 需要定性评估 |
| valuation_percentile | 0.5 | 需要历史估值数据 |
| growth_concentration | 0.3 | 需要分析师预测数据 |
| penetration | None | 需要行业渗透率数据 |
| cost_curve | None | 需要单位成本数据 |

### 改进建议

如果需要更精确的分析，可以：

1. **补充YAML数据**：对关键标的使用YAML模式，手动填充定性指标
2. **扩展数据库**：在数据库中添加行业数据表
3. **混合模式**：数据库提供基础数据，YAML覆盖特定字段

## 工作流集成

### 与AIRS-X集成

```bash
# Step 1: AIRS-X扫描生成候选池
cd project/airs-x
python scan_china.py  # 生成Top100 A股

# Step 2: 提取候选股票代码
# 从AIRS-X报告中提取Grade A/B的股票代码，保存到stocks.txt

# Step 3: SVIP深度筛选
cd project/svip
python run_svip_db.py --stocks-list stocks.txt --market CN --theme-map themes.yaml
```

### 与SPUD-INVEST集成

```bash
# Step 1: SVIP生成核心池
python run_svip_db.py --stocks-list stocks.txt --market CN

# Step 2: 从SVIP报告提取核心池标的

# Step 3: SPUD-INVEST仓位约束
cd project/spud-invest
python run_spud_invest.py --sync-svip
```

## 示例文件

项目提供了以下示例文件：

```
project/svip/data/
├── stocks_list_example.txt      # 股票代码列表示例
├── theme_map_example.yaml       # 主题映射示例
├── sample_stocks.yaml           # YAML模式示例（原有）
└── macro_inputs.yaml            # 宏观数据示例
```

## 完整示例

### 示例1：A股核心池筛选

```bash
# 1. 创建股票列表
cat > my_stocks_cn.txt << EOF
000001  # 平安银行
600519  # 贵州茅台
000858  # 五粮液
600036  # 招商银行
601318  # 中国平安
EOF

# 2. 创建主题映射
cat > my_themes.yaml << EOF
stocks:
  "000001": "金融制度/支付清算"
  "600519": "品牌/代际消费"
  "000858": "品牌/代际消费"
  "600036": "金融制度/支付清算"
  "601318": "金融制度/支付清算"
EOF

# 3. 运行分析
python run_svip_db.py \
  --stocks-list my_stocks_cn.txt \
  --market CN \
  --theme-map my_themes.yaml \
  --macro data/macro_inputs.yaml
```

### 示例2：美股科技股筛选

```bash
# 1. 创建股票列表
cat > tech_stocks.txt << EOF
AAPL
MSFT
NVDA
GOOGL
META
AMZN
EOF

# 2. 创建主题映射
cat > tech_themes.yaml << EOF
stocks:
  "AAPL": "AI/算力密度"
  "MSFT": "AI/算力密度"
  "NVDA": "AI/算力密度"
  "GOOGL": "AI/算力密度"
  "META": "AI/算力密度"
  "AMZN": "AI/算力密度"
EOF

# 3. 运行分析
python run_svip_db.py \
  --stocks-list tech_stocks.txt \
  --market US \
  --theme-map tech_themes.yaml
```

## 故障排查

### 问题1：数据库未找到

```
FileNotFoundError: Database not found: ../database/china_a_stocks.db
```

**解决方案**：
- 检查数据库文件是否存在
- 使用 `--china-db` 或 `--us-db` 指定正确路径

### 问题2：股票代码未找到

```
WARNING: 未找到A股公司: 000002
```

**解决方案**：
- 检查股票代码是否正确
- 确认该股票在数据库中存在
- 对于退市股票，从列表中移除

### 问题3：财务数据不完整

```
WARNING: 未找到A股财务数据: 000001
```

**解决方案**：
- 该股票可能是新上市，历史数据不足
- 检查数据库是否包含该股票的财务数据
- 考虑使用YAML模式手动输入数据

## 性能优化

### 批量处理

数据库模式支持批量加载，适合处理大量股票：

```bash
# 一次性分析100只股票
python run_svip_db.py --stocks-list top100.txt --market CN
```

### 数据库索引

确保数据库有适当的索引以提高查询速度：

```sql
-- A股数据库
CREATE INDEX IF NOT EXISTS idx_companies_code ON companies(code);
CREATE INDEX IF NOT EXISTS idx_financial_company_date ON financial_data(company_id, report_date);

-- 美股数据库
CREATE INDEX IF NOT EXISTS idx_companies_tic ON companies(tic);
CREATE INDEX IF NOT EXISTS idx_financial_gvkey_year ON financial_data_annual(gvkey, fyear);
```

## 下一步

1. **扩展数据源**：集成更多数据源（如行业数据、分析师预测）
2. **自动化流程**：编写脚本自动从AIRS-X同步候选池
3. **增量更新**：支持增量更新已有分析结果
4. **可视化**：开发Streamlit仪表盘展示分析结果

## 参考文档

- [慢变量统一投资框架使用说明](../../慢变量统一投资框架使用说明.md)
- [SVIP操作手册](SVIP_操作手册.md)
- [AIRS-X数据库文档](../../airs-x/docs/database.md)

---

*SVIP Database Mode Guide v1.0 — 2026年3月1日*
