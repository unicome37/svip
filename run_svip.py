"""
SVIP v1.0 — 主入口

慢变量投资池系统（Slow Variable Investment Pool）

用法:
    python run_svip.py                    # 使用示例数据运行
    python run_svip.py --stocks data.yaml # 指定股票数据
    python run_svip.py --market CN        # 指定市场
    python run_svip.py --no-save          # 不保存报告
"""
import argparse
import sys
import os
import yaml
from datetime import datetime

# 确保 src 和 config 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from src.models import SVIPStock, PhaseState
from src.svi_engine import compute_svi
from src.valuation_engine import compute_valuation
from src.acceleration_engine import compute_acceleration_score
from src.macro_filter import compute_macro_state
from src.tail_risk import compute_tail_risk
from src.portfolio_engine import generate_report
from src.report_generator import generate_markdown_report, save_report


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_stocks_from_yaml(data: dict) -> list[SVIPStock]:
    """从 YAML 数据构建 SVIPStock 列表"""
    stocks = []
    for item in data.get("stocks", []):
        fin = item.get("financials", {})
        val = item.get("valuation", {})

        # Step 1: SVI 评分
        svi = compute_svi(
            symbol=item["symbol"],
            market=item.get("market", "US"),
            roic_10y_median=fin.get("roic_10y_median", 0),
            fcf_conversion=fin.get("fcf_conversion", 0),
            gross_margin_std=fin.get("gross_margin_std", 0.1),
            debt_to_equity=fin.get("debt_to_equity", 1.0),
            market_share=fin.get("market_share", 0),
            cr4=fin.get("cr4", 0),
            moat_rating=fin.get("moat_rating", 50),
            demand_rigidity_rating=fin.get("demand_rigidity_rating", 50),
            substitution_risk_rating=fin.get("substitution_risk_rating", 50),
        )

        # Step 2: A1 估值评估
        valuation = compute_valuation(
            symbol=item["symbol"],
            fcf_yield=val.get("fcf_yield", 0),
            pe_ratio=val.get("pe_ratio", 0),
            growth_rate=val.get("growth_rate", 0),
            svi_score=svi.total,
            valuation_percentile=val.get("valuation_percentile", 0.5),
            growth_concentration=val.get("growth_concentration", 0.3),
            reinvestment_declining_years=val.get("reinvestment_declining_years", 0),
        )

        # Step 3: A2 加速检测（使用默认稳态，实际需要时间序列数据）
        acceleration = compute_acceleration_score(
            symbol=item["symbol"],
            theme=item.get("theme", ""),
        )

        stock = SVIPStock(
            symbol=item["symbol"],
            name=item.get("name", ""),
            market=item.get("market", "US"),
            sector=item.get("sector", ""),
            theme=item.get("theme", ""),
            svi=svi,
            valuation=valuation,
            acceleration=acceleration,
        )
        stocks.append(stock)

    return stocks


def main():
    parser = argparse.ArgumentParser(description="SVIP 慢变量投资池系统")
    parser.add_argument(
        "-s", "--stocks",
        default="data/sample_stocks.yaml",
        help="股票数据 YAML 路径",
    )
    parser.add_argument(
        "-m", "--macro",
        default="data/macro_inputs.yaml",
        help="宏观数据 YAML 路径",
    )
    parser.add_argument(
        "--market",
        default="US",
        choices=["US", "HK", "CN"],
        help="目标市场",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存 Markdown 报告",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  SVIP v1.0 — 慢变量投资池系统")
    print("  Slow Variable Investment Pool")
    print("=" * 60)
    print()

    # 加载数据
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stocks_path = os.path.join(base_dir, args.stocks)
    macro_path = os.path.join(base_dir, args.macro)

    print(f"📊 加载股票数据: {args.stocks}")
    stock_data = load_yaml(stocks_path)
    stocks = build_stocks_from_yaml(stock_data)
    print(f"   共 {len(stocks)} 只股票")

    # SVI 结果摘要
    print("\n📈 SVI 慢变量指数评分:")
    for s in stocks:
        status = "✅" if s.svi.passed_hard_screen else "❌"
        print(f"   {status} {s.symbol:6s} SVI={s.svi.total:5.1f} [{s.svi.level.value}]"
              f"  ROIC={s.svi.roic_10y_median:.0%}")

    # 估值结果
    print("\n💰 A1 估值安全垫:")
    for s in stocks:
        tier_icon = {"A": "🟢", "B": "🟡", "C": "🔴"}[s.valuation.tier.value]
        flags = f" 红旗×{s.valuation.red_flag_count}" if s.valuation.red_flag_count > 0 else ""
        print(f"   {tier_icon} {s.symbol:6s} Tier={s.valuation.tier.value}"
              f"  FCF_Yield={s.valuation.fcf_yield:.1%}"
              f"  QPEG={s.valuation.qpeg:.2f}{flags}")

    # 加载宏观数据
    print(f"\n🌍 加载宏观数据: {args.macro}")
    macro_data = load_yaml(macro_path)
    md = macro_data.get("macro", {})
    td = macro_data.get("tail_risk", {})

    macro = compute_macro_state(
        yield_spread=md.get("yield_spread_10y2y"),
        real_yield=md.get("real_yield"),
        credit_spread=md.get("credit_spread"),
        m2_yoy=md.get("m2_yoy"),
        fci=md.get("fci"),
        credit_growth=md.get("credit_growth"),
        earnings_yoy=md.get("earnings_yoy"),
        ism_new_orders=md.get("ism_new_orders"),
    )
    print(f"   宏观评分: {macro.total_score:+d} ({macro.wind.value})"
          f"  MacroRiskFactor={macro.macro_risk_factor:.2f}")

    tail_risk = compute_tail_risk(
        vix=td.get("vix"),
        credit_spread_change=td.get("credit_spread_change"),
        regulatory_intensity=td.get("regulatory_intensity", 0),
    )
    print(f"   尾部风险: {tail_risk.state.value}"
          f"  TailRiskFactor={tail_risk.tail_risk_factor:.2f}")

    # 生成报告
    print(f"\n🔧 构建组合 (市场: {args.market})...")
    report = generate_report(stocks, macro, tail_risk, market=args.market)

    # 控制台输出
    alloc = report.allocation
    print(f"\n📋 组合配置:")
    print(f"   总股票仓位: {alloc.total_equity:.1%}")
    print(f"   现金: {alloc.cash_weight:.1%}")
    print(f"   核心池: {alloc.core_pool_weight:.1%}")
    print(f"   仓位上限: {alloc.final_equity_ceiling:.1%}")

    print(f"\n   核心池标的:")
    for s in report.core_pool:
        print(f"     {s.symbol:6s} 目标权重={s.target_weight:.1%}"
              f"  行动={s.action.value}")

    if report.watch_pool:
        print(f"\n   观察池标的:")
        for s in report.watch_pool:
            print(f"     {s.symbol:6s} [{s.svi.level.value}]")

    if alloc.violations:
        print(f"\n⚠️  违规警告:")
        for v in alloc.violations:
            print(f"   {v}")

    # 保存报告
    if not args.no_save:
        report_dir = os.path.join(base_dir, "reports")
        filepath = save_report(report, report_dir)
        print(f"\n📄 报告已保存: {filepath}")

    print("\n" + "=" * 60)
    print("  完成。慢变量是地形，价格是水流。")
    print("=" * 60)


if __name__ == "__main__":
    main()
