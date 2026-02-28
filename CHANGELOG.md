# 更新日志

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-02-28

### 新增

#### 核心引擎
- ✨ SVI 慢变量指数评分引擎（结构质量筛选）
- ✨ A1 估值安全垫模块（FCF Yield + QPEG）
- ✨ A2 慢变量加速检测模块（相位识别）
- ✨ A3 组合权重引擎（W=Q×V×P + 约束投影）
- ✨ A4 宏观慢变量过滤器（利率/流动性/盈利）
- ✨ A7 极端风险模块（流动性/制度/技术替代）
- ✨ A8 慢变量主题轮动引擎（SVRA）
- ✨ 组合编排引擎（整合所有模块）
- ✨ Markdown 报告生成器

#### 数据模型
- ✨ 完整的数据结构定义（23个类，8个枚举）
- ✨ 跨市场参数适配（US/HK/CN）
- ✨ 配置集中管理系统

#### 文档
- 📚 README.md（系统概述）
- 📚 USAGE.md（使用指南）
- 📚 MANUAL.md（完整操作手册，8个部分）
- 📚 QUICK_REFERENCE.md（快速参考卡片）
- 📚 PROJECT_SUMMARY.md（项目总结）
- 📚 CONTRIBUTING.md（贡献指南）

#### 示例与测试
- 📦 示例数据（6只股票，4个YAML文件）
- 🧪 单元测试（SVI、Valuation引擎）
- ✅ 系统验证脚本（verify_setup.py）

#### 工具
- 🔧 命令行工具（run_svip.py）
- 🔧 跨市场支持（--market US/HK/CN）
- 🔧 自定义数据输入

### 特性

- 🎯 基于慢变量存在论投资学理论体系
- 🎯 完整的 A0-A11 模块实现
- 🎯 三池分类系统（Core/Watch/Block）
- 🎯 多层约束投影（单票/主题/行业）
- 🎯 宏观与尾部风险自动调节
- 🎯 季度轮动信号生成
- 🎯 中文友好的完整文档

### 技术栈

- Python 3.11+
- pandas, numpy, pydantic
- dataclass-based 架构
- 模块化设计
- 配置驱动

---

## [未来计划]

### v1.1.0（计划中）
- [ ] 数据库集成（自动读取财务数据）
- [ ] FRED API 自动获取宏观数据
- [ ] 更多单元测试覆盖
- [ ] 回测框架实现（A5）

### v1.2.0（计划中）
- [ ] Streamlit Dashboard 可视化
- [ ] 与 SPUD-INVEST 自动联动
- [ ] 更多慢变量主题桶
- [ ] 自动化报告邮件

### v2.0.0（长期）
- [ ] 完整回测验证系统
- [ ] 机器学习辅助慢变量识别
- [ ] 多账户组合管理
- [ ] 移动端监控应用

---

[1.0.0]: https://github.com/unicome37/svip/releases/tag/v1.0.0
