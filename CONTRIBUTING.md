# 贡献指南

感谢你对 SVIP 项目的关注！

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议，请：

1. 在 [Issues](https://github.com/unicome37/svip/issues) 中搜索是否已有相关问题
2. 如果没有，创建新的 Issue，并提供：
   - 清晰的标题
   - 详细的描述
   - 复现步骤（如果是 bug）
   - 预期行为 vs 实际行为
   - 系统环境信息

### 提交代码

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用有意义的变量名和函数名
- 添加必要的注释（中文）
- 为新功能添加单元测试
- 更新相关文档

### 文档贡献

文档改进同样重要！如果你发现：
- 文档错误或不清楚的地方
- 缺少的使用示例
- 可以改进的说明

欢迎提交 PR 改进文档。

## 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/unicome37/svip.git
cd svip

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest

# 代码检查
ruff check src/
```

## 提交信息规范

提交信息应该清晰描述改动内容：

- `feat: 添加新功能`
- `fix: 修复 bug`
- `docs: 更新文档`
- `test: 添加测试`
- `refactor: 重构代码`
- `style: 代码格式调整`

## 行为准则

- 尊重所有贡献者
- 保持友好和专业
- 接受建设性批评
- 关注项目目标

## 许可

通过贡献代码，你同意你的贡献将在 MIT 许可下发布。

---

再次感谢你的贡献！🎉
