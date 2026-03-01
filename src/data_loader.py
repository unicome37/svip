"""
SVIP v1.0 — Data Loader

加载并校验 slow_variables.yaml 和 theme_buckets.yaml。
提供主题桶验证和慢变量代理指标查询。
"""
import os
import yaml
from typing import Dict, List, Optional


def load_yaml(path: str) -> dict:
    """加载 YAML 文件"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_theme_buckets(data_dir: str) -> Dict[str, dict]:
    """加载主题桶定义"""
    path = os.path.join(data_dir, "theme_buckets.yaml")
    if not os.path.exists(path):
        return {}
    data = load_yaml(path)
    return data.get("theme_buckets", {})


def load_slow_variables(data_dir: str) -> List[dict]:
    """加载慢变量清单"""
    path = os.path.join(data_dir, "slow_variables.yaml")
    if not os.path.exists(path):
        return []
    data = load_yaml(path)
    return data.get("slow_variables", [])


def get_valid_themes(data_dir: str) -> set:
    """获取所有有效主题桶名称"""
    buckets = load_theme_buckets(data_dir)
    return set(buckets.keys())


def validate_stock_themes(
    stocks_data: list,
    data_dir: str,
) -> List[str]:
    """
    校验股票的 theme 字段是否在已定义的主题桶中。
    返回警告列表。
    """
    valid_themes = get_valid_themes(data_dir)
    if not valid_themes:
        return []

    warnings = []
    for item in stocks_data:
        theme = item.get("theme", "")
        symbol = item.get("symbol", "UNKNOWN")
        if theme and theme not in valid_themes:
            warnings.append(
                f"{symbol}: theme '{theme}' 不在已定义的主题桶中。"
                f"有效主题: {', '.join(sorted(valid_themes))}"
            )
    return warnings


def get_proxy_indicators(data_dir: str, theme: str) -> List[str]:
    """获取指定主题的慢变量代理指标"""
    sv_list = load_slow_variables(data_dir)
    for sv in sv_list:
        if sv.get("theme") == theme:
            return sv.get("proxy_indicators", [])
    return []
