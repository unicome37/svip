"""
SVIP v1.0 — Report Generator (Markdown 报告生成)

生成可读的 Markdown 格式投资报告。
"""
from datetime import datetime
from typing import Optional
from src.models import (
    SVIPReport, SVIPStock, SVILevel, PortfolioAllocation,
    MacroState, TailRiskResult, RotationSignal,
)


def _phase_emoji(phase: str) -> str:
    return {"accelerating": "🚀", "steady": "➡️", "decaying": "📉"}.get(phase, "❓")


def _tier_emoji(tier: str) -> str:
    return {"A": "🟢", "B": "🟡", "C": "🔴"}.get(tier, "⚪")


def _wind_emoji(wind: str) -> str:
    return {"tailwind": "🌬️", "neutral": "➡️", "headwind": "🌊"}.get(wind, "❓")


def _risk_emoji(state: str) -> str:
    return {
        "normal": "🟢", "alert": "🟡", "tense": "🟠", "crisis": "🔴"
    }.get(state, "⚪")


def format_stock_table(stocks: list[SVIPStock], title: str) -> str:
    """格式化股票表格"""
    if not stocks:
        return f"### {title}\n\n*（空）*\n"

    lines = [f"### {title}\n"]
    lines.append("| 代码 | 名称 | SVI | 估值 | 相位 | 目标权重 | 行动 |")
    lines.append("|------|------|-----|------|------|---------|------|")

    for s in sorted(stocks, key=lambda x: x.target_weight, reverse=True):
        svi = f"{s.svi.total:.0f}" if s.svi else "-"
        tier = f"{_tier_emoji(s.valuation.tier.value)} {s.valuation.tier.value}" if s.valuation else "-"
        phase = f"{_phase_emoji(s.acceleration.phase.value)}" if s.acceleration else "-"
        weight = f"{s.target_weight:.1%}" if s.target_weight > 0 else "-"
        lines.append(
            f"| {s.symbol} | {s.name} | {svi} | {tier} | {phase} | {weight} | {s.action.value} |"
        )

    return "\n".join(lines) + "\n"


def format_macro_section(macro: Optional[MacroState]) -> str:
    """格式化宏观状态"""
    if not macro:
        return "### 宏观慢变量状态\n\n*（未提供宏观数据）*\n"

    lines = ["### 宏观慢变量状态\n"]
    lines.append(f"| 指标 | 评分 | 状态 |")
    lines.append("|------|------|------|")
    lines.append(f"| 利率结构 | {macro.interest_rate_score:+d} | {'顺风' if macro.interest_rate_score > 0 else '逆风' if macro.interest_rate_score < 0 else '中性'} |")
    lines.append(f"| 流动性 | {macro.liquidity_score:+d} | {'顺风' if macro.liquidity_score > 0 else '逆风' if macro.liquidity_score < 0 else '中性'} |")
    lines.append(f"| 盈利周期 | {macro.earnings_cycle_score:+d} | {'顺风' if macro.earnings_cycle_score > 0 else '逆风' if macro.earnings_cycle_score < 0 else '中性'} |")
    lines.append(f"\n**综合评分**: {macro.total_score:+d} {_wind_emoji(macro.wind.value)} **{macro.wind.value}**")
    lines.append(f"**MacroRiskFactor**: {macro.macro_risk_factor:.2f}")
    return "\n".join(lines) + "\n"


def format_tail_risk_section(tr: Optional[TailRiskResult]) -> str:
    """格式化尾部风险"""
    if not tr:
        return "### 尾部风险状态\n\n*（未提供风险数据）*\n"

    lines = ["### 尾部风险状态\n"]
    lines.append(f"- 流动性风险: {tr.liquidity_risk:.0f}/100")
    lines.append(f"- 制度风险: {tr.regime_risk:.0f}/100")
    lines.append(f"- 技术替代风险: {tr.disruption_risk:.0f}/100")
    lines.append(f"\n**状态**: {_risk_emoji(tr.state.value)} **{tr.state.value}**")
    lines.append(f"**TailRiskFactor**: {tr.tail_risk_factor:.2f}")
    if tr.vix is not None:
        lines.append(f"**VIX**: {tr.vix:.1f}")
    return "\n".join(lines) + "\n"


def format_rotation_section(signals: list[RotationSignal]) -> str:
    """格式化轮动信号"""
    if not signals:
        return "### 慢变量主题轮动信号\n\n*（无轮动信号）*\n"

    lines = ["### 慢变量主题轮动信号\n"]
    lines.append("| 主题 | 平均加速度 | Z-Score | 权重调整 |")
    lines.append("|------|-----------|---------|---------|")
    for sig in signals:
        adj = f"{sig.weight_adjustment:+.0%}" if sig.weight_adjustment != 0 else "不变"
        lines.append(
            f"| {sig.theme} | {sig.avg_acceleration:.1f} | {sig.z_score:+.2f} | {adj} |"
        )
    return "\n".join(lines) + "\n"


def generate_markdown_report(report: SVIPReport) -> str:
    """生成完整 Markdown 报告"""
    alloc = report.allocation
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M")

    sections = []

    # 标题
    sections.append(f"# SVIP 慢变量投资池报告\n")
    sections.append(f"> 生成时间: {ts} | 市场: {report.market}\n")

    # 系统状态概览
    sections.append("## 系统状态概览\n")
    if alloc:
        sections.append(f"| 指标 | 值 |")
        sections.append(f"|------|-----|")
        sections.append(f"| 总股票仓位 | {alloc.total_equity:.1%} |")
        sections.append(f"| 现金 | {alloc.cash_weight:.1%} |")
        sections.append(f"| 核心池仓位 | {alloc.core_pool_weight:.1%} |")
        sections.append(f"| 观察池仓位 | {alloc.watch_pool_weight:.1%} |")
        sections.append(f"| 仓位上限 | {alloc.final_equity_ceiling:.1%} |")
        sections.append(f"| 宏观因子 | {alloc.macro_risk_factor:.2f} |")
        sections.append(f"| 尾部风险因子 | {alloc.tail_risk_factor:.2f} |")
        sections.append("")

    # 核心池
    sections.append("## 投资池\n")
    sections.append(format_stock_table(report.core_pool, "核心池 (Core)"))
    sections.append(format_stock_table(report.watch_pool, "观察池 (Watch)"))

    # 主题暴露
    if alloc and alloc.theme_exposure:
        sections.append("### 主题暴露\n")
        sections.append("| 主题 | 权重 |")
        sections.append("|------|------|")
        for theme, w in sorted(alloc.theme_exposure.items(), key=lambda x: -x[1]):
            sections.append(f"| {theme} | {w:.1%} |")
        sections.append("")

    # 宏观
    sections.append("## 宏观与风险\n")
    sections.append(format_macro_section(report.macro))
    sections.append(format_tail_risk_section(report.tail_risk))

    # 轮动
    sections.append("## 轮动信号\n")
    sections.append(format_rotation_section(report.rotation_signals))

    # 违规
    if alloc and alloc.violations:
        sections.append("## ⚠️ 违规警告\n")
        for v in alloc.violations:
            sections.append(f"- {v}")
        sections.append("")

    # 页脚
    sections.append("---")
    sections.append(f"*SVIP v1.0 — 慢变量投资池系统 | {ts}*\n")

    return "\n".join(sections)


def save_report(report: SVIPReport, output_dir: str = "reports") -> str:
    """保存报告到文件"""
    import os
    os.makedirs(output_dir, exist_ok=True)

    ts = report.timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"SVIP_{report.market}_报告_{ts}.md"
    filepath = os.path.join(output_dir, filename)

    content = generate_markdown_report(report)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
