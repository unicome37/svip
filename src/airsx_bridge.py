"""
SVIP v1.0 — AIRS-X Bridge

从 AIRS-X summary.csv 读取评级数据，补充 SVIP 的主观评估字段。

AIRS-X 提供的可用数据：
- industry        → SVIP sector
- airs_grade/score → 可映射为 moat_rating 参考
- S (Stability)    → 可映射为 demand_rigidity_rating
- U (Uncertainty)  → 可映射为 substitution_risk_rating（反向）
- esd_quadrant     → 辅助 moat_rating 判断
- zone             → 辅助判断企业质量
"""
import csv
import glob
import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


def load_airsx_summary(airsx_dir: str) -> Dict[str, Dict]:
    """
    从 AIRS-X 目录加载 summary.csv，按 stock_code 索引。

    Args:
        airsx_dir: AIRS-X 项目根目录

    Returns:
        {stock_code: {字段字典}, ...}
    """
    cache: Dict[str, Dict] = {}

    # 优先查找结果目录中的 summary.csv
    pattern = os.path.join(airsx_dir, "airs_*_results_*", "summary.csv")
    csvs = sorted(glob.glob(pattern), reverse=True)
    if not csvs:
        # 回退到根目录
        root_csv = os.path.join(airsx_dir, "summary.csv")
        if os.path.exists(root_csv):
            csvs = [root_csv]

    for csv_path in csvs:
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    code = row.get("stock_code", "").strip()
                    if code and code not in cache:
                        cache[code] = row
        except Exception as e:
            logger.warning(f"加载 AIRS-X summary 失败: {csv_path}: {e}")

    logger.info(f"AIRS-X bridge: 加载 {len(cache)} 只股票数据")
    return cache


def _safe_float(val, default=0.0) -> float:
    """安全转换浮点数"""
    if val is None or val == "" or val == "None":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _spud_s_to_demand_rigidity(s_score: float) -> int:
    """
    将 AIRS-X 的 S（稳定性）映射为 SVIP 的 demand_rigidity_rating。

    S 范围约 0-5，映射到 0-100:
    - S >= 4.0 → 90 (极高需求刚性)
    - S >= 3.0 → 70
    - S >= 2.0 → 50
    - S >= 1.0 → 30
    - S < 1.0  → 15
    """
    if s_score >= 4.0:
        return 90
    elif s_score >= 3.0:
        return int(50 + (s_score - 3.0) * 40)  # 50-90
    elif s_score >= 2.0:
        return int(30 + (s_score - 2.0) * 20)  # 30-50
    elif s_score >= 1.0:
        return int(15 + (s_score - 1.0) * 15)  # 15-30
    else:
        return 15


def _spud_u_to_substitution_risk(u_score: float) -> int:
    """
    将 AIRS-X 的 U（不确定性）映射为 SVIP 的 substitution_risk_rating。

    U 越高 → 替代风险越高 → rating 越高（反向指标）。
    U 范围约 0-5，映射到 0-100:
    - U >= 4.0 → 90 (极高替代风险)
    - U >= 3.0 → 70
    - U >= 2.0 → 50
    - U < 2.0  → 30
    """
    if u_score >= 4.0:
        return 90
    elif u_score >= 3.0:
        return int(50 + (u_score - 3.0) * 40)
    elif u_score >= 2.0:
        return int(30 + (u_score - 2.0) * 20)
    else:
        return 30


def _zone_to_moat_rating(zone: str, esd_quadrant: str, airs_grade: str) -> int:
    """
    综合 AIRS-X 的 zone、ESD象限、评级，映射为 SVIP 的 moat_rating。

    zone 含义:
    - "主脊线资产" → 核心资产，moat 高
    - "稳定收益"   → 中等 moat
    - "成长机遇"   → 中等偏低
    - "禁入区"     → 低

    esd_quadrant 辅助:
    - "护城河"     → moat 加分
    - "灵活健康"   → 中性
    - "投机/泡沫"  → 减分
    """
    base = 50

    # zone 基准
    zone_map = {
        "主脊线资产": 75,
        "稳定收益": 60,
        "成长机遇": 45,
        "禁入区": 20,
    }
    base = zone_map.get(zone, 50)

    # ESD 调整
    if "护城河" in (esd_quadrant or ""):
        base = min(100, base + 15)
    elif "投机" in (esd_quadrant or "") or "泡沫" in (esd_quadrant or ""):
        base = max(0, base - 10)

    # AIRS 评级调整
    grade_adj = {"A": 10, "B": 5, "C": 0, "D": -10}
    base += grade_adj.get(airs_grade, 0)

    return max(0, min(100, base))


def enrich_svip_stock(stock_data: Dict, airsx_cache: Dict[str, Dict]) -> Dict:
    """
    用 AIRS-X 数据补充 SVIP 股票的主观评估字段。

    只更新仍为默认值（50）的字段，不覆盖已有的人工评估。

    Args:
        stock_data: SVIP 格式的股票字典
        airsx_cache: load_airsx_summary() 返回的缓存

    Returns:
        补充后的 stock_data（原地修改）
    """
    code = stock_data.get("symbol", "")
    airsx = airsx_cache.get(code)
    if not airsx:
        return stock_data

    fin = stock_data.get("financials", {})

    s_score = _safe_float(airsx.get("S"))
    u_score = _safe_float(airsx.get("U"))
    zone = airsx.get("zone", "")
    esd = airsx.get("esd_quadrant", "")
    grade = airsx.get("airs_grade", "")
    industry = airsx.get("industry", "")

    # 补充 sector（如果为空）
    if not stock_data.get("sector") and industry:
        stock_data["sector"] = industry

    # 补充 moat_rating（仅当仍为默认值 50）
    if fin.get("moat_rating", 50) == 50 and (zone or esd or grade):
        fin["moat_rating"] = _zone_to_moat_rating(zone, esd, grade)

    # 补充 demand_rigidity_rating
    if fin.get("demand_rigidity_rating", 50) == 50 and s_score > 0:
        fin["demand_rigidity_rating"] = _spud_s_to_demand_rigidity(s_score)

    # 补充 substitution_risk_rating
    if fin.get("substitution_risk_rating", 50) == 50 and u_score > 0:
        fin["substitution_risk_rating"] = _spud_u_to_substitution_risk(u_score)

    return stock_data


def enrich_batch(
    stocks_data: List[Dict],
    airsx_dir: str = None,
) -> List[Dict]:
    """
    批量补充 SVIP 股票数据。

    Args:
        stocks_data: SVIP 格式的股票字典列表
        airsx_dir: AIRS-X 项目目录（默认 ../airs-x）

    Returns:
        补充后的列表
    """
    from pathlib import Path

    if airsx_dir is None:
        airsx_dir = str(Path(__file__).resolve().parent.parent.parent / "airs-x")

    if not os.path.isdir(airsx_dir):
        logger.info(f"AIRS-X 目录不存在: {airsx_dir}，跳过桥接补充")
        return stocks_data

    cache = load_airsx_summary(airsx_dir)
    if not cache:
        return stocks_data

    enriched = 0
    for stock in stocks_data:
        before_moat = stock.get("financials", {}).get("moat_rating", 50)
        enrich_svip_stock(stock, cache)
        if stock.get("financials", {}).get("moat_rating", 50) != before_moat:
            enriched += 1

    logger.info(f"AIRS-X bridge: 补充了 {enriched}/{len(stocks_data)} 只股票的评估数据")
    return stocks_data
