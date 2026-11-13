# DeepSeek Harness / DSH 兼容性说明

## 核心结论

Melody Notation 的 `melody_notation.mcp_server` 使用 MCP 官方 Python SDK 的 FastMCP，采用 `stdio` 传输。DeepSeek Harness 的 `@deepseek-ai/dsh-mcp-client` 支持连接外部 MCP stdio 服务，所以无须编写专属 DSH 工具协议。

官方来源：
- https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/mcp/mcp-client/README.zh.md
- https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/mcp.md
- https://api-docs.deepseek.com/zh-cn/guides/vision/

## 安装（Windows PowerShell）

在项目根目录执行：

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all,test]"
python -m pytest -q
```

然后打开 `configs/deepseek-harness-mcp.yml`，把其中**一条** `@deepseek-ai/dsh-mcp-client` 配置添加到 DSH 的 `cordis.yml` 或当前生效的 profile patch 的 `plugins:` 列表下。不要用这个单独文件覆盖你的 DSH 完整配置；路径按实际安装位置修改。DSH 以此方式主动启动 Python MCP 子进程；无需另开服务监听端口。

在 DeepSeek Harness 里可以试着调用：

> 请使用 melody_notation 的 MCP 工具列出可用音色，创建 C 大调 4/4 120 BPM 的四小节简谱，导出 flute 音色的 MP3 和 MIDI，并生成 PNG 简谱图片；如要覆盖已有文件先征求我的同意。

可使用的工具包含 `list_instruments`、`create_score`、`inspect_score`、`replace_measure`、`export_midi`、`export_audio`、`export_png`、`transcribe_image`。工具名应以 `mcp__melody_notation__` 开头。工作区所有文件读写都受 `MELODY_WORKSPACE` 限制。

## 图像识谱选项

DeepSeek 官方当前提供 `deepseek-flash` 图片输入，支持通过 Chat Completions 传入 base64 PNG/JPEG/WebP 等。无需 GPT 额度，但需要 DeepSeek API Key，可能产生 API 费用。

**PowerShell（临时设置，仅当前窗口）：**

```powershell
$env:DEEPSEEK_API_KEY = '你的 DeepSeek API Key'
$env:MELODY_VISION_MODEL = 'deepseek-flash'
python -m melody_notation.cli ocr 'my_score.png' -o 'output/vision_draft.jianpu'
```

如果 DSH 的 MCP 服务启用清洗后的独立环境，单纯在终端设置变量**不一定会传给 MCP 子进程**，需使用 DSH 的安全凭证注入方式或在 DSH YAML 插件的 `env` 中明确配置 `DEEPSEEK_API_KEY`（不要把明文密钥写入仓库）。可按 DSH 官方 YAML 文档用 `!!js process.env.DEEPSEEK_API_KEY` 注入。

也支持本地视觉服务器：

```powershell
$env:MELODY_VISION_BASE_URL = 'http://127.0.0.1:8000/v1'
$env:MELODY_VISION_MODEL = '你的视觉模型名称'
python -m melody_notation.cli ocr 'my_score.png' -o 'output/vision_draft.jianpu'
```

识谱只是草稿：人工核对高低音点、附点、下划线、节拍、休止符及连音后再导出，不应将不确定结果视作正确。当前不支持乐谱多声部高精度 OMR。

## 不需要大模型的功能

图形编辑器、简谱解析/节拍校验、MIDI 导出、内置钢琴/笛子音色音频生成、PNG 导出都在本地完成。没有 DeepSeek API Key 也能运行这些功能；使用 GUI 或 CLI 甚至无需启动 DSH。

## 已验证 / 未验证

- 本地基础代码及新增环境配置的单元测试可以在项目目录直接执行。
- **尚未在你的 DSH 环境里实测 MCP 服务启动、工具发现、权限及模型调用**。如果调用失败，先核对 Windows Python 路径、MCP SDK 安装、YAML 插入层级与 `MELODY_WORKSPACE`。

## v0.2 可视化编辑与 MCP 增量工具

新版增加 `edit_note`、`create_slur`、`remove_slur`、`insert_note`、`delete_note` 五个工具，继续通过相同的 `mcp__melody_notation__*` 命名空间暴露。旧版 8 个 MCP 工具仍然存在。**升级代码后重启 DSH 或重新同步 MCP 工具清单**，以便模型能发现新增工具。

示例：先用 `inspect_score` 检查音符索引，然后 `edit_note(path="examples/visual_demo.jianpu",measure_number=2,note_number=3,degree=5,octave=1,overwrite=true)`；编辑后的错误小节可通过 `inspect_score` 查看 `issues`，修正后再导出。

连音线与延音线不是一回事：本版 `create_slur` 只绘制连音弧线，不合并 MIDI 音符时长。视觉界面需使用 `python -m melody_notation.cli gui` 单独启动；DSH 是工具客户端，并不会在 Harness 内嵌入 Tkinter 窗口。
