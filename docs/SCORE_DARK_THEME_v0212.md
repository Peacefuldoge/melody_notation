# v0.2.12 — 深色乐谱画布

## 实现范围

在深色主题下，**编辑器内的乐谱本身**不再使用白色背景；谱纸切换到石墨蓝灰 `#293544`，音符及其附点、短横线、八度点、连音线、小节线、装饰音、转调与小节编号都使用对应的浅色调。当前选中音符为深蓝底 + 浅蓝边框，节拍错误小节使用暗红色提示。浅色主题保留原来白底黑字的样式。

切换主题由 `Editor.toggle_theme()` 发起，`Editor.redraw()` 按 `self.theme_mode` 将 `theme='dark'` 或 `theme='light'` 传入 `render_score()`。绘制颜色统一维护在 `src/png.py` 的 `SCORE_THEMES` 中。`render_score()` 的尺寸、音符命中区域以及返回值结构均不变，保留点击、滚动、居中与缩放行为。

## 导出行为

`export_png()` **默认仍然导出白底黑字**，适合打印与分享，不受 GUI 当前主题影响。若代码调用方明确需要暗色图片，可使用：

```python
export_png(score, 'score-dark.png', theme='dark')
```

MIDI / MP3 / WAV、`.jianpu`、项目格式与 Codex / DeepSeek Harness MCP 均未修改。

## Windows / Conda

```powershell
conda activate melody
cd D:\Work\melody-notation-v0.2.12
python -m pip install -e ".[all,test]"
python -m melody_notation.cli gui
```

从 v0.2.11 最小更新，仅需替换 `src/png.py` 与 `src/gui.py` 并重启 GUI；若仍使用 editable install，一般无需重新安装。请先备份本地手动修改的文件。

## 验证

```bash
python -m pytest -q
# 可用 Linux Xvfb 时：
PYTHONPATH=. xvfb-run -a python devtools/score_dark_theme_smoke.py
```

GUI 冒烟测试覆盖载入《荒》、深浅主题切换、选中音符保留与真实截图。自动化测试覆盖暗色谱纸/墨迹、连音与选中高亮、无效拍数颜色、PNG 默认打印色不变。当前未在用户 Windows 上测试。
