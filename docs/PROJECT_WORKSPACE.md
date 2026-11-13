# v0.2.8 多文件项目工作台与侧栏导航

## v0.2.8 左侧导航设计

侧栏交互接近 ChatGPT 桌面应用，而并非照搬聊天功能：左侧 43px 的导航图标栏、暗色项目面板、最近打开的乐谱、项目文件树（支持多个项目），以及搜索过滤。主谱面/右侧 Inspector 与音频组件保持独立。

- `workspace.py` 的 `remember_project` / `load_recent_projects` 负责本地历史（路径，不含文件正文）。
- `workspace_gui.py` 的 `WorkspaceMixin` 负责侧栏和树选中行为；打开其他项目的简谱时更新活动项目，现有编辑标签继续保留。
- 搜索仅过滤侧栏显示，绝不删除或修改磁盘文件。
- 收起侧栏只隐藏导航面板，保留一列图标；中央画布自动占用释放的宽度。
- Codex / DeepSeek Harness 的 MCP 接口保持原样，GUI 项目切换不自动修改 Agent 权限根目录。

## 实现范围

- **ProjectWorkspace** (`workspace.py`)：真实目录，项目名/清单、子文件夹与 `.jianpu` 枚举，创建与重命名，路径限制。
- **ScoreTab** (`workspace.py`)：每个文件独立的 Score 对象、撤销/重做栈、选中音符、连音锚点、源码草稿、dirty 状态、音色/倍速和滚动位置。
- **WorkspaceMixin** (`workspace_gui.py`)：项目树、创建/打开/命名、中央编辑标签、切换状态、保存确认。
- **Editor** (`gui.py`)：继续复用原来单谱的渲染 Canvas、音符 Inspector、试听与导出；每次激活一个 ScoreTab 绑定到 Editor 的现有控件。

## 操作对应关系

| 操作 | 生效范围 |
|---|---|
| 新建项目 / 打开项目 | 设为活动项目并记录在最近项目列表；编辑器已有打开标签继续保留 |
| 新建简谱 | 当前选中的项目或子文件夹中产生独立文件，直接打开标签 |
| 双击 `.jianpu` | 激活现有标签，或读取磁盘内容并新开标签 |
| 撤销 / 重做 | **仅当前标签** |
| 新建内置示例 | **新开未保存标签**，不替换其他乐谱 |
| Ctrl+S / 导出 | **仅当前标签** |
| 关闭标签 / 退出 | 对未保存的更改询问保存/不保存/取消 |
| 重命名 | 改变文件系统路径，并更新已打开标签的路径引用；存在未保存更改时禁止重命名 |

## 给未来音轨与 AI Chat 的扩展点

```text
Workspace
  Project (folder / .melody-project.json)
    Subproject (folder)
      ScoreDocument (.jianpu) × N
      Track (future: track arrangement / channel / instrument)
    AI Chat Session (future: not implemented)
```

中央 `ScoreTab` 目前是文件编辑标签，不代表同时播放的多音轨。后续新增 Track 时，应将轨道属性和混音时间轴独立建模，不要把多个 `.jianpu` 粗暴合并成一个 Score 对象。

MCP 仍由 `mcp_server.py` 的 `MELODY_WORKSPACE` 约束路径；不自动同步 GUI 未保存的更改。避免两个独立进程同时写入同一文件导致覆盖。

## 后续未实现

项目树拖放排序、启动时自动重开全部编辑标签、跨项目会话恢复、文件外部修改监控、多轨、AI 对话和 Diff 审批。最近项目路径列表现已支持。

### v0.3 补充：多轨文件

项目树现可识别 `.jianpu`、`.drum`、`.mtrack`。后两者分别在独立 Tkinter 步进编辑器和多轨时间线中打开；完整用法见 [MULTITRACK_DRUMS.md](MULTITRACK_DRUMS.md)。之前的“多音轨未实现”描述仅适用于 v0.2.x，v0.3 已加入基本的多轨混音和分轨 MIDI 导出，但尚不支持波形倒放或中央标签内直接编辑多轨。
