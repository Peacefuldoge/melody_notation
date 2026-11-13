# 窗口内试听 · v0.2.3

## 目标

用内置音频设备播放取代 `os.startfile` / `xdg-open` / `open` 打开外部播放器。

## UI 操作

- 「▶ 试听」合成并播放当前有效乐谱；切换为「Ⅱ 暂停」
- 暂停后「▶ 继续」从暂停时间继续；按「■ 停止」回到 0
- 底部时间进度条支持拖动定位，显示 `m:ss / m:ss`
- Ctrl+Space 试听/暂停，文本源码区获焦时不抢键盘输入
- 修改乐谱、切换音色、新建/打开、OCR 替换时，旧音频立即失效
- 错误乐谱不合成；音频设备不可用时提示错误，不会打开外部播放器

## 实现与边界

- `src/audio.py` 保留原有 `synthesize()` 和导出逻辑
- `src/playback.py` 提供统一设备接口（load/play/pause/stop/seek/close/state/position/duration）
- Windows 使用 `ctypes.WinDLL('winmm').mciSendStringW` 和临时 PCM_16 WAV；设备打开和文件清理由同一个播放器对象负责，使用后自动清理临时文件
- 该接口是 Windows 历史遗留 API；未来可以替换为现代 WASAPI，而不改变 GUI 上层控制逻辑
- 非 Windows 使用可选 `sounddevice` 后端；`pip install -e ".[preview]"`
- 音频合成计算采用 ThreadPoolExecutor；通过 Tk 的 `after` 在 UI 线程读取结果，**后台线程绝不操作 Tk 控件**
- 播放进度每 140ms 查询一次，修改进度条在鼠标松开时执行 seek
- GUI 关闭时释放音频设备、临时 WAV，并停止线程池接收新任务
- 不改变 MCP Server、Codex/DSH 配置、MIDI 与 WAV/MP3/PNG 导出

## 测试

- `python -m pytest -q`：包括 WinMM 假驱动状态测试、sounddevice 假后端测试
- `xvfb-run -a python -m devtools.transport_gui_smoke`：GUI 中播放/暂停/继续/停止/定位/撤销旧音频的无声设备模拟测试
- Windows 11 设备输出、音量、输出路由需要在实际电脑上确认（此 Linux 容器没有 Windows 音频设备）
