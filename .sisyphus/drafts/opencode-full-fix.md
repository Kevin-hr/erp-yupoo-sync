# Draft: OpenCode 全部修复计划

## 用户需求
- 全部修复 OpenCode 配置 + 测试三大系统

## 确认的决策
1. **修复 OpenCode 配置**: oh-my-opencode → oh-my-openagent
2. **测试范围**:
   - OpenCode 基本功能诊断
   - ERP 决策系统 Phase 1 完整测试
   - Yupoo 同步流水线验证

## 技术发现
- OpenCode v1.2.27 已安装在 `C:\Users\Administrator\AppData\Roaming\npm\opencode.cmd`
- 配置文件位于 `C:\Users\Administrator\.config\opencode\opencode.json`
- oh-my-opencode 插件已重命名为 oh-my-openagent
- 决策系统 Phase 1 已完成，12测试通过

## 修复步骤
1. 更新 opencode.json: oh-my-opencode → oh-my-openagent
2. 验证 OpenCode 可正常运行
3. 运行决策系统测试
4. 验证 Yupoo 同步流水线

## Open Questions
- 是否需要记录测试结果到 memory.md？
