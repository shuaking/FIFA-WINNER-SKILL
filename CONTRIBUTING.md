# 贡献指南 (Contributing Guide)

感谢你对 FIFA-WINNER-SKILL 项目的关注！我们欢迎各种形式的贡献。

## 🤝 如何参与

### 贡献方式

1. **报告Bug** - 在 [Issues](https://github.com/Dxboy266/FIFA-WINNER-SKILL/issues) 中提交
2. **提出功能建议** - 在 [Issues](https://github.com/Dxboy266/FIFA-WINNER-SKILL/issues) 中讨论
3. **提交代码** - 通过 Pull Request
4. **完善文档** - 修正错误、补充说明
5. **数据源贡献** - 分享新的赔率、新闻API

## 📝 提交 Pull Request 流程

### 1. Fork 并克隆仓库

```bash
# Fork 项目到你的账号下，然后克隆
git clone https://github.com/YOUR_USERNAME/FIFA-WINNER-SKILL.git
cd FIFA-WINNER-SKILL
```

### 2. 创建特性分支

```bash
git checkout -b feature/your-feature-name
# 或修复bug
git checkout -b fix/issue-123
```

### 3. 进行修改并提交

```bash
# 修改代码后
git add .
git commit -m "feat: add new odds data source adapter"

# 或
git commit -m "fix: resolve prediction scoring model edge case"
```

**提交信息格式：**
- `feat:` 新功能
- `fix:` Bug修复
- `docs:` 文档修改
- `style:` 代码格式（不影响功能）
- `refactor:` 重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 4. 推送并创建 PR

```bash
git push origin feature/your-feature-name
```

然后在GitHub上创建Pull Request，描述你的修改内容。

## ✅ 代码规范

### Python代码规范
- 遵循 PEP 8
- 函数和类添加docstring
- 关键逻辑添加注释

### 测试要求
提交代码前请运行测试：

```bash
# 运行单元测试
python -m pytest tests/

# 运行审计脚本
python scripts/worldcup_github_readiness_auditor.py write --edition 2026 --root .
```

### 提交前检查清单
- [ ] 代码通过所有测试
- [ ] 添加了必要的文档/注释
- [ ] 更新了相关的README或文档
- [ ] 遵守了安全边界（禁止博彩推广）

## 🚫 安全边界

**禁止的贡献类型：**
- ❌ 添加投注建议、赔率交易功能
- ❌ 移除免责声明
- ❌ 添加"稳赚"、"必赢"等误导性语言
- ❌ 集成博彩平台API

## 🎯 推荐贡献方向

我们特别欢迎以下类型的贡献：

### 数据源扩展
- 新的赔率API适配器
- 新闻舆情爬虫优化
- 伤停信息采集

### 预测模型优化
- 权重配置优化
- 新的评分维度
- 历史数据回测工具

### 可视化增强
- 海报模板设计
- 报告格式优化
- 数据可视化图表

### 文档完善
- 多语言翻译
- API文档
- 使用教程

### 测试覆盖
- 单元测试补充
- 集成测试
- 边界条件测试

## 📞 联系方式

- **GitHub Issues**: 技术问题讨论
- **微信群**: 见 README.md（快速交流）
- **开发者微信**: 见 README.md（深度合作）

## 📜 许可协议

贡献的代码将使用与项目相同的 MIT License。

提交PR即表示你同意：
1. 你拥有所提交代码的版权
2. 你的贡献将在MIT协议下发布
3. 你遵守本项目的安全边界要求

---

再次感谢你的贡献！🎉
