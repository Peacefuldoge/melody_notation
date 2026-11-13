"""Disk-backed Melody projects and independent in-memory score tabs.

Projects are folders; every *.jianpu is a normal, portable text file. A small
manifest records project identity without hiding musical data in a database.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Optional

from .core import Score, parse_text, text_from_score

MANIFEST = '.melody-project.json'


class WorkspaceError(ValueError):
    pass


@dataclass
class ScoreTab:
    score_model: Score
    path: Optional[Path] = None
    is_sample: bool = False
    label: str = '未命名'
    modified: bool = False
    selected: tuple[int, int] | None = None
    slur_anchor: tuple[int, int] | None = None
    undo_stack: list[Score] = field(default_factory=list)
    redo_stack: list[Score] = field(default_factory=list)
    source_text: str = ''
    source_dirty: bool = False
    instrument: str = 'piano'
    speed_label: str = '1.00×'
    scroll_y: float = 0.0

    @property
    def dirty(self) -> bool:
        return self.modified or self.source_dirty

    @property
    def title(self) -> str:
        return self.path.name if self.path else self.label


class ProjectWorkspace:
    def __init__(self, root: Path):
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            raise WorkspaceError(f'项目目录不存在：{root}')
        self.root = root

    @classmethod
    def create(cls, parent: Path, name: str) -> 'ProjectWorkspace':
        clean = validate_name(name)
        parent = Path(parent).expanduser().resolve()
        if not parent.is_dir():
            raise WorkspaceError('请选择已存在的父目录')
        project = parent / clean
        if project.exists():
            raise FileExistsError(f'已存在同名文件夹：{project}')
        project.mkdir()
        (project / MANIFEST).write_text(
            json.dumps({'format': 'melody-notation-project', 'version': 1, 'name': clean},
                       ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return cls(project)

    @property
    def name(self) -> str:
        manifest = self.root / MANIFEST
        if manifest.is_file():
            try:
                return str(json.loads(manifest.read_text(encoding='utf-8')).get('name') or self.root.name)
            except (ValueError, OSError, TypeError):
                pass
        return self.root.name

    def resolve(self, relative: str | Path) -> Path:
        raw = Path(relative)
        if raw.is_absolute():
            raise WorkspaceError('请使用项目内部的相对路径')
        resolved = (self.root / raw).resolve()
        if resolved == self.root or not resolved.is_relative_to(self.root):
            raise WorkspaceError('路径必须位于当前项目内部')
        return resolved

    def list_scores(self) -> list[Path]:
        return sorted((p for p in self.root.rglob('*.jianpu')
                       if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(self.root)
                       and not any(part.startswith('.') for part in p.relative_to(self.root).parts)),
                      key=lambda p: str(p.relative_to(self.root)).casefold())

    def list_assets(self) -> list[Path]:
        """All visible project documents: notation, drum patterns and arrangements."""
        return sorted((p for p in self.root.rglob('*')
                       if p.is_file() and p.suffix.lower() in ('.jianpu', '.drum', '.mtrack')
                       and not p.is_symlink() and p.resolve().is_relative_to(self.root)
                       and not any(part.startswith('.') for part in p.relative_to(self.root).parts)),
                      key=lambda p: str(p.relative_to(self.root)).casefold())

    def new_asset(self, relative: str, kind: str) -> Path:
        """Create a .drum/.mtrack safely, without overwriting existing files."""
        from .drums import default_drum_pattern
        from .arrangement import Arrangement
        if kind not in ('drum', 'mtrack'):
            raise WorkspaceError('只支持 drum 或 mtrack')
        path=self.resolve(relative)
        if path.suffix.lower() != '.'+kind:
            raise WorkspaceError(f'文件后缀必须是 .{kind}')
        validate_name(path.stem)
        if path.exists():raise FileExistsError(f'同名文件已存在：{path.name}')
        if not path.parent.is_dir():raise WorkspaceError('上级目录不存在')
        # Atomic exclusive-create protects the user's original files.
        data=(default_drum_pattern(path.stem).to_dict() if kind=='drum' else
              Arrangement(path.stem).to_dict())
        with path.open('x',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
            f.write('\n')
        return path

    def list_dirs(self) -> list[Path]:
        return sorted((p for p in self.root.rglob('*')
                       if p.is_dir() and not p.is_symlink() and p.resolve().is_relative_to(self.root)
                       and not any(part.startswith('.') for part in p.relative_to(self.root).parts)),
                      key=lambda p: str(p.relative_to(self.root)).casefold())

    def new_folder(self, relative: str) -> Path:
        p = self.resolve(relative)
        validate_name(p.name)
        if p.exists():
            raise FileExistsError(f'文件夹已存在：{p.name}')
        if not p.parent.is_dir():
            raise WorkspaceError('请先建立上级子项目')
        p.mkdir()
        return p

    def new_score(self, relative: str, text: str) -> Path:
        p = self.resolve(relative)
        if p.suffix.lower() != '.jianpu':
            raise WorkspaceError('新乐谱必须使用 .jianpu 扩展名')
        validate_name(p.stem)
        if p.exists():
            raise FileExistsError(f'乐谱已存在：{p.name}')
        if not p.parent.is_dir():
            raise WorkspaceError('请选择存在的项目或子文件夹')
        score = parse_text(text, strict=False)
        # Exclusive create avoids silent overwrites, including TOCTOU races.
        with p.open('x', encoding='utf-8') as f:
            f.write(text_from_score(score))
        return p

    def rename(self, relative: str | Path, new_name: str) -> Path:
        current = self.resolve(relative)
        if not current.exists() or current.is_symlink():
            raise WorkspaceError('找不到需要重命名的项目项')
        new_name = validate_name(new_name)
        if current.is_file():
            ext=current.suffix.lower()
            if ext not in ('.jianpu','.drum','.mtrack'):
                raise WorkspaceError('只能重命名 Melody 文档')
            if not new_name.lower().endswith(ext):
                new_name += ext
        destination = self.resolve(current.relative_to(self.root).parent / new_name)
        if destination.exists():
            raise FileExistsError('目标名称已存在')
        # Keep referenced project clips valid when a .jianpu/.drum or whole
        # subfolder is renamed. Prepare changes BEFORE moving anything.
        updates=[]
        if current.is_dir() or current.suffix.lower() in ('.jianpu','.drum'):
            from .arrangement import Arrangement
            for arr_file in self.root.rglob('*.mtrack'):
                if arr_file.is_symlink() or not arr_file.is_file():continue
                arr=Arrangement.load(arr_file)
                touched=False
                for track in arr.tracks:
                    for clip in track.clips:
                        source=(self.root/clip.source).resolve()
                        if source==current or (current.is_dir() and source.is_relative_to(current)):
                            replaced=(destination/source.relative_to(current) if current.is_dir() else destination)
                            clip.source=replaced.relative_to(self.root).as_posix()
                            touched=True
                if touched:
                    new_arr_file=(destination/arr_file.relative_to(current) if
                                  current.is_dir() and arr_file.is_relative_to(current) else arr_file)
                    updates.append((new_arr_file,arr))
        current.rename(destination)
        for arr_file,arr in updates:
            arr.save(arr_file)
        return destination


def validate_name(name: str) -> str:
    name = name.strip()
    if (not name or name in ('.', '..') or len(name) > 120
        or any(c in name for c in '/\\:*?"<>|') or name.endswith(('.', ' '))):
        raise WorkspaceError('名称不能留空，也不能包含 Windows 文件名禁用字符')
    return name


# A list of entry points only. No score contents or editor drafts are written here.
def recent_projects_file() -> Path:
    override = os.environ.get('MELODY_RECENT_PROJECTS_FILE')
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get('APPDATA') or (Path.home() / '.config'))
    return base / 'MelodyNotation' / 'recent-projects.json'


def load_recent_projects(limit: int = 12) -> list[Path]:
    try:
        content = json.loads(recent_projects_file().read_text(encoding='utf-8'))
        if not isinstance(content, list):
            return []
    except (OSError, ValueError, TypeError):
        return []
    seen: set[Path] = set()
    result = []
    for raw in content:
        if not isinstance(raw, str):
            continue
        path = Path(raw).expanduser().resolve()
        if path.is_dir() and path not in seen:
            seen.add(path)
            result.append(path)
        if len(result) >= limit:
            break
    return result


def remember_project(path: Path, limit: int = 12) -> list[Path]:
    path = Path(path).expanduser().resolve()
    items = [path] + [p for p in load_recent_projects(limit) if p != path]
    items = items[:limit]
    target = recent_projects_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps([str(p) for p in items], ensure_ascii=False, indent=2),
                      encoding='utf-8')
    return items
