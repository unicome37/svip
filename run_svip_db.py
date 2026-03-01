"""
SVIP v1.0 — 数据库模式主入口

慢变量投资池系统（Slow Variable Investment Pool）
支持从本地数据库导入股票数据

用法:
    # 从数据库加载指定股票列表
    python run_svip_db.py --stocks-list stocks.txt --market CN
    
    # 从数据库加载并指定主题
    python run_svip_db.py --stocks-list stocks.txt --market US --theme-map themes.yaml
    
    # 混合模式：YAML + 数据库
    python run_svip_db.py --yaml data/sample_stocks.yaml --db-stocks stocks.txt
"""
import argparse
import sys
import os
import yaml
from datetime import datetime
from typing import List, Dict, Tuple

# 确保 src 和 config 可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from src.models import SVIPStock
from src.svi_engine import compute_svi
from src.valuation_engine import compute_valuation
from src.acceleration_engine import compute_acceleration_score
from src.macro_filter import compute_macro_state
from src.tail_risk import compute_tail_risk
from src.portfolio_engine import generate_report
from src.report_generator import save_report
from src.data_loader import validate_stock_themes
from src.db_loader import create_db_loader
from src.airsx_bridge import enrich_batch


def load_yaml(path: str) -> dict:
    """加载YAML文件"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_stocks_list(path: str) -> List[str]:
    """
    加载股票代码列表文件
    
    格式：每行一个股票代码
    支持注释（#开头）
    """
    stocks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                stocks.append(line)
    return stocks


def load_theme_map(path: str) -> Dict[str, str]:
    """
    加载股票-主题映射文件
    
    格式：
    stocks:
      000001: "金融制度/支付清算"
      600519: "品牌/代际消费"
      AAPL: "AI/算力密度"
    """
    data = load_yaml(path)
    return data.get("stocks", {})


def build_stocks_from_db(
    stock_codes: List[str],
    market: str,
    theme_map: Dict[str, str],
    china_db_path: str = None,
    us_db_path: str = None
) -> List[SVIPStock]:
    """
    从数据库构建SVIPStock列表
    
    Args:
        stock_codes: 股票代码列表
        market: 市场 ("CN", "US", "HK")
        theme_map: 股票代码到主题的映射
        china_db_path: A股数据库路径
        us_db_path: 美股数据库路径
    
    Returns:
        SVIPStock列表
    """
    print(f"\n📊 从数据库加载股票数据...")
    
    # 创建数据库加载器
    db_loader = create_db_loader(china_db_path, us_db_path)
    
    try:
        # 连接数据库
        db_loader.connect(market)
        
        # 构建加载列表：[(market, code, theme), ...]
        stock_list = []
        for code in stock_codes:
            theme = theme_map.get(code, "")
            stock_list.append((market, code, theme))
        
        # 批量加载
        stocks_data = db_loader.load_stocks_from_list(stock_list)
        print(f"   成功加载 {len(stocks_data)}/{len(stock_codes)} 只股票")
        
        # AIRS-X 桥接补充主观评估字段
        stocks_data = enrich_batch(stocks_data)
        
        # 转换为SVIPStock
        stocks = []
        for item in stocks_data:
            stock = build_stock_from_data(item)
            if stock:
                stocks.append(stock)
        
        return stocks
    
    finally:
        db_loader.close()


def build_stock_from_data(item: dict) -> SVIPStock:
    """从数据字典构建SVIPStock对象"""
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
    
    # Step 3: A2 加速检测
    accel_data = item.get("acceleration", {})
    acceleration = compute_acceleration_score(
        symbol=item["symbol"],
        theme=item.get("theme", ""),
        penetration_series=accel_data.get("penetration"),
        cost_curve_series=accel_data.get("cost_curve"),
        capex_series=accel_data.get("capex"),
        policy_series=accel_data.get("policy"),
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
    
    return stock


def build_stocks_from_yaml(data: dict) -> List[SVIPStock]:
    """从YAML数据构建SVIPStock列表（兼容原有逻辑）"""
    stocks = []
    for item in data.get("stocks", []):
        stock = build_stock_from_data(item)
        if stock:
            stocks.append(stock)
    return stocks


def print_stock_summary(stocks: List[SVIPStock]):
    """打印股票摘要"""
    print("\n📈 SVI 慢变量指数评分:")
    for s in stocks:
        status = "✅" if s.svi.passed_hard_screen else "❌"
        print(f"   {status} {s.symbol:8s} SVI={s.svi.total:5.1f} [{s.svi.level.value}]"
              f"  ROIC={s.svi.roic_10y_median:.0%}")
    
    print("\n💰 A1 估值安全垫:")
    for s in stocks:
        tier_icon = {"A": "🟢", "B": "🟡", "C": "🔴"}[s.valuation.tier.value]
        flags = f" 红旗×{s.valuation.red_flag_count}" if s.valuation.red_flag_count > 0 else ""
        print(f"   {tier_icon} {s.symbol:8s} Tier={s.valuation.tier.value}"
              f"  FCF_Yield={s.valuation.fcf_yield:.1%}"
              f"  QPEG={s.valuation.qpeg:.2f}{flags}")


def main():
    parser = argparse.ArgumentParser(
        description="SVIP 慢变量投资池系统 - 数据库模式"
    )
    
    # 数据源选项
    data_group = parser.add_mutually_exclusive_group()
    data_group.add_argument(
        "--yaml",
        help="YAML格式股票数据文件",
    )
    data_group.add_argument(
        "--stocks-list",
        help="股票代码列表文件（每行一个代码）",
    )
    
    # 数据库选项
    parser.add_argument(
        "--china-db",
        help="A股数据库路径（默认：../database/china_a_stocks.db）",
    )
    parser.add_argument(
        "--us-db",
        help="美股数据库路径（默认：../database/us_stocks_financial_data.db）",
    )
    
    # 主题映射
    parser.add_argument(
        "--theme-map",
        help="股票-主题映射YAML文件",
    )
    
    # 宏观数据
    parser.add_argument(
        "-m", "--macro",
        default="data/macro_inputs.yaml",
        help="宏观数据 YAML 路径",
    )
    
    # 市场
    parser.add_argument(
        "--market",
        default="US",
        choices=["US", "HK", "CN"],
        help="目标市场",
    )
    
    # 输出选项
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存 Markdown 报告",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  SVIP v1.0 — 慢变量投资池系统（数据库模式）")
    print("  Slow Variable Investment Pool - Database Mode")
    print("=" * 60)
    print()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载股票数据
    stocks = []
    
    if args.yaml:
        # YAML模式
        print(f"📊 加载YAML数据: {args.yaml}")
        yaml_path = os.path.join(base_dir, args.yaml)
        stock_data = load_yaml(yaml_path)
        stocks = build_stocks_from_yaml(stock_data)
        print(f"   共 {len(stocks)} 只股票")
    
    elif args.stocks_list:
        # 数据库模式
        print(f"📊 加载股票列表: {args.stocks_list}")
        list_path = os.path.join(base_dir, args.stocks_list)
        stock_codes = load_stocks_list(list_path)
        print(f"   共 {len(stock_codes)} 只股票代码")
        
        # 加载主题映射
        theme_map = {}
        if args.theme_map:
            theme_path = os.path.join(base_dir, args.theme_map)
            theme_map = load_theme_map(theme_path)
            print(f"   加载主题映射: {len(theme_map)} 条")
        
        # 从数据库加载
        stocks = build_stocks_from_db(
            stock_codes,
            args.market,
            theme_map,
            args.china_db,
            args.us_db
        )
    
    else:
        print("❌ 错误: 必须指定 --yaml 或 --stocks-list")
        parser.print_help()
        sys.exit(1)
    
    if not stocks:
        print("❌ 未加载到任何股票数据")
        sys.exit(1)
    
    # 打印摘要
    print_stock_summary(stocks)
    
    # 加载宏观数据
    print(f"\n🌍 加载宏观数据: {args.macro}")
    macro_path = os.path.join(base_dir, args.macro)
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
        print(f"     {s.symbol:8s} 目标权重={s.target_weight:.1%}"
              f"  行动={s.action.value}")
    
    if report.watch_pool:
        print(f"\n   观察池标的:")
        for s in report.watch_pool:
            print(f"     {s.symbol:8s} [{s.svi.level.value}]")
    
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
