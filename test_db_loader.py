"""
测试数据库加载器

验证从本地数据库加载股票数据的功能
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.db_loader import create_db_loader


def test_china_stock():
    """测试A股数据加载"""
    print("=" * 60)
    print("测试A股数据加载")
    print("=" * 60)
    
    loader = create_db_loader()
    
    try:
        # 测试加载平安银行
        print("\n加载 000001 (平安银行)...")
        stock_data = loader.load_china_stock("000001", "金融制度/支付清算")
        
        if stock_data:
            print(f"✅ 成功加载: {stock_data['name']}")
            print(f"   市场: {stock_data['market']}")
            print(f"   主题: {stock_data['theme']}")
            print(f"   ROIC 10年中位数: {stock_data['financials']['roic_10y_median']:.2%}")
            print(f"   FCF转化率: {stock_data['financials']['fcf_conversion']:.2f}")
            print(f"   毛利率波动: {stock_data['financials']['gross_margin_std']:.2%}")
            print(f"   FCF Yield: {stock_data['valuation']['fcf_yield']:.2%}")
            print(f"   PE Ratio: {stock_data['valuation']['pe_ratio']:.1f}")
        else:
            print("❌ 加载失败")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        loader.close()


def test_us_stock():
    """测试美股数据加载"""
    print("\n" + "=" * 60)
    print("测试美股数据加载")
    print("=" * 60)
    
    loader = create_db_loader()
    
    try:
        # 测试加载苹果
        print("\n加载 AAPL (Apple)...")
        stock_data = loader.load_us_stock("AAPL", "AI/算力密度")
        
        if stock_data:
            print(f"✅ 成功加载: {stock_data['name']}")
            print(f"   市场: {stock_data['market']}")
            print(f"   主题: {stock_data['theme']}")
            print(f"   ROIC 10年中位数: {stock_data['financials']['roic_10y_median']:.2%}")
            print(f"   FCF转化率: {stock_data['financials']['fcf_conversion']:.2f}")
            print(f"   毛利率波动: {stock_data['financials']['gross_margin_std']:.2%}")
            print(f"   FCF Yield: {stock_data['valuation']['fcf_yield']:.2%}")
            print(f"   PE Ratio: {stock_data['valuation']['pe_ratio']:.1f}")
        else:
            print("❌ 加载失败")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        loader.close()


def test_batch_load():
    """测试批量加载"""
    print("\n" + "=" * 60)
    print("测试批量加载")
    print("=" * 60)
    
    loader = create_db_loader()
    
    try:
        stock_list = [
            ("CN", "000001", "金融制度/支付清算"),
            ("CN", "600519", "品牌/代际消费"),
            ("US", "AAPL", "AI/算力密度"),
            ("US", "MSFT", "AI/算力密度"),
        ]
        
        print(f"\n批量加载 {len(stock_list)} 只股票...")
        stocks = loader.load_stocks_from_list(stock_list)
        
        print(f"✅ 成功加载 {len(stocks)}/{len(stock_list)} 只股票")
        for stock in stocks:
            print(f"   - {stock['symbol']:8s} {stock['name']:20s} [{stock['market']}]")
    
    except Exception as e:
        print(f"❌ 错误: {e}")
    
    finally:
        loader.close()


if __name__ == "__main__":
    print("\nSVIP 数据库加载器测试\n")
    
    # 测试A股
    test_china_stock()
    
    # 测试美股
    test_us_stock()
    
    # 测试批量加载
    test_batch_load()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
