# Melody Notation v0.3.0 — 多音轨与鼓点文件

## 文件格式

| 后缀 | 描述 | 编辑方式 |
|---|---|---|
| `.jianpu` | 原有的单旋律简谱 | 中央标签 / 源码 |
| `.drum` | JSON 格式 4/4 鼓点网格 | PySide6 文档标签中的 16 步音序器 |
| `.mtrack` | JSON 格式多轨编排 | PySide6 文档标签中的多轨时间线 |

`.drum` 和 `.mtrack` 都是 UTF-8 文本，可以交给 Codex / DeepSeek Harness 修改。工程中的 `.melody-project.json` 记录项目标识，其余文件可独立移动和备份（若移动 `.mtrack`，请连同其引用的素材一起移动）。

## 新建与编辑

1. 创建/打开 Melody 项目文件夹。
2. 在项目文件树中选中项目或子文件夹，点击 **新建音乐文件** 并选择鼓点或多轨工程。
3. 双击 `.drum`，在 16 步网格中点击格子开启/关闭底鼓 Kick、军鼓 Snare、闭合踩镲 Hi-hat；可切换鼓组、BPM 和小节数。
4. 双击 `.mtrack`，点击 **加入乐谱 / 鼓点**，从项目内选择现有 `.jianpu` 或 `.drum`。每加入一个文件默认新增一条音轨；选中已有轨道时可**追加片段**。
5. 在时间线或音轨树中选择片段；右侧填写：
   - `起点`：片段出现在工程第几拍（从 0 开始）
   - `裁剪起点/终点`：源乐谱中的拍范围（终点留空为全部）
   - `反转`：音符/鼓击的**演奏事件时间顺序**倒置，**并非倒放录制音频波形**
   - `音量`：0–2 倍
   - `旋律轨音色`：piano / flute / gameboy 等原有预设
6. 轨道上移/下移改变显示排列顺序；静音/Mute 和 Solo 控制哪些轨道发声。可前移/后移 4 拍、删除片段或删除整个轨道。所有这些操作都**不改变源 `.jianpu` 和 `.drum` 文件**。
7. 保存 `.mtrack` 后可直接试听混音，导出 **MIDI / WAV / MP3**（MP3 需系统有 FFmpeg）。

> 在项目树中打开 `.mtrack` 或 `.drum` 时，编辑器会显示在中央文档标签中。

## 鼓音源

| 预置鼓组 | 内置 WAV/MP3 声音特征 |
|---|---|
| acoustic | 短促的原声底鼓、噪声军鼓和闭合踩镲 |
| electronic | 衰减音高更突出的电子底鼓、合成军鼓/踩镲 |
| gameboy | 量化脉冲及噪声构成的复古 8-bit 鼓声 |

三套鼓组**均提供 Kick / Snare / Hi-hat 三个可编辑鼓声**。这是自合成的近似音色，不是盗用商用鼓采样或真实任天堂硬件 APU 复刻。

MIDI 依照 GM 规范：36 Bass Drum、38 Snare、42 Closed Hi-Hat，记入打击乐专用**通道 10**（代码中的 0 基索引为 9）。[General MIDI Percussion Key Map](https://www.cs.cmu.edu/~music/cmp/archives/cmsip/readings/GMSpecs_PercMap.htm)。各鼓组的特色波形不会写入标准 MIDI，因此别的 DAW 需要选定对应的 drum kit 才能听到接近的效果。

## 编排的时间与裁剪语义

- 项目 BPM 决定混音时间轴的秒数。来自不同 BPM 的 `.jianpu` 素材按照**拍对齐**，不继承原音频的秒数；不提供带音高保护的独立 time-stretch 算法。
- `trim_start` / `trim_end` 是**源文件的拍位置**，不会改变原始文件。片段不能裁剪超过源乐谱/鼓点时长。
- 片段可以重叠混音；撤回剪辑不会影响其源乐谱。
- `reversed` 仅倒转音符/鼓击事件的时间位置（包括音符长度、休止间隔），不做真正声音波形倒放；乐句连音线属于视觉记号。
- 当前只支持 4/4 的鼓点网格（每小节 16 步），但 `.jianpu` 本身仍支持原有拍号。
- 最长混音输出限制为 10 分钟，防止意外分配过大的音频缓冲。

## 文本数据结构

`.drum`：

```json
{
  "format": "melody-drum", "version": 1,
  "title": "鼓点", "bpm": 120, "bars": 2,
  "kit": "acoustic",
  "hits": {"kick": [0, 8, 16, 24], "snare": [4, 12, 20, 28], "hihat": [0, 2, 4, 6]}
}
```

`.mtrack`：

```json
{
  "format": "melody-mtrack", "version": 1, "title": "主题曲", "bpm": 120,
  "tracks": [{
    "name": "主旋律", "kind": "melody", "instrument": "flute",
    "muted": false, "solo": false,
    "clips": [{
      "source": "主旋律.jianpu", "start_beat": 0, "trim_start": 0,
      "trim_end": null, "reversed": false, "gain": 1.0
    }]
  }]
}
```

引用 `source` 的相对路径以项目根目录（包含 `.melody-project.json`）为基准。文件不能引用项目外部路径；对外部文件需要先拷贝到当前项目。保存时不会往源 `.jianpu` 中写入裁剪信息。

## CLI 与 Agent

```powershell
conda activate melody
cd D:\Work\melody-notation-v0.3.0
python -m pip install -e ".[all,test]"
python -m melody_notation.cli gui

# 文件格式校验
python -m melody_notation.cli validate "demo_projects/我的第一份工程/主题编排.mtrack"
python -m melody_notation.cli validate "demo_projects/我的第一份工程/节奏/原声鼓.drum"
# 多轨合成
python -m melody_notation.cli export "demo_projects/我的第一份工程/主题编排.mtrack" -o output/demo_mix.wav
python -m melody_notation.cli export "demo_projects/我的第一份工程/主题编排.mtrack" -o output/demo_mix.mid
```

Codex 用项目 Skill `.agents/skills/melody-notation/SKILL.md`。DeepSeek Harness 使用同一个 MCP Server，并通过 `create_arrangement`、`add_arrangement_clip`、`edit_arrangement_clip`、`reorder_arrangement_track`、`inspect_arrangement`、`export_multitrack_midi`、`export_multitrack_audio`、`create_drum_pattern`、`toggle_drum_hit`、`inspect_drum_pattern`、`export_drum_pattern` 等工具访问新文件。

**安全原则：** 修改已存在文件必须先获得用户批准，并传递 `overwrite=true`；用户在 GUI 里尚未保存的编辑不会自动同步到 MCP。

**从项目外导入：** 在多轨编辑器选择外部 `.jianpu` 或 `.drum` 时，程序会询问是否复制到当前工程的 `导入素材/` 文件夹；确认后复制一个新文件供编排引用，**不会修改或移动原件**。如果源文件有节拍/格式问题，会在加入音轨前提示。
