"""Opt-in vision-assisted numbered-score transcription; requires review."""
from __future__ import annotations
from pathlib import Path
import base64
import json
import mimetypes
import os
import re
from .core import parse_text, Score

PROMPT = """You are transcribing a Chinese numbered notation (简谱) image into an EDITABLE plain-text score.
Read every visible bar line and note, high-octave dots, low-octave dots, underlines, dotted durations, rests.
Return ONLY a JSON object with EXACT keys: title, key, time, bpm, bars, uncertainty.
- title: visible title or 未命名
- key: tonic for scale degree 1 e.g. C, D, Bb
- time: time signature e.g. 4/4
- bpm: integer, use 120 if unreadable
- bars: list of strings, EACH string is one measure's whitespace-delimited note tokens; preserve order
- uncertainty: short text describing ambiguous or untranscribed notation
TOKEN GRAMMAR:
1..7 = scale degrees in octave 4, 0 = one-beat rest, 1' = high 1, 5, = low 5.
1/2 = eighth note, 1/4 = sixteenth, 1. = dotted quarter, 1./2 = dotted eighth.
'-' is one added beat to previous note, and R is a full-measure rest.
Examples for 4/4: "1 2 3 4"; "5/2 6/2 7 1' 0"; "1' - - -"; "R".
For a visual dot ABOVE a note use apostrophe. For a dot FOLLOWING the note use a period.
For beams/underlines: single underline means /2; double underline means /4.
For slur arcs between notes, optionally encode with separate standalone ( and ) tokens; if uncertain, describe it in uncertainty.
Do NOT invent notes or pad missing bars. If unclear, report in uncertainty.
Bar duration must match meter if fully transcribed; count/check beats before returning.
"""

def vision_settings() -> tuple[str, str | None, str]:
    """Select a vision provider without tying transcription to Codex or ChatGPT.

    Priority: explicit compatible endpoint > DeepSeek API key > OpenAI API key.
    Returns (api_key, base_url, default_model). Never logs keys.
    """
    base = os.environ.get('MELODY_VISION_BASE_URL')
    requested_model = os.environ.get('MELODY_VISION_MODEL')
    custom_key = os.environ.get('MELODY_VISION_API_KEY')
    if base:
        # For a local OpenAI-compatible server a dummy key is usually sufficient.
        key = custom_key or os.environ.get('DEEPSEEK_API_KEY') or os.environ.get('OPENAI_API_KEY') or 'local'
        if not requested_model and 'api.deepseek.com' not in base:
            raise RuntimeError('Set MELODY_VISION_MODEL for a custom vision endpoint')
        return key, base, requested_model or 'deepseek-flash'
    if os.environ.get('DEEPSEEK_API_KEY'):
        return os.environ['DEEPSEEK_API_KEY'], 'https://api.deepseek.com', requested_model or 'deepseek-flash'
    if os.environ.get('OPENAI_API_KEY'):
        return os.environ['OPENAI_API_KEY'], None, requested_model or 'gpt-4.1-mini'
    raise RuntimeError('Set DEEPSEEK_API_KEY, OPENAI_API_KEY or MELODY_VISION_BASE_URL')


def transcribe_image(image_path: str | Path, *, model: str | None = None) -> tuple[Score, str]:
    """Uses a configurable vision-capable Chat Completions endpoint, not offline OCR.

    Env: DEEPSEEK_API_KEY (default DeepSeek Flash), or OPENAI_API_KEY.
    Can override with MELODY_VISION_BASE_URL, MELODY_VISION_API_KEY,
    and MELODY_VISION_MODEL for other vision-capable providers.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError('Install optional dependency: pip install -e ".[vision]"') from exc
    img = Path(image_path)
    if not img.is_file(): raise FileNotFoundError(img)
    mime = mimetypes.guess_type(img.name)[0]
    if mime not in ('image/png','image/jpeg','image/webp','image/gif'):
        raise ValueError('Use a PNG, JPEG or WEBP image')
    raw = img.read_bytes()
    if len(raw) > 20_000_000: raise ValueError('Image is too large (>20 MB)')
    api_key, base_url, default_model = vision_settings()
    client = OpenAI(api_key=api_key, base_url=base_url)
    chosen = model or default_model
    uri = f'data:{mime};base64,{base64.b64encode(raw).decode("ascii")}'
    completion = client.chat.completions.create(
        model=chosen,
        messages=[{'role':'user','content':[
            {'type':'text','text':PROMPT},
            {'type':'image_url','image_url':{'url':uri,'detail':'high'}}
        ]}], temperature=0)
    response = completion.choices[0].message.content or ''
    # Some compatible endpoints place JSON inside a code fence.
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '',response.strip(),flags=re.I)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError('Vision model did not return valid JSON. Try another vision-capable model.') from exc
    bars = payload.get('bars')
    if not isinstance(bars,list) or not bars or not all(isinstance(b,str) for b in bars):
        raise ValueError('Vision output must include a nonempty bars string list')
    text = (f"title: {payload.get('title','未命名')}\nkey: {payload.get('key','C')}\n"
            f"time: {payload.get('time','4/4')}\nbpm: {payload.get('bpm',120)}\n"
            f"notes:\n| " + ' | '.join(bars) + ' |\n')
    score = parse_text(text, strict=False)
    # Even a rhythm-invalid OCR result must remain editable: do not drop the draft.
    problems = score.validate(strict=False)
    notes = str(payload.get('uncertainty','')).strip()
    if problems:
        notes += ('; ' if notes else '') + '节拍待校对：' + '; '.join(problems)
    return score, notes
