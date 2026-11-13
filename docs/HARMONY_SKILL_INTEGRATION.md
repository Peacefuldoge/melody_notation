# Melody Harmony Skill — 使用与兼容性

此更新只**增加和弦知识 Skill 与两个只读 MCP 工具**。它不会改变 Tkinter GUI、`.jianpu` 语法、MIDI 或音频引擎，也不会偷偷启用尚未实现的多音轨。

## 文件位置

```text
Melody Notation/
├── AGENTS.md
├── .agents/skills/melody-harmony/SKILL.md       # Codex 自动发现
│   └── references/                             # 可独立复制的知识文件
├── skills/melody-harmony/SKILL.md               # 与既有 skills/ 并列的分发副本
├── src/harmony/
│   ├── chords.md                               # 29 种常见和弦的结构/情绪/用法
│   ├── progressions.md                         # 大小调进行模板
│   ├── workflow.md                             # AI 配和弦工作流与输出约束
│   ├── sources.md                              # 来源和证据边界
│   └── chords.json                             # 机器可读的音程与示例
└── src/mcp_server.py               # 新增只读查询工具
```

## Codex（本地自动发现）

在项目根目录打开 Codex，使用：

> 使用 `$melody-harmony`，读取《荒》的旋律与转调，分析每个乐句给两套和弦进行。先报告，不改原文件。

对于项目级 Skills，Codex 会在工作目录与仓库根目录的 `.agents/skills` 中寻找 `SKILL.md`。若看不到，重启当前会话或检查 Codex 打开的是否是本项目根目录。

## DeepSeek Harness（通过 MCP 获取内容）

沿用之前的 `@deepseek-ai/dsh-mcp-client` 的 stdio 配置，确保 MCP 的 Python 运行新版工程：

```yaml
- id: mcp-melody-notation
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: melody_notation
    transport: stdio
    command: 'D:/miniconda3/envs/melody/python.exe' # 示例：请换成 where python 的实际路径
    args: ['-m', 'melody_notation.mcp_server']
    cwd: 'D:/Work/melody-notation-v0.2.13'
    env:
      MELODY_WORKSPACE: 'D:/Work/你的音乐项目'
```

在 DSH 中提问：

> 请先调用 Melody Notation MCP 的 `list_harmony_topics`，然后分别调用 `read_harmony_guide(topic="chords")`、`read_harmony_guide(topic="progressions")` 与 `read_harmony_guide(topic="workflow")`。使用这些资料为我的简谱建议两套可解释的和弦进行，不要修改原乐谱。

**不要假设 DSH 会自动扫描 Codex 的 `.agents/skills/`**。本版用 MCP 提供不依赖 DSH Skill 自动发现机制的读取入口。新增工具需重启 DSH / 刷新工具清单。

## AI 在这里“学习”是什么意思？

这里的学习是**任务期间检索并遵循 Skill 知识**，不是重新训练模型权重。关闭会话后，如果下一次能够重新访问 Skill/MCP，它可以再次读取一致的文档。

## 后续多音轨衔接

未来可将和弦规划另存为 `*.harmony.md`（由用户审查），再转换为真正的 chord track/MIDI 多轨。当前 MIDI 只能导出原有单旋律，不应把文字和弦表说成已生成完整伴奏。参考 `src/harmony/workflow.md`。

## 验证命令

```powershell
conda activate melody
cd D:\Work\melody-notation-v0.2.13
python -m pip install -e ".[all,test]"
python -m pytest -q
python -c "from melody_notation.harmony import read_topic; print(read_topic('overview'))"
```

## 资料与授权

知识库用原创中文描述和整理，不粘贴长篇教材。出处见 `src/harmony/sources.md`。情绪词是有条件的创作线索；参考的心理学研究表明其听觉联想受和弦进行、调式、速度等上下文影响。
