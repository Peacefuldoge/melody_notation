from pathlib import Path
import json

from melody_notation.workspace import load_recent_projects, remember_project


def test_recent_project_history_persists_order_and_deduplicates(tmp_path, monkeypatch):
    index = tmp_path / 'prefs' / 'projects.json'
    monkeypatch.setenv('MELODY_RECENT_PROJECTS_FILE', str(index))
    a, b = tmp_path / 'A', tmp_path / 'B'
    a.mkdir(); b.mkdir()
    assert load_recent_projects() == []
    assert remember_project(a) == [a.resolve()]
    assert remember_project(b) == [b.resolve(), a.resolve()]
    assert remember_project(a) == [a.resolve(), b.resolve()]
    assert json.loads(index.read_text(encoding='utf-8')) == [str(a.resolve()), str(b.resolve())]


def test_recent_history_tolerates_corruption_or_deleted_projects(tmp_path, monkeypatch):
    index = tmp_path / 'broken.json'
    monkeypatch.setenv('MELODY_RECENT_PROJECTS_FILE', str(index))
    index.write_text('not-json', encoding='utf-8')
    assert load_recent_projects() == []
    path = tmp_path / 'gone'
    index.write_text(json.dumps([str(path), 23, str(tmp_path)]), encoding='utf-8')
    assert load_recent_projects() == [tmp_path.resolve()]
