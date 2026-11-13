# Melody Notation v0.4.4 — 目录迁移

## 新目录结构

```
melody_notation/
├── src/                  # 实现代码（旧版为 melody_notation/）
│   ├── __init__.py
│   ├── cli.py
│   ├── qt_gui.py
│   ├── mcp_server.py
│   ├── harmony/
│   └── samples/
├── demo_projects/
├── tests/
├── docs/
├── configs/
├── pyproject.toml
└── start-pyside6.ps1
```

## 安装和启动

在项目根目录激活原来的 Conda 环境：

```powershell
conda activate melody
cd D:\Work\melody_notation
python -m pip install -e ".[gui,test]"
python -m melody_notation.cli gui
```

安装后也能用 `melody-notation gui` 启动。MCP 配置无需更改模块路径（`melody_notation.mcp_server`）。

## 为什么不把 import 名字也改成 src？

`src` 是工程内部的源文件目录，不宜作为对外公开的 Python 包名称。保持原模块名可避免既有 MCP 客户端、第三方脚本、插件及测试全部失效。此项目使用 setuptools 的 `package-dir` 让文件路径和导入名称分离。

本次不修改音乐业务逻辑、音频合成、MCP 工具名及已有数据文件。
