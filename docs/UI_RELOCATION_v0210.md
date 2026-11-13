# Melody Notation v0.2.10 — GUI 操作区调整

## 目标

把 v0.2.9 顶部的一排动作按钮收纳进左侧导航，让播放器与音色控制就近集中到右侧音符 Inspector 上方。继续使用 Tkinter 及现有双主题，不触碰核心音乐模型、多文件项目、MCP 接口。

## 新布局

| 位置 | 内容 | 说明 |
|---|---|---|
| 顶部细信息条 | 当前乐谱标题、调号、拍号、BPM | 无重复操作按钮 |
| 左侧窄图标栏 | 展开/折叠、项目、新建、搜索、保存、全局菜单、帮助 | 折叠时仍可由 `···` 进入所有菜单 |
| 左侧导航面板 | `文件`、`编辑`、`导出`、`工具`；新建/保存；最近打开；项目树 | 按功能分组，菜单随主题即时生成 |
| 中央 | 多文档标签、乐谱、每行小节、源码抽屉 | 继续支持单击音符编辑 |
| 右侧上方 | 播放/暂停/继续、停止、音色、倍速、进度定位、时间 | 不再打开外部播放器 |
| 右侧下方 | 音高/八度/时值/升降号/演奏记号、插入/删除、连音线 | 独立滚动，不影响顶部播放器 |
| 底部 | 状态提示、拍数/同步状态 | 移除旧全宽播放进度条 |

### 菜单具体内容

- 文件：新建项目、打开项目、创建简谱、打开简谱、四份内置示例、保存、另存为
- 编辑：撤销、重做、检查节拍
- 导出：MIDI、WAV、MP3、PNG
- 工具：图片识谱 Beta、源码抽屉、切换浅色/深色、帮助

## 兼容性

- `INSTRUMENTS`, `SPEED_LABELS`, 播放器后台合成流程及所有音频导出函数未改变。
- `ProjectWorkspace`, `ScoreTab` 的磁盘数据结构未改变。
- `mcp_server.py`、`core.py`、`editing.py` 等非 GUI 引擎代码未修改。
- 修改 `ui_theme.py` 仅增加上下文标题及播放进度条的控件样式。
- 更新 `help_dialog.py` 中旧的「顶部按钮」「底部播放条」位置说明。

## 验证

- `pytest`：48 passed、1 skipped（可选 MCP SDK 不存在）。
- Tkinter Xvfb GUI 冒烟：浅色/深色、打开《荒》41 小节示例、右侧播放器控件映射、导航菜单、左侧折叠、1120×700 紧凑窗口与 Inspector 滚动，全部通过。
- 未验证：实际 Windows 扬声器、DeepSeek Harness/Codex MCP 端到端握手。

截图：`docs/screenshots/workbench-light.png`、`docs/screenshots/workbench-dark.png`、`docs/screenshots/workbench-compact.png`。
