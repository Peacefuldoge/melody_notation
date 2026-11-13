# UI 路线 A · Tkinter v0.2.2

## 设计目标

将 Melody Notation 的“许多等权操作按钮 + 常驻源码”改造成“谱面优先的简谱工作台”。不改变解析器、音符编辑语义和任何 MCP 工具签名。

- 视觉性格：安静、精确、略带温度
- 结构：工具栏 / 项目与音色条 / 属性检查器 / 谱面画布 / 可折叠源码抽屉 / 状态栏
- 色彩：中性灰蓝层次，单一蓝色交互强调色；节拍错误沿用柔和红色
- 跨平台：纯 Tk/ttk 与 Pillow；Windows 和 Linux 均可使用

## 改进清单

| 优化 | 具体表现 |
|---|---|
| 精简顶部操作 | 新建/打开放入“文件”；MIDI/WAV/MP3/PNG 放入“导出”；检查节拍/OCR/主题切换放入“更多” |
| 操作频率层级 | 保存、撤销、重做、试听保持可见；试听是唯一高对比主按钮 |
| 属性检查器 | 选中音符位置高亮，属性四行对齐，插入/删除一组，连音一组 |
| 源码抽屉 | 默认隐藏，位于谱面下方，可见时保留“从源码更新谱面”按钮 |
| 项目上下文 | 直接展示作品名、调号、拍号、BPM、音色、每行小节数 |
| 底部状态栏 | 显示当前乐谱校验状态和源码是否已同步 |
| 轻反馈 | 按钮 hover/pressed 色彩反馈，点击音符有一次约 200ms 的选中描边衰减 |
| 深浅主题 | “更多 → 切换深色/浅色主题”，不清空乐谱/撤销记录/源码草稿 |
| 快捷键 | F1 帮助、Ctrl+O 打开、Ctrl+S 保存、Ctrl+N 新建、Ctrl+Shift+S 另存、Ctrl+Enter 应用源码 |

## 关于“毛玻璃”

Tkinter 无原生的通用背景模糊或 Windows DWM Acrylic 控件。这一版使用浅灰背景、磨砂感的层叠中性色面板、1px 分隔线和对比克制的按钮来模拟轻磨砂质感，**不是系统级真实模糊**。主乐谱纸面保持白色且不模糊，确保数字、附点与连音清晰。没有尝试需要注入平台原生窗口句柄的高风险系统 API。

## 不改动的能力

`src/core.py`, `editing.py`, `png.py`, `audio.py`, `midi.py`, `mcp_server.py`, `vision.py` 的音乐行为与工具接口未改变，既有 Codex 和 DeepSeek Harness MCP 配置继续有效（仅项目路径需要更新）。

## 验证

- `pytest -q`：解析、音符编辑、PNG/MIDI/音频、帮助内容、MCP 函数测试
- `xvfb-run -a python devtools/gui_smoke.py`：实际鼠标事件、图形修改、撤销/重做
- `xvfb-run -a python -m devtools.route_a_gui_smoke`：菜单、源码、主题、文件导出、缩小窗口
- `xvfb-run -a python -m devtools.capture_workstation`：真实 UI 截图

未在用户的 Windows 环境或真实 DeepSeek Harness/Codex 实例进行端到端验证。
