"""
SVIP v1.0 — 安装验证脚本

检查系统是否正确安装和配置。
"""
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """检查所有模块是否可导入"""
    print("🔍 检查模块导入...")
    try:
        from config import settings
        from src import models
        from src import svi_engine
        from src import valuation_engine
        from src import acceleration_engine
        from src import weight_engine
        from src import macro_filter
        from src import tail_risk
        from src import rotation_engine
        from src import portfolio_engine
        from src import report_generator
        print("   ✅ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
        return False


def check_data_files():
    """检查数据文件是否存在"""
    print("\n📁 检查数据文件...")
    files = [
        "data/slow_variables.yaml",
        "data/theme_buckets.yaml",
        "data/sample_stocks.yaml",
        "data/macro_inputs.yaml",
    ]
    all_exist = True
    for f in files:
        if os.path.exists(f):
            print(f"   ✅ {f}")
        else:
            print(f"   ❌ {f} 不存在")
            all_exist = False
    return all_exist


def check_config():
    """检查配置是否正确"""
    print("\n⚙️  检查配置...")
    try:
        from config.settings import settings
        print(f"   ✅ SVI 核心池阈值: {settings.svi.core_threshold}")
        print(f"   ✅ 估值 FCF Yield 下限: {settings.valuation.fcf_yield_min:.1%}")
        print(f"   ✅ 单票上限: {settings.weight.single_stock_max:.0%}")
        print(f"   ✅ 主题桶上限: {settings.weight.theme_bucket_max:.0%}")
        return True
    except Exception as e:
        print(f"   ❌ 配置错误: {e}")
        return False


def run_simple_test():
    """运行简单功能测试"""
    print("\n🧪 运行功能测试...")
    try:
        from src.svi_engine import compute_svi
        from src.valuation_engine import compute_valuation
        from src.models import SVILevel, ValuationTier

        # 测试 SVI
        svi = compute_svi(
            symbol="TEST",
            market="US",
            roic_10y_median=0.25,
            fcf_conversion=0.90,
            gross_margin_std=0.02,
            debt_to_equity=0.50,
            moat_rating=85,
            demand_rigidity_rating=80,
            substitution_risk_rating=20,
        )
        assert svi.passed_hard_screen is True
        # SVI 可能在 CORE 或 WATCH，只要通过硬筛选即可
        print(f"   ✅ SVI 计算: {svi.total:.1f} [{svi.level.value}]")

        # 测试 A1
        val = compute_valuation(
            symbol="TEST",
            fcf_yield=0.04,
            pe_ratio=28,
            growth_rate=0.12,
            svi_score=svi.total,
        )
        assert val.tier in (ValuationTier.A, ValuationTier.B)
        print(f"   ✅ 估值评估: Tier {val.tier.value}, QPEG={val.qpeg:.2f}")

        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("  SVIP v1.0 安装验证")
    print("=" * 60)

    results = []
    results.append(("模块导入", check_imports()))
    results.append(("数据文件", check_data_files()))
    results.append(("配置检查", check_config()))
    results.append(("功能测试", run_simple_test()))

    print("\n" + "=" * 60)
    print("  验证结果")
    print("=" * 60)
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name:12s} {status}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 系统验证通过！可以运行 python run_svip.py")
    else:
        print("\n⚠️  部分检查失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
