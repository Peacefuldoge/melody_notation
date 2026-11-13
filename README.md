# Melody Notation v0.5.10 — PySide6 project workbench

## v0.5.10 — 简谱每行小节排版修复（2026-11-13）

- 「每行小节」现在代表真正固定的每行小节数（2–5）；不再因局部音符密集而提前断行。
- 密集小节自动为谱纸增加足够的水平空间，并允许横向滚动；普通宽度下优先显示完整小节行。
- 修复低八度圆点与时值下划线交错的问题；最末不满行保持靠左排版。
- 不改变乐谱节拍和已有工程文件。详细修订见 `CHANGELOG.md`。

## v0.5.8 — 演奏设置集中管理（2026-11-13）

- 钢琴主工具栏仅保留「开始录制」「输入设备」「⚙ 演奏设置」，不再铺满独立的音色、刷新、音量、音域和导出控件。
- 点击「演奏设置」打开非模态子窗口，集中管理实时演奏音色、监听音量、键盘音域、MIDI 设备重扫、键位映射及录制 MIDI 导出；关窗后按钮自动复位。
- 同一套原始控件直接移动至子窗口，保留既有信号连接、设备检测、QSettings 音域持久化与 MIDI 音高行为。切换文件或折叠键盘时自动关闭子窗口。
- 四套主题继续跟随应用样式；不改变简谱、鼓点、多轨数据及 MCP SDK 2.x 接口。

## v0.5.7 — 演奏工具栏响应式布局修复（2026-11-13）

- 移除键盘控制工具栏内层横向滚动区域，解决窄窗时控件被遮挡和工具栏断裂。
- 将录制、MIDI 设备、音色、工具按钮、监听音量、音域作为同一个响应式工具栏，按完整控件组自动折行。
- 琴键区域独立自适应，仍支持正常宽度下扩展一组八度，极窄宽度下仅琴键可横向滚动。
- 不改变演奏音高、录制、MIDI、音色或保存格式；保留四套主题。

## v0.5.6 — 键盘八度平移（2026-11-13）

- 钢琴默认基础音域 C3–C5，宽屏自动增加右侧琴键，最多到 C6。
- 演奏工具栏最右侧增加「音域 − C3–C5 +」，可从 C1 至 C5 整组平移，宽屏扩展上限随之变为 C4 至 C8；设置使用 QSettings 保存。
- 电脑快捷键和用户自定义键位随音域一起平移；**外接 MIDI 保持设备发来的原始音高**，录音的简谱及 MIDI 记录实际音高。
- 切换八度会释放正在发声的音符，避免悬挂音；原有音乐文件无需转换。

## v0.5.5 — 钢琴宽度自适应与扩展音域

- 简谱界面底部钢琴默认显示 C4–C6；窗口变宽时从右侧逐个增加白键及黑键，最多可扩展到 C7（额外一个八度），窗口缩小时自动收回。
- 既有快捷键不改变；新增的琴键可用鼠标和外接 MIDI 设备演奏。可在「键位设置」中为 C6–C7 高音区自定义键位。
- 保留 v0.5.4 的紧凑工具栏、分隔线宽度修复和窄窗口横向滚动机制。

## v0.5.4 — 键盘工具栏与侧栏拖拽修复

- 演奏工具栏将「键盘音色」并入第一行，移除常驻说明行；输入设备状态改为鼠标悬浮提示。
- 侧边栏外层 splitter 面板遵从项目树最大宽度，杜绝拖动分隔线产生空白条；收起和恢复保留用户选定宽度。
- 两八度钢琴随编辑区宽度缩放，极窄窗口才出现横向滚动；控制栏在窄窗口内独立滚动，不挤占谱面。

## v0.5.3 — 更干净的项目目录

- `output/` 是 MIDI、WAV、MP3、PNG 等**用户导出文件的默认目录**，发布包里只有 `.gitkeep`，不含历史开发产物。
- 项目截图保存在 `docs/screenshots/`；`devtools/` 的 GUI 截图工具也写入此处。
- 项目根目录新增 `.gitignore`：忽略 `output/` 中的导出文件、缓存、Python 安装构建产物、虚拟环境、`.env` 及编辑器临时文件，但保留 `output/.gitkeep`。
- **重要：升级时不要直接删除你现有的 `output/`！** 其中可能有你自己的作品。建议先备份旧项目，再从新 ZIP 中替换源码、文档与配置，保留自己的 `output/` 数据。
- 这次未更改原有音乐文件格式、MCP 接口和音频引擎。

## v0.5.2 — 侧栏折叠与键盘独立音色

- 折叠导航时只保留图标栏，编辑空间立即扩展，展开恢复原宽度。
- 简谱底部「键盘音色」只控制实时演奏与演奏 MIDI；右侧「音色」仍独立控制乐谱试听。
- 原有快速录制优化继续保留。

## v0.5.1 — 快速演奏记谱与密集谱面修复

- 快速弹奏时根据连续起音间隔自动将记谱网格细化到 **1/8 拍（32 分音符）**，减少多个音符被误合并；仍保留原始 MIDI 的真实时间、力度及和弦。
- 自动连接极短换键间隙，减少多余的 `0` 休止符；真实的停顿仍会显示为休止符。
- 简谱按每小节音符密度自动调整换行和宽度，保留可选音符的点击区域；极密集谱面可横向滚动，不再压缩得相互重叠。
- 正在录制时限制整谱重绘频率，减少快速按键时 UI 卡顿或事件积压；结束录制会同步刷新完整简谱。
- 现有 `.jianpu` / `.drum` / `.mtrack` 文件格式不变，MCP SDK 仍仅支持 2.x。

## v0.5.0 — 演奏键盘、实时简谱录制与 MIDI 设备

- 简谱编辑界面底部新增可折叠的虚拟钢琴，且源码编辑区始终位于其上方；鼓点和多轨界面不显示钢琴。
- 支持电脑键盘、鼠标弹奏和 USB MIDI / MIDI 乐器；按两秒周期扫描设备并在「自动检测」模式下自动切换输入端口。
- 点击「开始录制」后将演奏按自动选择的 1/4 或 1/8 拍网格实时转写为现有单声部简谱，包含力度与音符时长、间隙、休止符推断；支持在已有乐谱之后继续录制。
- 录制时保留独立的原始 MIDI 事件，导出时保留完整复音（和弦）、力度、实际开始/结束时间；普通菜单的 MIDI 导出仍输出当前简谱。
- 自定义电脑键位映射，保存至 QSettings，覆盖 C4–C6 范围，提供恢复默认与改绑确认。
- 琴键使用四套主题相应的白/黑、深浅蓝、米色、浅绿/深绿配色。
- 安装 `.[gui]` 时自动安装 `mido`、`python-rtmidi` 与 `sounddevice`，供外接设备扫描及低延迟实时监听；缺少音频输出设备不妨碍录制和 MIDI 导出。
- 关于限制：`.jianpu` 仍是单声部数据模型；录制时和弦只在原始 MIDI 导出中完整保留，简谱保留最先演奏的旋律音。外接设备必须能提供标准 MIDI 输入，不代表所有 USB 设备都可自动识别。

## v0.4.9 — MCP SDK 2.x 专用（不支持 1.x）

- MCP Server 直接使用 `from mcp.server.mcpserver import MCPServer`，不再提供 `FastMCP` 回退路径。
- `mcp` / `all` 可选依赖固定为 `mcp>=2,<3`，不再根据 Python 版本安装 MCP 1.x。
- **MCP 功能要求 Python 3.11+**。核心乐谱/GUI 仍保留 Python 3.10 的原项目兼容范围；Python 3.10 环境无法安装 MCP 2.x。
- DeepSeek Harness/Codex 的 stdio 服务入口和工具名称不变。

在 Windows Conda 中更新并检查：

```powershell
conda activate melody
cd D:\Work\melody_notation
python --version
python -m pip install -e ".[gui,mcp,test]"
python -c "from melody_notation.mcp_server import mcp; print(type(mcp).__name__)"
```

正常应显示 `MCPServer`。若本机曾手动安装 MCP 1.x，以上安装命令会升级到 SDK 2.x。

## v0.4.8 — MCP SDK 2.x 兼容修复

- 修复 MCP 2.x 由于 `mcp.server.fastmcp` 已移除造成的启动失败；SDK 2.x 用 `MCPServer`，旧 SDK 1.x 继续可用。
- DSH/Codex MCP 客户端沿用 `python -m melody_notation.mcp_server`；服务端仍通过 stdio 通信。
- Windows Conda 在工程根目录执行 `python -m pip install -e ".[gui,mcp,test]"` 更新 MCP 依赖和可编辑映射。

```powershell
conda activate melody
cd D:\Work\melody_notation
python -m pip install -e ".[gui,mcp,test]"
python -c "from melody_notation.mcp_server import mcp; print('MCP Server OK')"
```

DeepSeek Harness 示例服务配置在 `configs/deepseek-harness-mcp.yml`。需要用你的 Python 环境绝对路径启动；不建议让 MCP 服务把调试消息写到 stdout，以免破坏 stdio 协议。

## v0.4.7 — 新建文件默认空白

- 新建简谱：一个没有预置音符或休止符的空白小节。点击「＋ 添加音符」开始创作。
- 新建鼓点：底鼓 Kick、军鼓 Snare、踩镲 Hi-hat 三条空音轨，**默认没有任何鼓击**；可以继续增加其他鼓轨。
- 已保存的作品和内置示例维持原样；MCP / Qt / Tkinter 新建行为一致。

## v0.4.6 — 修复自定义鼓轨试听

- 修复动态鼓轨 `track_4` 等 ID 被错误作为鼓声音色交给合成器，造成“未知鼓声或音色”的问题。
- 自定义轨道更名、选择声音、保存/重新打开后均能正确试听；默认底鼓、军鼓、踩镲及多轨混音继续兼容。
- 音频合成失败与系统音频设备故障现在提供不同的错误提示。
- 项目根目录 `melody_notation/`、内部 `src/` 和导入 `melody_notation` 保持不变。

## v0.4.5 — 可管理鼓点音轨

- `.drum` 创建时仍默认有底鼓 Kick、军鼓 Snare、踩镲 Hi-hat 三个鼓轨。
- 在 PySide6 鼓点音序器的网格下方点击 **＋ 添加鼓轨** 新增，名称自动为「新建鼓点 4」「新建鼓点 5」等；双击轨道名重命名，右键轨道名可重命名、切换鼓声或删除。
- 鼓轨最多 64 条，每轨可以选择底鼓、军鼓或踩镲音色；自定义轨道会参与试听、WAV/MP3、MIDI 和多音轨编排。
- `.drum` 存储升级到 v2（轨道 ID、名称、音色及节奏），**兼容读取旧 v1 的三轨节奏文件**。保存后的 v2 文件需由 v0.4.5+ 读取。
- 沿用 `melody_notation/src/` 物理目录及 `melody_notation` Python 模块入口。


## v0.4.4 — 源码目录调整（保留现有模块接口）

工程顶层文件夹为 `melody_notation/`，代码从内部同名目录移到 `src/`。
仅物理目录改变，**Python 模块名仍是 `melody_notation`**，这样 GUI、MCP 客户端及已有插件无需修改 Python 导入路径。

升级后在工程根目录执行一次 `python -m pip install -e ".[gui,test]"` 重新建立源码映射。
以后继续使用 `python -m melody_notation.cli gui` 或 `melody-notation gui` 启动。
MCP 模块入口仍是 `python -m melody_notation.mcp_server`，MCP serverName 不变。

Melody Notation supports editable numbered scores (`.jianpu`), drums (`.drum`), multitrack arrangements (`.mtrack`), audio and MIDI exports, and Codex / DeepSeek Harness MCP tools.

## Playback hotfix — 2026-11-11

On Windows, the PySide6 preview prefers the built-in Windows MCI WAV driver (already used by Melody Notation's Tkinter player). Qt Multimedia is retained as a fallback. Playback errors are now reported in a dialog rather than only briefly in the status bar. The playback/inspector section titles have been removed without hiding their controls.

If playback is still silent, verify the selected Windows output device and system volume, then run the GUI from PowerShell to capture any error details. No additional Python audio package is required for the native Windows MCI backend.

## UI polish revision — 2026-11-11

This v0.4.3 UI-only revision removes the redundant header below the menu bar, keeps the right properties card content-sized (without a tall tinted blank region), and shows the real package version in the status bar's bottom-right corner. The inspector's panel-right toggle now lives in the editor tab strip; `Ctrl+I` still works. The four themes and original music features are unchanged.

## What's new

The PySide6 window keeps the Codex-style workbench introduced in v0.4.2, and v0.4.3 adds two music-focused refinements: a new bundled sample **月光（图片简化样例）** based on the score images you provided, and a smoother built-in preview synth with more natural envelopes and gentler ambience for piano, flute, clarinet, strings, guitar and music box. Light, dark, beige and olive themes are retained.

## Install with Conda (Windows)

```powershell
conda activate melody
cd D:\Work\melody_notation
python -m pip install -e ".[gui,test]"
python -m melody_notation.cli gui
```

`pretty_midi>=0.2.10,<0.3` is used, avoiding the earlier invalid `>=0.2.20` requirement.

## Shortcuts

- `Ctrl+N`: new score
- `Ctrl+O`: open music file
- `Ctrl+S`: save
- `Ctrl+Shift+S`: save as
- `Ctrl+Tab`: next document
- `Ctrl+Space`: play/pause
- `Ctrl+Shift+F`: focus project search (expands panel as needed)
- `Ctrl+I`: toggle inspector
- `F1`: help

Settings is the gear **below Help** in the icon rail. Adjust theme, language, default save location and native material there.

## Test

```powershell
python -m pytest -q
python devtools\qt_gui_smoke.py
python devtools\qt_settings_smoke.py
python devtools\qt_codex_layout_smoke.py
```

The original Tkinter editor is still available with `python -m melody_notation.cli tk-gui` for fallback.

## Important validation boundary

This release's music core and source syntax have been tested, but this build environment does **not have PySide6 installed**, so the redesigned Qt window was not rendered or interacted with here. Run the Qt smoke script on your machine; it uses a disposable test project. See [UI architecture](docs/CODEX_STYLE_WORKBENCH.md).
