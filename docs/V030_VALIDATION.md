# v0.3.0 Validation Summary

- `PYTHONPATH=. pytest -q`：**65 passed / 1 skipped**（跳过的测试需要可选 MCP SDK；实际 MCP 连接尚未在本机验证）。
- `xvfb-run -a python devtools/multitrack_gui_smoke.py`：真实启动 Tkinter，创建/重开多轨、修改并保存片段、点击鼓点网格、保存、切换主题；生成实际截图。
- `.mtrack` / `.drum` JSON 读取、保存、长度边界校验、来源路径保护、中文项目文件重命名引用、剪辑反转、裁剪、Mute/Solo、合成 WAV、标准分轨 MIDI 的自动化测试通过。
- `python -m melody_notation.cli validate` 可检查两种新文件类型；`export` 已验证能导出 `.mtrack` MIDI。
- 实际项目示例生成 `output/demo_multitrack.{mid,wav,mp3}`，MIDI 包含 3 条轨道（1 旋律、2 鼓轨）；鼓轨 `is_drum=True`，并使用 GM 36/38/42。
- Windows GUI / MCI 扬声器输出、真实 Codex 与 DeepSeek Harness MCP 端到端连接、跨系统打包安装 **尚未实测**；请在 Windows Conda 环境中验证。
- 本版 Tkinter 多轨和鼓点编辑器是独立的子窗口；不包含真正的 PCM 反向播放、拖拽裁剪手柄、VST/SF2 鼓源或 AI Chat。
