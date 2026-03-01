"""
SVIP v1.0 — Database Loader

从本地数据库导入股票数据，支持A股和美股数据库。
参考AIRS-X的数据库访问模式，为SVIP提供数据库输入能力。
"""
import os
import sqlite3
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
from dataclasses import dataclass
import logging

from src.models import SVIPStock, Market

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """数据库配置"""
    china_db_path: str
    us_db_path: str


class SVIPDatabaseLoader:
    """
    SVIP数据库加载器
    
    从本地SQLite数据库加载股票财务数据，转换为SVIP所需格式。
    支持A股和美股两个数据库。
    """
    
    def __init__(
        self,
        china_db_path: Optional[str] = None,
        us_db_path: Optional[str] = None
    ):
        """
        初始化数据库加载器
        
        Args:
            china_db_path: A股数据库路径
            us_db_path: 美股数据库路径
        """
        # 默认路径：project/database/
        if china_db_path is None:
            china_db_path = str(
                Path(__file__).resolve().parent.parent.parent / "database" / "china_a_stocks.db"
            )
        if us_db_path is None:
            us_db_path = str(
                Path(__file__).resolve().parent.parent.parent / "database" / "us_stocks_financial_data.db"
            )
        
        self.config = DatabaseConfig(
            china_db_path=china_db_path,
            us_db_path=us_db_path
        )
        self.china_conn = None
        self.us_conn = None
    
    def connect(self, market: str = "CN"):
        """建立数据库连接"""
        if market in ("CN", "HK"):
            if not os.path.exists(self.config.china_db_path):
                raise FileNotFoundError(f"A股数据库未找到: {self.config.china_db_path}")
            self.china_conn = sqlite3.connect(self.config.china_db_path)
            self.china_conn.row_factory = sqlite3.Row
            logger.info(f"已连接A股数据库: {self.config.china_db_path}")
        
        if market == "US":
            if not os.path.exists(self.config.us_db_path):
                raise FileNotFoundError(f"美股数据库未找到: {self.config.us_db_path}")
            self.us_conn = sqlite3.connect(self.config.us_db_path)
            self.us_conn.row_factory = sqlite3.Row
            logger.info(f"已连接美股数据库: {self.config.us_db_path}")
    
    def close(self):
        """关闭数据库连接"""
        if self.china_conn:
            self.china_conn.close()
            self.china_conn = None
        if self.us_conn:
            self.us_conn.close()
            self.us_conn = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    # =========================================================================
    # A股数据加载
    # =========================================================================
    
    def load_china_stock(self, code: str, theme: str = "") -> Optional[Dict[str, Any]]:
        """
        从A股数据库加载单只股票数据
        
        Args:
            code: 股票代码 (如: '000001')
            theme: 慢变量主题桶
        
        Returns:
            股票数据字典，格式与YAML兼容
        """
        if not self.china_conn:
            self.connect("CN")
        
        # 获取公司信息
        company = self._get_china_company_info(code)
        if not company:
            logger.warning(f"未找到A股公司: {code}")
            return None
        
        # 获取财务数据
        financials = self._get_china_financials(company['company_id'])
        if not financials:
            logger.warning(f"未找到A股财务数据: {code}")
            return None
        
        # 获取市场数据
        market_data = self._get_china_market_data(company['company_id'])
        
        # 转换为SVIP格式
        return self._convert_china_to_svip_format(
            company, financials, market_data, theme
        )
    
    def _get_china_company_info(self, code: str) -> Optional[Dict]:
        """获取A股公司信息"""
        query = "SELECT * FROM companies WHERE code = ?"
        cursor = self.china_conn.execute(query, (code,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _get_china_financials(
        self,
        company_id: int,
        years: int = 10
    ) -> List[Dict]:
        """获取A股历史财务数据（年报）"""
        query = """
        SELECT * FROM financial_data
        WHERE company_id = ? AND report_type = 'annual'
        ORDER BY report_date DESC
        LIMIT ?
        """
        cursor = self.china_conn.execute(query, (company_id, years))
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_china_market_data(self, company_id: int) -> Optional[Dict]:
        """获取A股最新市场数据"""
        query = """
        SELECT * FROM market_data
        WHERE company_id = ?
        ORDER BY trade_date DESC
        LIMIT 1
        """
        cursor = self.china_conn.execute(query, (company_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _convert_china_to_svip_format(
        self,
        company: Dict,
        financials: List[Dict],
        market_data: Optional[Dict],
        theme: str
    ) -> Dict[str, Any]:
        """将A股数据转换为SVIP格式"""
        latest = financials[0] if financials else {}
        
        # 计算10年ROIC中位数
        roic_10y_median = self._calculate_roic_median(financials)
        
        # 计算FCF转化率
        fcf_conversion = self._calculate_fcf_conversion(financials)
        
        # 计算毛利率波动
        gross_margin_std = self._calculate_margin_stability(financials)
        
        # 计算估值指标
        fcf_yield, pe_ratio, growth_rate = self._calculate_valuation_metrics(
            financials, market_data
        )
        
        return {
            "symbol": company['code'],
            "name": company['name'],
            "market": "CN",
            "sector": company.get('sector', ''),
            "theme": theme,
            "financials": {
                "roic_10y_median": roic_10y_median,
                "fcf_conversion": fcf_conversion,
                "gross_margin_std": gross_margin_std,
                "debt_to_equity": self._calculate_debt_ratio(latest),
                "market_share": 0.0,  # 需要额外数据源
                "cr4": 0.0,  # 需要额外数据源
                "moat_rating": 50,  # 默认值，需要人工评估
                "demand_rigidity_rating": 50,
                "substitution_risk_rating": 50,
            },
            "valuation": {
                "fcf_yield": fcf_yield,
                "pe_ratio": pe_ratio,
                "growth_rate": growth_rate,
                "valuation_percentile": 0.5,  # 需要历史估值数据
                "growth_concentration": 0.3,  # 需要分析师预测数据
                "reinvestment_declining_years": 0,
            },
            "acceleration": {
                # 加速数据需要额外时间序列，暂时留空
                "penetration": None,
                "cost_curve": None,
                "capex": self._extract_capex_series(financials),
            }
        }
    
    # =========================================================================
    # 美股数据加载
    # =========================================================================
    
    def load_us_stock(self, ticker: str, theme: str = "") -> Optional[Dict[str, Any]]:
        """
        从美股数据库加载单只股票数据
        
        Args:
            ticker: 股票代码 (如: 'AAPL')
            theme: 慢变量主题桶
        
        Returns:
            股票数据字典，格式与YAML兼容
        """
        if not self.us_conn:
            self.connect("US")
        
        # 获取公司信息
        company = self._get_us_company_info(ticker)
        if not company:
            logger.warning(f"未找到美股公司: {ticker}")
            return None
        
        # 获取财务数据
        financials = self._get_us_financials(company['gvkey'])
        if not financials:
            logger.warning(f"未找到美股财务数据: {ticker}")
            return None
        
        # 转换为SVIP格式
        return self._convert_us_to_svip_format(company, financials, theme)
    
    def _get_us_company_info(self, ticker: str) -> Optional[Dict]:
        """获取美股公司信息"""
        clean_ticker = ticker.replace(".", "").upper()
        query = "SELECT * FROM companies WHERE UPPER(tic) = ? LIMIT 1"
        cursor = self.us_conn.execute(query, (clean_ticker,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _get_us_financials(self, gvkey: str, years: int = 10) -> List[Dict]:
        """获取美股历史财务数据（年报）"""
        query = """
        SELECT * FROM financial_data_annual
        WHERE gvkey = ?
        ORDER BY fyear DESC
        LIMIT ?
        """
        cursor = self.us_conn.execute(query, (gvkey, years))
        return [dict(row) for row in cursor.fetchall()]
    
    def _convert_us_to_svip_format(
        self,
        company: Dict,
        financials: List[Dict],
        theme: str
    ) -> Dict[str, Any]:
        """将美股数据转换为SVIP格式"""
        latest = financials[0] if financials else {}
        
        # 计算指标（美股字段名不同）
        roic_10y_median = self._calculate_us_roic_median(financials)
        fcf_conversion = self._calculate_us_fcf_conversion(financials)
        gross_margin_std = self._calculate_us_margin_stability(financials)
        fcf_yield, pe_ratio, growth_rate = self._calculate_us_valuation_metrics(financials)
        
        return {
            "symbol": company['tic'],
            "name": company['conm'],
            "market": "US",
            "sector": "",  # Compustat不直接提供
            "theme": theme,
            "financials": {
                "roic_10y_median": roic_10y_median,
                "fcf_conversion": fcf_conversion,
                "gross_margin_std": gross_margin_std,
                "debt_to_equity": self._calculate_us_debt_ratio(latest),
                "market_share": 0.0,
                "cr4": 0.0,
                "moat_rating": 50,
                "demand_rigidity_rating": 50,
                "substitution_risk_rating": 50,
            },
            "valuation": {
                "fcf_yield": fcf_yield,
                "pe_ratio": pe_ratio,
                "growth_rate": growth_rate,
                "valuation_percentile": 0.5,
                "growth_concentration": 0.3,
                "reinvestment_declining_years": 0,
            },
            "acceleration": {
                "penetration": None,
                "cost_curve": None,
                "capex": self._extract_us_capex_series(financials),
            }
        }
    
    # =========================================================================
    # 批量加载
    # =========================================================================
    
    def load_stocks_from_list(
        self,
        stock_list: List[Tuple[str, str, str]]
    ) -> List[Dict[str, Any]]:
        """
        批量加载股票数据
        
        Args:
            stock_list: [(market, code, theme), ...] 列表
                market: "CN" 或 "US"
                code: 股票代码
                theme: 慢变量主题桶
        
        Returns:
            股票数据字典列表
        """
        stocks = []
        for market, code, theme in stock_list:
            try:
                if market in ("CN", "HK"):
                    stock_data = self.load_china_stock(code, theme)
                elif market == "US":
                    stock_data = self.load_us_stock(code, theme)
                else:
                    logger.warning(f"不支持的市场: {market}")
                    continue
                
                if stock_data:
                    stocks.append(stock_data)
            except Exception as e:
                logger.error(f"加载股票 {market}:{code} 失败: {e}")
        
        return stocks
    
    # =========================================================================
    # 财务指标计算（A股）
    # =========================================================================
    
    def _calculate_roic_median(self, financials: List[Dict]) -> float:
        """计算10年ROIC中位数"""
        roics = []
        for f in financials:
            net_profit = f.get('net_profit')
            total_assets = f.get('total_assets')
            total_liabilities = f.get('total_liabilities')
            
            if all([net_profit, total_assets, total_liabilities]):
                invested_capital = total_assets - total_liabilities
                if invested_capital > 0:
                    roic = net_profit / invested_capital
                    roics.append(roic)
        
        if roics:
            roics.sort()
            mid = len(roics) // 2
            return roics[mid] if len(roics) % 2 == 1 else (roics[mid-1] + roics[mid]) / 2
        return 0.0
    
    def _calculate_fcf_conversion(self, financials: List[Dict]) -> float:
        """计算FCF转化率"""
        if not financials:
            return 0.0
        
        latest = financials[0]
        net_profit = latest.get('net_profit', 0)
        operating_cf = latest.get('operating_cash_flow', 0)
        capex = latest.get('capex', 0)
        
        if net_profit and net_profit > 0:
            fcf = operating_cf - abs(capex)
            return fcf / net_profit
        return 0.0
    
    def _calculate_margin_stability(self, financials: List[Dict]) -> float:
        """计算毛利率波动（标准差）"""
        margins = []
        for f in financials:
            revenue = f.get('revenue')
            operating_profit = f.get('operating_profit')
            if revenue and operating_profit and revenue > 0:
                margin = operating_profit / revenue
                margins.append(margin)
        
        if len(margins) >= 3:
            mean = sum(margins) / len(margins)
            variance = sum((m - mean) ** 2 for m in margins) / len(margins)
            return variance ** 0.5
        return 0.0
    
    def _calculate_debt_ratio(self, financial: Dict) -> float:
        """计算资产负债率"""
        total_assets = financial.get('total_assets', 0)
        total_liabilities = financial.get('total_liabilities', 0)
        if total_assets and total_assets > 0:
            equity = total_assets - total_liabilities
            return total_liabilities / equity if equity > 0 else 0.0
        return 0.0
    
    def _calculate_valuation_metrics(
        self,
        financials: List[Dict],
        market_data: Optional[Dict]
    ) -> Tuple[float, float, float]:
        """计算估值指标：FCF Yield, PE, Growth Rate"""
        fcf_yield = 0.0
        pe_ratio = 0.0
        growth_rate = 0.0
        
        if market_data and financials:
            latest = financials[0]
            market_cap = market_data.get('market_cap')
            
            # FCF Yield
            if market_cap and market_cap > 0:
                operating_cf = latest.get('operating_cash_flow', 0)
                capex = latest.get('capex', 0)
                fcf = operating_cf - abs(capex)
                fcf_yield = fcf / market_cap if fcf > 0 else 0.0
            
            # PE Ratio
            pe_ratio = market_data.get('pe_ratio_ttm', 0.0) or 0.0
            
            # Growth Rate (简单计算：最近3年营收CAGR)
            if len(financials) >= 3:
                revenues = [f.get('revenue', 0) for f in financials[:3]]
                if revenues[0] and revenues[-1] and revenues[-1] > 0:
                    growth_rate = (revenues[0] / revenues[-1]) ** (1/2) - 1
        
        return fcf_yield, pe_ratio, growth_rate
    
    def _extract_capex_series(self, financials: List[Dict]) -> Optional[List[float]]:
        """提取资本开支时间序列（最近5年）"""
        capex_list = []
        for f in financials[:5]:
            capex = f.get('capex')
            if capex:
                capex_list.append(abs(capex))
        return capex_list if capex_list else None
    
    # =========================================================================
    # 财务指标计算（美股）
    # =========================================================================
    
    def _calculate_us_roic_median(self, financials: List[Dict]) -> float:
        """计算美股10年ROIC中位数"""
        roics = []
        for f in financials:
            # Compustat字段: ni (净利润), at (总资产), lt (总负债)
            ni = f.get('ni') or f.get('ib')
            at = f.get('at')
            lt = f.get('lt')
            
            if all([ni, at, lt]):
                invested_capital = at - lt
                if invested_capital > 0:
                    roic = ni / invested_capital
                    roics.append(roic)
        
        if roics:
            roics.sort()
            mid = len(roics) // 2
            return roics[mid] if len(roics) % 2 == 1 else (roics[mid-1] + roics[mid]) / 2
        return 0.0
    
    def _calculate_us_fcf_conversion(self, financials: List[Dict]) -> float:
        """计算美股FCF转化率"""
        if not financials:
            return 0.0
        
        latest = financials[0]
        ni = latest.get('ni') or latest.get('ib', 0)
        oancf = latest.get('oancf', 0)  # 经营现金流
        capx = latest.get('capx', 0)  # 资本开支
        
        if ni and ni > 0:
            fcf = oancf - abs(capx)
            return fcf / ni
        return 0.0
    
    def _calculate_us_margin_stability(self, financials: List[Dict]) -> float:
        """计算美股毛利率波动"""
        margins = []
        for f in financials:
            # revt (营收), oiadp (营业利润)
            revt = f.get('revt') or f.get('sale')
            oiadp = f.get('oiadp') or f.get('oibdp')
            if revt and oiadp and revt > 0:
                margin = oiadp / revt
                margins.append(margin)
        
        if len(margins) >= 3:
            mean = sum(margins) / len(margins)
            variance = sum((m - mean) ** 2 for m in margins) / len(margins)
            return variance ** 0.5
        return 0.0
    
    def _calculate_us_debt_ratio(self, financial: Dict) -> float:
        """计算美股资产负债率"""
        at = financial.get('at', 0)  # 总资产
        lt = financial.get('lt', 0)  # 总负债
        if at and at > 0:
            equity = at - lt
            return lt / equity if equity > 0 else 0.0
        return 0.0
    
    def _calculate_us_valuation_metrics(
        self,
        financials: List[Dict]
    ) -> Tuple[float, float, float]:
        """计算美股估值指标"""
        fcf_yield = 0.0
        pe_ratio = 0.0
        growth_rate = 0.0
        
        if financials:
            latest = financials[0]
            
            # FCF Yield (使用prcc_f财年末价格和csho流通股)
            prcc_f = latest.get('prcc_f')  # 财年末价格
            csho = latest.get('csho')  # 流通股数（百万股）
            if prcc_f and csho:
                market_cap = prcc_f * csho  # 百万美元
                oancf = latest.get('oancf', 0)
                capx = latest.get('capx', 0)
                fcf = oancf - abs(capx)
                fcf_yield = fcf / market_cap if market_cap > 0 and fcf > 0 else 0.0
            
            # PE Ratio (使用epsfi和prcc_f)
            epsfi = latest.get('epsfi')
            if epsfi and epsfi > 0 and prcc_f:
                pe_ratio = prcc_f / epsfi
            
            # Growth Rate
            if len(financials) >= 3:
                revenues = [f.get('revt') or f.get('sale', 0) for f in financials[:3]]
                if revenues[0] and revenues[-1] and revenues[-1] > 0:
                    growth_rate = (revenues[0] / revenues[-1]) ** (1/2) - 1
        
        return fcf_yield, pe_ratio, growth_rate
    
    def _extract_us_capex_series(self, financials: List[Dict]) -> Optional[List[float]]:
        """提取美股资本开支时间序列"""
        capex_list = []
        for f in financials[:5]:
            capx = f.get('capx')
            if capx:
                capex_list.append(abs(capx))
        return capex_list if capex_list else None


# ===============================================================================
# 工厂函数
# ===============================================================================

def create_db_loader(
    china_db_path: Optional[str] = None,
    us_db_path: Optional[str] = None
) -> SVIPDatabaseLoader:
    """
    创建数据库加载器
    
    Args:
        china_db_path: A股数据库路径
        us_db_path: 美股数据库路径
    
    Returns:
        SVIPDatabaseLoader实例
    """
    return SVIPDatabaseLoader(china_db_path, us_db_path)
