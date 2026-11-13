# Melody Notation

**可编辑简谱 · 鼓点编排 · 多轨音乐工作台 · MIDI 演奏录制 · MCP 音乐工具**

> 当前版本：**v0.5.10**（版本号保持不变）。软件以本地文件和可编辑音乐事件为中心，并非输入提示词后一键合成整首歌曲的服务。

Melody Notation 是一款桌面数字简谱与编曲工具。你可以在同一个项目里编写 `.jianpu` 简谱、设计 `.drum` 节奏、将已有素材组织成 `.mtrack` 多轨编排，随后试听、校验和导出。项目由普通文件夹构成，既能通过图形界面操作，也能通过 CLI、Codex / DeepSeek Harness 等 MCP 客户端调用工具。

## 功能概览

| 功能 | 当前支持 |
|---|---|
| 简谱编辑 | 空白简谱创建、图形化选音与插入、音级/八度/时值/升降号/装饰音、连音线、源码编辑、撤销重做、节拍检查 |
| 乐谱排版 | 每行固定 2–5 小节；密集乐段拓宽并允许横向滚动；PNG 乐谱导出 |
| 鼓点音序器 | 新建默认 **Kick、Snare、Hi-hat 三条空轨**；16 步网格、添加/重命名/删除鼓轨、鼓声选择、不同鼓组 |
| 多轨编排 | 将已保存的简谱/鼓点作为片段，设置开始拍、非破坏性裁剪、反转、音量、静音/Solo、音轨顺序 |
| 演奏与录制 | 虚拟钢琴、电脑键盘、标准 MIDI 输入；录制旋律简谱与原始复音 MIDI 事件；独立的演奏设置 |
| 文件管理 | 新建、打开、重命名、子文件夹、搜索、右键删除文件/文件夹/项目（移入系统回收站） |
| 试听与导出 | 内置合成试听；MIDI、WAV、MP3，以及简谱 PNG（适用格式随文档类型而异） |
| 扩展 | 本地 CLI、MCP Python SDK **2.x** 服务端、图片识谱（Beta，需配置视觉模型 API） |

四种 UI 主题：浅色、深色、米色和橄榄绿。核心音乐文件无需账号或云服务。

## 安装与启动

推荐 Windows 10/11、Python **3.11+** 和独立 Conda 环境。核心组件兼容 Python 3.10；**MCP SDK 2.x 需要 Python 3.11+**。

```powershell
conda create -n melody python=3.11 -y
conda activate melody
cd D:\Work\melody_notation
python -m pip install -e ".[gui,mcp,test]"
python -m melody_notation.cli gui
```

也可以运行 `melody-notation gui`。若已在旧环境中安装过本项目，更新源码后请重新执行 `pip install -e ...`，使依赖和 `src/` 源码映射生效。

备用 Tkinter 编辑器：

```powershell
python -m melody_notation.cli tk-gui
```

主界面依赖 PySide6；MIDI 输入与低延迟监听需要相应的可选依赖和可用的系统设备。导出 MP3 需在系统 `PATH` 中提供 **FFmpeg**；WAV/MIDI/PNG 不依赖 FFmpeg。图片识谱需额外安装 `.[vision]`、配置模型 API，并在实际发送图片前授权。

## 第一次创作

1. 启动后选择**新建项目**并指定存放目录；已有项目可直接**打开项目**。
2. 在项目树中选中项目或子文件夹，点击**新建音乐文件**，选择「简谱」「鼓点」或「多轨工程」。
3. 新建简谱默认没有预置音符或休止符，可通过「＋ 添加音符」开始录入；新建鼓点默认三条空轨，无预置节奏。
4. 在编辑器中修改内容、点击试听，然后按 `Ctrl+S` 保存。多轨编排引用的是**已保存**的源文件，试听前请先保存素材。
5. 使用「导出」菜单生成 MIDI/WAV/MP3/PNG；不支持的格式不会对当前文档提供有效导出。

### 项目树：重命名与删除

在左侧**项目文件**树中右键目标：

- 对 `.jianpu` / `.drum` / `.mtrack` 文件：选择**重命名**或**删除文件（移至回收站）**。
- 对子文件夹：选择**重命名**或**删除文件夹（移至回收站）**；删除子文件夹会一并移走其所有内容。
- 对项目根节点：选择**删除项目（移至回收站）**；整项目删除仅允许由 Melody 创建、带有效 `.melody-project.json` 标识的目录。

**删除之前必须确认**。被删文件的打开标签会关闭，未保存的草稿不会自动写回磁盘。备用 Tkinter 界面会要求先关闭相关鼓点/多轨独立编辑窗口。系统回收站是否可恢复、保留多久由操作系统决定；重要作品仍建议单独备份。**删除源简谱/鼓点不会自动清理其他 `.mtrack` 文件的引用**，因此可能导致多轨片段失效。删除并非「撤销」操作，`Ctrl+Z` 不会恢复已删除文件。

### 文件结构与示例

```text
我的音乐项目/
├── .melody-project.json      # Melody 项目标识
├── 第一乐章/
│   ├── 主旋律.jianpu         # 可阅读、可编辑的文本简谱
│   └── 鼓点.drum             # JSON 鼓点事件
└── 主题编排.mtrack           # JSON 多轨事件与项目内素材引用
```

软件内置示例可以独立打开；已保存作品和示例不受新建文件的空白初始设置影响。工程自带的展示素材位于 `demo_projects/` 和 `src/samples/`。

### 简谱源码速查

```text
title: 我的旋律
key: C
time: 4/4
bpm: 120
notes:
| 1 2 3 5 | 6/2 5/2 3 2 1 |
```

`1`–`7` 为音级、`0` 为休止；`5'` 表示高八度，`5,` 表示低八度；`5/2` 为半拍，`5 -` 延长一拍；连音用独立的 `( ... )` 标记。**`6/5` 不是两个音符**，也不是合法的时值写法；应使用 `6 5` 或 `6/2` 等有效写法。更完整的记号说明见软件内 **F1 → 简谱语法速查**。

## 快捷键

| 快捷键 | 操作 |
|---|---|
| `Ctrl+N` / `Ctrl+O` | 新建简谱 / 打开音乐文件 |
| `Ctrl+S` / `Ctrl+Shift+S` | 保存 / 另存为 |
| `Ctrl+Z` / `Ctrl+Y` | 编辑撤销 / 重做（不含磁盘删除） |
| `Ctrl+Tab` / `Ctrl+W` | 切换标签 / 关闭当前标签 |
| `Ctrl+Space` | 播放/暂停 |
| `Ctrl+Shift+F` | 聚焦项目搜索 |
| `Ctrl+I` | 展开/收起属性面板 |
| `Ctrl+Enter` | 从简谱源码更新谱面 |
| `F1` | 软件内帮助与搜索 |

## 命令行与 MCP

除了桌面编辑器，核心文件也支持命令行操作：

```powershell
python -m melody_notation.cli validate "demo_projects\我的第一份工程\山风.jianpu"
python -m melody_notation.cli export "demo_projects\我的第一份工程\山风.jianpu" -o "output\shanfeng.mid"
python -m melody_notation.mcp_server
```

MCP 使用官方 **`mcp>=2,<3`** 和 stdio 传输；不包含 SDK 1.x 回退分支。配置 Codex / DeepSeek Harness 等客户端时，指向已安装依赖的 Python 解释器，并把 `-m melody_notation.mcp_server` 作为启动参数。MCP 是可选组件，主界面不依赖客户端在线。配置示例见 `configs/deepseek-harness-mcp.yml`、`docs/DEEPSEEK_HARNESS.md`。

## 项目目录

| 路径 | 内容 |
|---|---|
| `src/` | 核心乐谱、音频、鼓点、多轨、Qt/Tk 界面与 MCP 源码（导入包名仍为 `melody_notation`） |
| `src/harmony/` | 和声知识资源 |
| `src/samples/` | 内置示例简谱 |
| `demo_projects/` | 可打开的演示工程 |
| `docs/` | 架构、技术说明与操作文档 |
| `tests/` | 单元和回归测试 |
| `devtools/` | GUI 冒烟测试及维护工具 |
| `configs/` | MCP 客户端配置示例 |
| `packaging/` | 打包配置/脚本 |
| `output/` | 用户导出文件的默认目录，**升级时请保留自己的数据** |

## 测试与常见问题

```powershell
python -m pytest -q
python devtools\qt_gui_smoke.py
```

GUI 冒烟测试需要桌面图形环境和已安装的 PySide6；在无 GUI 的运行环境中，静态检查不能替代 Windows 实机测试。

- **打不开 GUI**：在当前 Conda 环境重新执行 `pip install -e ".[gui]"`。
- **无法播放**：检查系统输出设备、音量和可选音频后端；尝试先导出 WAV 验证音乐合成。
- **MP3 导出失败**：检查 `ffmpeg -version` 和系统 `PATH`。
- **多轨文件找不到素材**：确认素材存在于原项目内、已保存且路径没有在软件外被改动或删除。
- **删错文件**：先查看系统回收站；若无法恢复，则从自己的备份找回。
- **代码更新后版本未变化**：本次功能和文档维护**不修改 v0.5.10 版本号**。

更多变更历史见 [`CHANGELOG.md`](CHANGELOG.md)。软件内按 `F1` 可搜索项目管理、简谱、鼓点、多轨、MIDI 录制、导出和常见错误。
