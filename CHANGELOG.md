## 0.5.10 — 简谱每行小节与记谱符号排版修复（2026-11-13）

- 「每行小节」改为严格指定每个完整谱面行的小节数量（2–5），不再被旧版按音符密度提前换行的逻辑覆盖。
- 小节音符较密时拓宽渲染画布，以允许水平滚动并保留音符间距，避免强行压缩产生重叠；不修改实际节拍或小节数据。
- 最后一行不足指定数量时左对齐并保留正常小节宽度，避免单个小节撑满整张谱纸；多余空间按音符密度分配。
- Qt 画布针对每行小节数设置合理的最低缩放比例，普通宽度下尽量显示完整的四小节；极密集或窄窗口继续提供水平滚动。
- 统一时值下划线、低八度圆点和小节编号的垂直层级，修复短时值低音符号相互遮挡的问题；选中音符的热区随之扩展。
- 保留现有 .jianpu/MIDI/MCP、键盘录制和其他编辑功能。

## 0.5.9 — 窗口缩放稳定性与崩溃日志（2026-11-13）

- 钢琴工具栏改为持久化 Qt height-for-width 流布局：拖拽窗口或分隔线时，不再反复销毁/重建子布局，也不在 resizeEvent 中改变自身固定高度。
- 钢琴滚动区域将可见琴键宽度调整合并到事件循环中执行，并预留稳定的滚动条高度。
- 简谱画布高度更新改成延迟合并，避免在 Qt resizeEvent 内修改几何尺寸引发递归布局。
- GUI 启动时开启 faulthandler 诊断日志；Windows 默认路径：`%LOCALAPPDATA%\MelodyNotation\logs\crash.log`。如果出现原生闪退，保留 Python 线程堆栈辅助定位。
- 不修改 .jianpu/.drum/.mtrack、MIDI、MCP、音频合成算法。
- 自动化测试包括布局宽度转换、源码回归和 Qt GUI 压力测试脚本；Windows 本机渲染测试仍需执行。

## 0.5.8 — 钢琴演奏设置窗口与主工具栏精简（2026-11-13）

- 将原来散落在键盘上方的「键盘音色、MIDI 设备刷新、键位设置、录制 MIDI 导出、监听音量、音域调节」移入统一的非模态「演奏设置」子窗口。
- 主工具栏现在只有「开始录制」「输入设备」「⚙ 演奏设置」，缩放时保持紧凑布局，不再需要横向滚动控件组。
- 保留同一批控制控件及原有回调，因此音色独立切换、音量、八度平移、自定义键位、设备扫描和 MIDI 导出行为不变；MIDI 状态在子窗口可见。
- 切换简谱标签、折叠键盘或清理编辑器时安全关闭子窗口，窗口关闭会同步复位设置按钮。
- 无音乐数据格式或 MCP SDK 变更，继续保持 `melody_notation/src/` 工程结构。

## 0.5.7 — 修复钢琴工具栏在窄窗重叠和遮挡（2026-11-13）

- 取消演奏工具栏的横向滚动容器及外侧独立控制栏，改为统一的自适应换行布局。
- 输入设备、键盘音色、录制按钮、监听音量和八度切换成组显示；音域在所在行最右侧。
- 修复缩放时出现第二个滚动条、控件裁切与错位的问题，保持底部琴键独立布局。
- 补充宽/窄窗口分行计算与 Qt 界面回归测试；保留既有文件格式与 MCP 2.x 接口。

## 0.5.6 — 可调起始八度与右侧音域快捷控制（2026-11-13）

- 默认键盘基础范围 C3–C5，宽屏可动态扩展最多到 C6；新增控制栏最右侧「− / C3–C5 / +」八度调节，允许 C1–C5 起始。
- 电脑键盘映射（含自定义）跟随八度平移；MIDI 外接设备不移调；录制继续保留真实音高。
- 持久化用户选择，切换时安全释放按下的音符；升级不改 `.jianpu` 或原始演奏 MIDI 格式。

## 0.5.5 — 钢琴右侧动态扩展一组八度（2026-11-13）

- 简谱底部钢琴根据实际编辑器宽度动态显示 C4–C6 到 C4–C7；较宽时从右侧逐个增加完整白键与相邻黑键，最多增加 1 个八度。
- 窄窗口继续使用 v0.5.4 的缩放与横向滚动，且宽度不变时不会重复重建琴键布局。
- 鼠标弹奏、实时录制、外接 MIDI 以及四套主题适用于新增琴键；自定义电脑键位对话框扩展到 C7，并增加可滚动区域。默认键位映射不变。
- 不改变 `.jianpu`、`.drum`、`.mtrack`、MIDI 格式、MCP 工具或 `src/` 目录结构。

## 0.5.4 — 钢琴工具栏整理与分隔线拖拽修复（2026-11-13）

- 将「键盘音色」移到钢琴控制工具栏第一行，删除下面的冗长演奏说明行。设备连接、断开及实时音频警告通过输入设备/刷新按钮的悬浮提示查看。
- 给项目导航外层 NavShell 施加与侧栏一致的最小/最大宽度，防止横向拖动分隔线时在导航与编辑器之间留下死白区；折叠只剩 54px 图标栏，展开恢复最近宽度。
- 宽度不足时钢琴键自动缩放，保留两八度完整键盘；更窄时才允许横向滚动。工具栏本身横向滚动，监听音量始终靠右显示。
- 保留现有 `.jianpu`、`.drum`、`.mtrack`、MIDI、MCP SDK 2.x 和 `melody_notation/src/` 结构；不更改音乐数据和演奏算法。

## 0.5.3 — 发布目录清理与 Git 忽略规则（2026-11-13）

- 新增项目根目录 `.gitignore`，默认忽略 `output/` 下的用户导出文件、Python 缓存、构建产物、虚拟环境、私有 `.env` 配置与编辑器临时文件。
- `output/` 仅保留 `.gitkeep`，作为应用的默认 MIDI/WAV/MP3/PNG 导出位置；本次发布包不再夹带历史测试音频或测试 MIDI。
- 将原来 `output/` 中的 25 张开发截图移动到 `docs/screenshots/`，并修改 GUI 开发截图脚本的写入路径；修复旧脚本中硬编码的本机路径。
- 不修改 `.jianpu`、`.drum`、`.mtrack`、MCP、播放或导出 API。升级时**只替换源码，务必保留本机已经导出的 `output/` 用户文件**。

## 0.5.2 — 项目导航折叠与键盘音色切换（2026-11-13）

- 修复项目导航折叠只隐藏内层侧栏，却没有收缩 QSplitter 外层导航宽度的问题；折叠时仅保留 54px 图标导航栏，工作区自动扩展，恢复时返回原有侧栏宽度。
- 简谱底部钢琴新增独立「键盘音色」切换器，支持钢琴、吉他、八音盒、长笛、单簧管、小提琴、弦乐与 Game Boy 音色。保持键盘音色与右侧乐谱试听音色互不干扰。
- 改进实时监听的各乐器波形，音色切换对后续音符立即生效；正在释放的音符保留原音色。演奏 MIDI 导出使用录制界面当前选择的乐器程序。
- 保留 v0.5.1 快速演奏记谱、原始 MIDI、外接 MIDI 自动检测、`.jianpu` 文件格式，以及 `melody_notation/src/` 安装映射与 MCP 2.x 专用接口。

## 0.5.1 — 快速弹奏自动量化与谱面拥挤修复（2026-11-13）

- 快速连续起音时自动从 1/4 拍细化至 1/8 拍（32 分音符）记谱，保留快速按键而不是合并到同一格。
- 将短暂换键间隙视为连贯演奏，减少无意义休止符；真实停顿仍以休止符表示。
- 简谱渲染根据小节音符数量动态分配行宽和换行；极密小节加宽纸面并允许水平滚动，音符与点击热区不再重叠。
- 实时录制中合并频繁的谱面重绘请求，降低 UI 渲染对快速输入的影响。
- 原始演奏 MIDI 始终保留原始时间戳、力度与复音；`.jianpu` 格式、音色、鼓点及多轨格式不变。

## 0.5.0 — Real-time performance keyboard (2026-11-12)

- Added collapsible score-only bottom piano; source view sits above the keyboard.
- Added computer-key and mouse performance, user-definable key mapping, and four theme-aware piano palettes.
- Added auto-discovering MIDI input via mido/python-rtmidi with connect/disconnect handling and manual override.
- Added optional low-latency polyphonic sounddevice monitor; unavailable output does not block transcription.
- Added real-time quantized one-voice score projection, transactional undo and separate raw/polyphonic MIDI performance export.
- Preserved .jianpu format, .drum/.mtrack editors, project src layout, MCP SDK 2.x-only API and existing exports.

## 0.4.9 — MCP Python SDK 2.x 专用（2026-11-12）

- 移除 MCP 1.x 的 `FastMCP` 导入回退路径，统一使用 SDK 2.x 的 `MCPServer`。
- `mcp` 与 `all` 可选依赖要求 `mcp>=2,<3`；MCP 服务运行环境要求 Python 3.11+。
- 所有 MCP 工具测试替换为 SDK 2.x 对应的模拟类，并增加仅安装 SDK 1.x 时拒绝加载的回归测试。
- 保留 31 个工具的 API、stdio 服务入口、`src/` 目录结构及音乐文件格式；版本号更新至 v0.4.9。
- 真实 MCP SDK 2.x 客户端握手需在安装 SDK 的环境中验证。

## 0.4.8 — 兼容 MCP Python SDK 2.x（2026-11-12）

- 修复 `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`：MCP 2.x 使用 `MCPServer`，旧环境兼容 MCP 1.x 的 `FastMCP`。
- 保持 MCP 服务名称、31 个工具、stdio 启动命令、文件格式及现有工作区权限检查不变。
- MCP 可选依赖按 Python 版本选择：Python 3.11+ 安装 MCP 2.x；Python 3.10 安装 MCP 1.x（需要已有旧环境）。
- 增加模拟 SDK v1/v2 导入的自动化回归测试；真实 MCP 2.x 客户端握手仍需在已安装 SDK 的用户环境验证。
- 修订 README 的兼容说明，版本号提升至 v0.4.8。

## 0.4.7 — 新建文件默认空白（2026-11-12）

- 新建 `.jianpu` 默认一个空小节，不预置音符或休止符；可点击「＋ 添加音符」录入第一音，源码文本往返不丢失空小节。
- 新建 `.drum` 默认保留底鼓、军鼓、踩镲三条音轨，但所有步进格为空；新增轨道仍从「新建鼓点 4」编号。
- 统一 PySide6 / Tkinter / 项目 API / MCP 的默认创建行为；原有示例文件和已保存作品内容不修改。
- 补充空白文件保存、重新打开、音符插入及鼓点编辑的回归测试。
- 保持 `melody_notation/src/` 物理目录结构与 Python 模块名，版本递增到 v0.4.7。

## 0.4.6 — 修复新增鼓轨无法试听（2026-11-11）

- 修复 PySide6 后台试听合成器误将鼓轨 ID（如 `track_4`）当作鼓声音色、导致“未知鼓声或音色”的问题；改为从每条鼓轨的 `sound` 字段解析 kick/snare/hihat。
- 同声音类型的多条鼓轨复用一次 one-shot 音色采样，避免无节奏音轨的无谓合成。
- 错误弹窗将音频合成异常与 Windows 输出设备异常区别提示。
- 新增回归覆盖自定义音轨、新文件保存重开、重命名、改鼓声、删除旧轨、不同速度和空音轨；`.drum` v1/v2 格式不变。
- 同步安装包、源码、界面及开发工具版本为 v0.4.6；继续使用 `melody_notation/src/` 物理结构。

## 0.4.5 — 可增删重命名的鼓点音轨（2026-11-11）

- 鼓点音序器新增「＋ 添加鼓轨」入口，默认三轨不变；新轨名称自动编号。
- 支持双击音轨名重命名，以及右键重命名、选择 kick/snare/hihat 鼓声和删除轨道（有鼓点时确认）。
- 新增鼓轨完整接入编辑撤销/重做、保存读取、鼓点试听与导出、多轨混音、MCP 工具；Tkinter 旧界面也能显示/管理自定义行。
- `.drum` 格式升级为 v2，保存每条鼓轨独立 ID/名称/鼓声/鼓点，支持加载原有 v1 文件；旧版应用无法读取新版 v2，请按需备份原始文件。
- 保留根目录 `melody_notation/` + 子目录 `src/`，CLI/MCP Python 模块名不变。

## 0.4.4 — 源码目录调整与兼容保留（2026-11-11）

- 将项目根目录命名为 `melody_notation/`，内部 Python 源码目录更名为 `src/`。
- 使用 setuptools `package-dir` 映射：`src/` 对外仍然是 `melody_notation` Python 包；公开 CLI、MCP 模块路径与工具服务名称保持兼容。
- 修正测试、文档、Skills 中基于文件系统的源码路径，保留 `.jianpu`、`.drum`、`.mtrack` 数据格式和所有 V5 播放、旋转动画、延音修复。
- 统一程序版本和项目/插件元数据为 v0.4.4；历史版本记录保留。
- 升级时需要从工程根目录执行一次：`python -m pip install -e ".[gui,test]"。

## 2026-11-11 — v0.4.3 V5 修复与自然延音（版本号未变）

- 修复 `.mtrack` 打开后首帧绘图时 `name 'major' is not defined`：4 拍/小节刻度现在明确初始化，不修改 `.mtrack` 数据格式。
- 播放按钮在后台 WAV 合成期间显示 12 辐射线旋转指示及“合成中…”；合成成功、失败、停止或切换文档均清理指示状态。等待期间连续点击不会重复提交任务，停止可取消当前预览结果。
- 内置合成器统一使用“按键保持 + 自然释放”的包络。钢琴、吉他、八音盒不再在起音几十毫秒后突然静音，木管/弦乐等在音符结束时短暂平滑释放；快节奏装饰音采用较短释放。
- 多轨预览与导出增加轻微共享空间感，并为释放尾音留出更充分的缓冲时长；所有 MIDI 和节拍事件时间保持原样。
- 额外回归测试验证启动时刻度定义、旋转状态接线、音符中段响度以及 WAV 试听。
- 已通过非 GUI 自动化测试；Windows 上真实 PySide6 窗口和声音设备需本地复核。

# Changelog

## 0.4.3 audio/UI hotfix (2026-11-11) — Windows preview and inspector cards

- Windows PySide6 playback now tries the project's existing native WinMM/MCI WAV backend first. If it cannot open/play, it falls back to Qt Multimedia instead of relying exclusively on Qt multimedia plugins.
- Playback transport (play/pause, stop, position scrub and speed changes) follows the active backend; WAV rendering remains asynchronous.
- Preview synthesis failures and Qt audio errors now show actionable error dialogs. Silent Qt startup failures trigger a delayed playback check.
- Removed the visible "试听控制" / "编辑属性" headers from the right inspector, keeping the two compact rounded cards.
- No change to .jianpu/.drum/.mtrack formats, audio synthesis, MIDI, MCP or version 0.4.3. Windows GUI/audio behavior still requires local device validation.

## 0.4.3 UI polish, pass 2 (2026-11-11) — native titlebar and flat controls

- Native Windows 11 titlebar now follows the active theme's caption, caption-text and border color while continuing to request the system glass-like backdrop when enabled; no replacement for Windows caption buttons.
- Removed the three unwanted menu chevrons from the icon rail New action, sidebar New music file button, and Project actions button, while retaining their click-to-open menus.
- Changed Qt numeric spin buttons into flat, borderless steppers with subtle theme-aware hover states.
- All music engine, score model, export, workspace and MCP APIs remain unchanged. Version stays 0.4.3.


## 0.4.3 UI polish (2026-11-11) — layout-only revision

- Removed the redundant 46px secondary top chrome; the native titlebar and File/Edit/View/Export/Help menubar remain intact.
- Moved the inspector toggle to the top-right corner of the editor tab strip; its Ctrl+I shortcut and View menu command still work.
- Fixed the right properties card expanding into a large tinted empty panel; card contents stay compact with clear unused sidebar space.
- Set stack/editor page backgrounds to transparent, avoiding mismatched inner background rectangles across all four color themes.
- Added a persistent `Melody Notation v0.4.3` label to the bottom-right status bar, including when the inspector is hidden.
- Updated a stale unit-test expectation from the pre-v0.4.3 0.35 s tail to the existing v0.4.3 0.45 s preview reverb tail; no synthesis code was changed.
- No music file formats, synthesis algorithms or MIDI/export code were changed. Package remains v0.4.3 with a UI-only patch.

## 0.4.3 — New sample + smoother preview synth

- Added a bundled built-in sample **月光（图片简化样例）** derived from the user-provided score images. Lyrics and credit text are omitted on purpose; the phrasing/rhythm is simplified to keep the sample editable.
- Exposed the new sample in both the PySide6 and Tkinter example menus.
- Improved the built-in offline preview synth with gentler envelopes, lighter ambience reverb, softer clipping, and more instrument-specific timbres for piano, flute, clarinet, strings, guitar and music box.
- Regenerated sample preview exports for the new score.

## 0.4.2 — Codex-style project workbench

- Redesigned the **PySide6 application shell** around a persistent icon rail, collapsible project navigation, central document tabs and optionally visible right inspector.
- Replaced the duplicated sidebar dropdowns with a single compact new-file menu, project context menu, and conventional File/Edit/View/Export/Help menu bar.
- Moved Help and Settings to the bottom of the icon rail; themes continue to come from Settings.
- Added a recent-project list and consistent high-DPI line icons for panel controls.
- Added inspector visibility toggle (Ctrl+I) and remembered its setting.
- Kept four theme palettes, existing notation renderer, drum sequencer, multitrack timeline, MIDI/audio/export and MCP endpoints unchanged.
- Added `devtools/qt_codex_layout_smoke.py` and UI design notes.

## 0.4.1

Four coordinated themes, vector icons, preferences dialog, bilingual UI, and Windows native material best-effort support.
