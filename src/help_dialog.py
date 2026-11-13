"""In-app Chinese tutorial for the numbered-notation desktop editor.

This help window is deliberately read-only and modeless: reading or copying an
example must never overwrite the user's current score.
"""
from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk


EXAMPLE_SCORE = """title: 我的第一首简谱
key: C
time: 4/4
bpm: 120
notes:
| 1 2 3 5 | 6/2 5/2 3 2 1 |
| ( 3' 2' 1' 7 ) | 1' - - - |
"""


@dataclass(frozen=True)
class HelpSection:
    title: str
    content: str


HELP_SECTIONS = (
    HelpSection("项目与多文件", """# 项目工作台（v0.3.0）

## 项目是什么？
一个项目是你电脑上的普通文件夹，可以放许多 .jianpu 简谱、.drum 鼓点、.mtrack 多音轨编排文件和子文件夹。每张简谱都是独立文本文件，可用其他编辑器打开，也能由 Codex / DeepSeek Harness 通过原有 MCP 工具操作。

## 建立项目
1. 左栏「项目」右侧点 ＋：创建新的项目；在标题旁的更多菜单可打开已有项目。
2. 最近打开的多个项目会在「项目」里列出，展开可找到 .jianpu 文件。
3. 左栏「✎ 新建简谱」：在选中的项目/子文件夹中创建新乐谱，自动打开标签。
4. 项目栏底部「＋ 新建文件夹」可建立子项目，例如乐章、主题曲、角色配乐。
5. 双击项目树中的简谱文件，在中央多标签工作区打开；按 F2 可重命名选中项。

## 多标签编辑
• 每一张简谱有自己的音符、撤销历史、选中位置和未应用的源码草稿。
• Ctrl+Tab 切换到下一个标签，Ctrl+W 关闭当前标签。
• 未保存的标签前有 ●；关闭时会询问是否保存。
• Ctrl+S 只保存当前标签；Ctrl+Shift+S 另存为。
• 内置示例在新标签中作为副本打开，不会覆盖项目里其他文件。

## 版面说明
左侧导航会随浅色/深色主题切换，包含项目、最近打开和搜索；左侧「文件 / 编辑 / 导出 / 工具」是唯一的完整操作菜单，标题不再重复展开菜单。保存与另存为均在「文件」菜单，也可使用 Ctrl+S / Ctrl+Shift+S。窄侧栏在折叠状态下提供快捷操作。中央是乐谱和多标签，右侧上方是试听控制卡片，下方是可滚动的音符属性。点 ≡ 可收起或展开左侧栏；Ctrl+Shift+F 聚焦搜索。源码从乐谱上方「源码」按钮展开。

## 鼓点与多音轨
在「文件」菜单新建 .drum 鼓点或 .mtrack 多音轨编排；双击项目树中的文件，可打开对应的独立编辑窗口。 .drum 是每小节 16 格、底鼓/军鼓/踩镲的可编辑节奏，支持原声、电子、8-bit 三套鼓组。 .mtrack 支持添加项目内 .jianpu/.drum 作为片段、改变轨道顺序、裁剪、反转片段音符时间顺序、调整起始拍、静音和 Solo，并混音导出 WAV/MP3/分轨 MIDI。

## 尚未开发
项目树暂不支持拖拽排序；多音轨/鼓点当前在独立窗口打开，不与简谱共用中央标签；AI Chat 与 Diff 审批将在后续版本开发。"""),
    HelpSection("快速入门", """# 第一次使用 Melody Notation

Melody Notation 可以手动编辑数字简谱、试听旋律，并导出 MIDI、音频和 PNG 乐谱。核心功能不需要登录 AI 服务。

## 5 步完成一段旋律
1. 启动软件后，中央会显示一份示例简谱；也可在左侧「文件 → 内置示例」里选择《荒》等乐谱。
2. 单击中央谱面上的数字音符，右侧 Inspector 会显示音符属性。
3. 修改「音级 / 休止」「高低八度」「音符时值」等选项；选中后立即更新谱面。
4. 在左侧「编辑 → 检查节拍」确认节拍正确，再到右侧「试听控制」播放。
5. 点击左侧「导出」菜单，选择 MIDI / WAV / MP3 / PNG，保存作品。

提示：点击乐谱区右上角「显示简谱源码」，即可打开底部源码抽屉。改完文本后必须点击「从源码更新谱面」或按 Ctrl+Enter。

## 在软件里找帮助
左侧窄图标栏底部「?」按钮，或键盘 F1，可以随时打开教程；不会覆盖正在编辑的乐谱。"""),
    HelpSection("可视化编辑", """# 点击音符，直接修改

## 选中与修改
• 在中央谱面上单击一个数字，会出现选中标记。
• 右侧属性面板显示它位于第几小节、第几个音符。
• 「音级 / 休止」可以选择 0（休止）或 1～7。
• 「高低八度」可以选 -3 至 +3；「音符时值」可以选半拍、一拍、两拍等。
• 「临时升降号」可选择自然、升号 # 或降号 ♭。
• 「演奏记号」可设置颤音、波音、回音、断奏、重音、保持音与同音震音。
• 属性下拉框选定后会自动应用，也能点击「应用音符修改」。

## 增删与撤销
• 「后插入」：在选中音符之后加入一个新音符。
• 「删除」：删除选中的音符。
• 左侧「编辑 → 撤销/重做」或 Ctrl+Z / Ctrl+Y：回退或重做可视化修改。
• 调整音符时值或插入音符后，某小节可能暂时不是 4 拍；这是允许的编辑草稿状态，修正后才可导出。

## 乐谱浏览
• 鼠标滚轮上下滚动谱面；右侧音符属性过长时可使用属性区滚动条。
• 乐谱区域右上角「每行小节」可选择 2、3、4、5，小节数固定；密集乐谱会加宽以避免重叠。
• 点击乐谱区域右上角「显示简谱源码」，可在底部展开源码编辑抽屉。"""),
    HelpSection("简谱语法速查", """# 简谱源码格式与常见记号

以下是本软件接受的文本格式，不等同于所有传统简谱印刷符号。

## 音高
1 2 3 4 5 6 7    七个音级，默认每个音符 1 拍
0                  休止 1 拍
1'                 高一个八度的 1
1''                高两个八度的 1
5,                 低一个八度的 5
#4                 升 4
b7                 降 7

## 时值（假定四分音符为一拍）
5                  1 拍
5/2                半拍（0.5 拍）
5/4                四分之一拍（0.25 拍）
5/8                八分之一拍（0.125 拍）
5.                 附点：1.5 拍
5./2               附点半拍：0.75 拍
5..                1.75 拍
5 -                将前一音延长 1 拍（总共 2 拍）
5 - -              将前一音延长 2 拍（总共 3 拍）
R                  整小节休止（独占一个小节）

## 演奏记号：放在音符末尾
5{tr}             颤音（与上方邻音快速交替）
5{mordent}        上波音（主音-上邻音-主音）
5{lower_mordent}  下波音
5{turn}           回音（上邻音-主音-下邻音-主音）
5{staccato}       断奏（缩短实际发声）
5{accent}         重音（提高 MIDI 力度）
5{tenuto}         保持音（稍延长实际发声）
5{tremolo}        同音震音（快速重复主音）

以上记号不增加小节拍数；不支持在休止符 0 上使用。

注意：斜杠后面只允许 2、4、8，不能随意写其他数字。比如 6/5 是无效写法。如果要表示两个音符 6 和 5，请写「6 5」。

## 小节
使用竖线 | 分隔小节。4/4 表示每小节共 4 拍：

```text
| 1 2 3 5 | 6/2 5/2 3 2 1 |
```

注意：上面第二小节为 0.5+0.5+1+1+1 = 4 拍。

## 元数据

title: 曲名
key: C
time: 4/4
bpm: 120
key_changes: 25=Bb    （可选：从第25小节开始转为降B调）
notes:

可用音调以程序实际支持的调性为准，默认建议从 key: C 开始。"""),
    HelpSection("连音线", """# 如何绘制连音线（Slur）

## 在图形界面中操作
1. 在中央谱面点击连音的第一个音符。
2. 点击右侧音符属性卡片底部「连音线」中的「设起点」。
3. 点击连音结束的音符。
4. 点击「连接」，谱面会画出连音弧线。
5. 如需删除，选中连音范围内的音符，点击「移除」。

连音线可以跨小节，但不允许相互嵌套、交叠，也不能跨越休止符。

## 在源码中操作
连音标记 ( 和 ) 必须是独立符号，前后用空格隔开：

```text
| ( 1 2 3 5 ) | 6 5 3 1 |
```

如果跨小节，允许在另一小节结束：

```text
| 1 2 ( 3 5 | 6 5 ) 3 1 |
```

## 重要区别
Slur（圆滑线）表示一段音乐乐句，和 Tie（延音线）不同。
当前版本会绘制 Slur，但不会把它自动变成真实乐器连奏演奏法；Tie 尚未实现。"""),
    HelpSection("试听与导出", """# 听旋律、保存成文件

## 选择音色
右侧「试听控制」中的「音色」可选择：
piano 钢琴、flute 笛子、violin 小提琴、strings 弦乐、guitar 吉他、music_box 音乐盒、clarinet 单簧管、gameboy 复古 8-bit 芯片音色。

目前默认音色是程序合成的近似乐器音；并不是专业采样音源。可在后续工作流中选用 SoundFont 音色库。

## 试听
点击右侧「▶ 播放」，软件会检查乐谱，使用当前音色合成旋律并在应用内播放。
• 播放中点击「Ⅱ 暂停」，再次点击「▶ 继续」即可接着播放。
• 点击「■ 停止」停止试听，再点「播放」会从头重播。
• 右侧试听控制卡片的进度条可用鼠标拖动，定位到歌曲的指定时间。
• Ctrl+Space 可以播放/暂停（源码文本编辑框获得焦点时除外）。
• 右侧「倍速」提供 1.00×、1.25×、1.50×、1.75×、2.00×；调整正在播放的速度将从相同乐句位置继续。
• 倍速只影响试听，不会修改 BPM 元数据，也不改变正常速度下导出的 MIDI/WAV/MP3。
• 改动音符或切换音色后，旧试听自动清除；下一次播放使用最新乐谱。
• Windows 使用内置音频接口，无需额外安装播放器。macOS/Linux 需安装可选的 sounddevice 后端。

如果无法播放，请检查系统音量、默认输出设备；macOS/Linux 可运行 python -m pip install sounddevice。

## 文件格式
• MIDI（.mid）：可在 FL Studio、Cubase 等 DAW 中继续编辑音符。
• WAV（.wav）：无损音频，通常无需额外工具。
• MP3（.mp3）：压缩音频，需要安装 FFmpeg 并配置 PATH。
• PNG（.png）：将当前简谱绘制为图片。
• .jianpu：可编辑的源文件，建议每次导出前先「保存」。

如果节拍检查没有通过，软件会阻止试听和导出，避免产生拍数错误的作品。"""),
    HelpSection("图片自动识谱", """# 从图片生成可编辑简谱（Beta）

1. 点击左侧「工具 → 图片识谱（Beta）」。
2. 选择 PNG / JPG / JPEG / WEBP 图片。
3. 软件会先询问你是否允许把图片发送到所配置的视觉模型 API。
4. 识别完成后，生成可编辑的简谱草稿；逐小节核对音符、节拍和连音。
5. 修正后保存为 .jianpu，再导出所需格式。

## 注意
• 这项功能依赖视觉模型配置，并非完全离线；可能产生 API 使用费用。
• 细小的高低八度点、附点、下划线、连音线容易识别错误。
• 识别结果不是经过校对的正式乐谱，务必人工检查。
• 图片识谱发生问题时，仍可直接手动输入简谱。"""),
    HelpSection("AI 助手集成", """# Codex / DeepSeek Harness 双端兼容

Melody Notation 提供独立的 MCP Server。Codex、DeepSeek Harness 可以共用同一组音乐工具；桌面编辑器不依赖 AI 助手。

## 常见操作
• 读取 / 创建简谱
• 替换小节，修改、插入或删除音符
• 创建、移除连音线
• 校验乐谱、导出 MIDI、音频、PNG
• 可选调用视觉识谱

## Conda 安装
在项目目录执行：

```powershell
conda activate melody
python -m pip install -e ".[all,test]"
python -m melody_notation.cli gui
```

MCP 客户端应配置为调用 melody 环境中的 python.exe，并运行模块 melody_notation.mcp_server。
具体配置参考项目 README.md 和 docs/DEEPSEEK_HARNESS.md。不同版本的 Harness 配置格式可能不同，请以实际运行环境为准。"""),
    HelpSection("常见问题与快捷键", """# 常见错误与处理方法

## 报错：Invalid note '6/5'
原因：软件把 / 当成时值分母，仅接受 /2、/4、/8。
• 要两个音符：改为「6 5」
• 要半拍的音 6：改为「6/2」
• 要将音 6 延长一拍：改为「6 -」
修改后点击源码抽屉里的「从源码更新谱面」。

## 报错：Measure ... beats; expected 4
原因：该小节的音符时值之和不是 4 拍（当 time: 4/4 时）。
例如：| 1 2 3 5 | 是 4 拍；| 1 2 3 | 只有 3 拍。
可以补一个音符、补休止符 0，或者调整已有音符的时值。

## 报错：有未应用的源码更改
原因：简谱源码抽屉中的文本已经改过，但尚未解析。
点击「从源码更新谱面」，或按 Ctrl+Enter；若解析失败，先按提示修正文本。

## 看不到新谱面
检查是否忘记点击「从源码更新谱面」，或源码是否包含非法音符；应用失败时现有谱面会保持不变。

## 快捷键
F1            打开本帮助教程
Ctrl+Enter    从源码更新谱面（焦点在源码编辑器时）
Ctrl+Z        撤销图形操作（焦点在源码编辑器外时）
Ctrl+Y        重做图形操作（焦点在源码编辑器外时）

如仍无法解决，请记录软件版本、操作步骤和报错原文，便于定位问题。"""),
)


def _insert_rich_text(widget: tk.Text, content: str) -> None:
    """Render a small, safe subset of Markdown without a browser dependency."""
    inside_code = False
    for line in content.splitlines():
        if line.strip().startswith('```'):
            inside_code = not inside_code
            continue
        if inside_code:
            widget.insert('end', line + '\n', 'code')
        elif line.startswith('# '):
            widget.insert('end', line[2:] + '\n', 'h1')
        elif line.startswith('## '):
            widget.insert('end', line[3:] + '\n', 'h2')
        elif line.startswith('• '):
            widget.insert('end', '  ' + line + '\n', 'bullet')
        else:
            widget.insert('end', line + '\n', 'body')
    widget.configure(state='disabled')


class HelpDialog:
    """Reusable non-modal help window with chapters, search and example copy."""

    def __init__(self, parent: tk.Misc):
        self.window = tk.Toplevel(parent)
        self.window.title('帮助与教程 — Melody Notation')
        self.window.geometry('980x680')
        self.window.minsize(700, 480)
        self.window.transient(parent)
        self.search_text = tk.StringVar()
        self.visible_sections = list(HELP_SECTIONS)
        self.selected_title = None
        self._build()
        self._filter_sections()
        self.window.bind('<Escape>', lambda event: self.window.destroy())

    def _build(self):
        shell = ttk.Frame(self.window, padding=16)
        shell.pack(fill='both', expand=True)
        ttk.Label(shell, text='Melody Notation · 帮助与教程',
                  font=('Microsoft YaHei UI', 16, 'bold')).pack(anchor='w', pady=(0, 4))
        ttk.Label(shell, text='从第一段旋律开始，学习简谱编辑、连音、试听和文件导出。',
                  foreground='#57687a').pack(anchor='w', pady=(0, 14))
        # Pack the footer first so a large text area cannot hide its buttons.
        footer = ttk.Frame(shell)
        footer.pack(side='bottom', fill='x', pady=(12, 0))
        self.feedback = tk.StringVar(value='教程仅供阅读，不会修改当前乐谱。')
        ttk.Label(footer, textvariable=self.feedback, foreground='#57687a').pack(side='left')
        ttk.Button(footer, text='关闭', command=self.window.destroy).pack(side='right', padx=(8, 0))
        ttk.Button(footer, text='复制完整示例简谱', command=self.copy_example).pack(side='right')
        pane = ttk.PanedWindow(shell, orient='horizontal')
        pane.pack(fill='both', expand=True)
        nav = ttk.Frame(pane)
        viewer = ttk.Frame(pane)
        pane.add(nav, weight=1)
        pane.add(viewer, weight=4)

        ttk.Label(nav, text='教程目录').pack(anchor='w', pady=(0, 6))
        search = ttk.Entry(nav, textvariable=self.search_text)
        search.pack(fill='x', pady=(0, 8))
        self.search_text.trace_add('write', lambda *_: self._filter_sections())
        self.chapter_list = tk.Listbox(nav, exportselection=False,
                                       activestyle='none', borderwidth=0,
                                       highlightthickness=1, relief='flat',
                                       font=('Microsoft YaHei UI', 10),
                                       selectbackground='#dce8f4',
                                       selectforeground='#173c65')
        self.chapter_list.pack(fill='both', expand=True)
        self.chapter_list.bind('<<ListboxSelect>>', self._on_select)

        text_frame = ttk.Frame(viewer)
        text_frame.pack(fill='both', expand=True, padx=(16, 0))
        scroll = ttk.Scrollbar(text_frame, orient='vertical')
        scroll.pack(side='right', fill='y')
        self.text = tk.Text(text_frame, wrap='word', borderwidth=0,
                            font=('Microsoft YaHei UI', 10), padx=16, pady=10,
                            spacing1=2, spacing3=5,
                            background='#ffffff', foreground='#253245',
                            yscrollcommand=scroll.set)
        self.text.pack(side='left', fill='both', expand=True)
        scroll.configure(command=self.text.yview)
        self.text.tag_configure('h1', font=('Microsoft YaHei UI', 16, 'bold'),
                                foreground='#162e45', spacing1=2, spacing3=16)
        self.text.tag_configure('h2', font=('Microsoft YaHei UI', 11, 'bold'),
                                foreground='#243b52', spacing1=12, spacing3=7)
        self.text.tag_configure('body', lmargin1=4, lmargin2=4)
        self.text.tag_configure('bullet', lmargin1=12, lmargin2=30)
        self.text.tag_configure('code', font=('Consolas', 10),
                                foreground='#284a68', background='#edf3f8',
                                lmargin1=12, lmargin2=12)

    def _filter_sections(self):
        query = self.search_text.get().strip().lower()
        self.visible_sections = [section for section in HELP_SECTIONS
                                 if query in section.title.lower() or query in section.content.lower()]
        self.chapter_list.delete(0, 'end')
        for section in self.visible_sections:
            self.chapter_list.insert('end', '  ' + section.title)
        if self.visible_sections:
            current = next((i for i, section in enumerate(self.visible_sections)
                            if section.title == self.selected_title), 0)
            self.chapter_list.selection_set(current)
            self.chapter_list.activate(current)
            self._display(self.visible_sections[current])
        else:
            self.selected_title = None
            self.text.configure(state='normal')
            self.text.delete('1.0', 'end')
            self.text.insert('end', '没有找到相关教程。试试输入“时值”“连音”“6/5”或“导出”。')
            self.text.configure(state='disabled')

    def _on_select(self, event=None):
        selected = self.chapter_list.curselection()
        if selected and selected[0] < len(self.visible_sections):
            self._display(self.visible_sections[selected[0]])

    def _display(self, section: HelpSection):
        self.selected_title = section.title
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        _insert_rich_text(self.text, section.content)
        self.text.yview_moveto(0)

    def copy_example(self):
        self.window.clipboard_clear()
        self.window.clipboard_append(EXAMPLE_SCORE)
        self.window.update()
        self.feedback.set('示例已复制到剪贴板；可粘贴到「简谱源码」，再按 Ctrl+Enter。')

    def show(self):
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
