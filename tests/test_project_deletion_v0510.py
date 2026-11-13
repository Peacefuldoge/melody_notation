"""Project-tree deletion must be guarded and keep the existing version number."""
import json
from pathlib import Path

import pytest

from melody_notation import workspace
from melody_notation.workspace import ProjectWorkspace, WorkspaceError


SCORE = 'title: T\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |\n'


@pytest.fixture
def trash(monkeypatch, tmp_path):
    moved = []
    bin_dir = tmp_path / '_mock_trash'
    bin_dir.mkdir()

    def fake_trash(path):
        src = Path(path)
        dst = bin_dir / f'{len(moved)}_{src.name}'
        src.rename(dst)
        moved.append((src, dst))

    monkeypatch.setattr(workspace, 'send2trash', fake_trash)
    return moved


def test_delete_score_moves_only_selected_file(tmp_path, trash):
    project = ProjectWorkspace.create(tmp_path, 'project')
    a = project.new_score('one.jianpu', SCORE)
    b = project.new_score('two.jianpu', SCORE)
    deleted = project.delete('one.jianpu')
    assert deleted == a
    assert not a.exists() and b.exists() and project.root.exists()
    assert trash[0][1].read_text(encoding='utf8').startswith('title: T')


def test_delete_nested_folder_includes_contents(tmp_path, trash):
    project = ProjectWorkspace.create(tmp_path, 'project')
    folder = project.new_folder('movement')
    project.new_score('movement/lead.jianpu', SCORE)
    kept = project.new_score('other.jianpu', SCORE)
    assert project.delete('movement') == folder
    assert not folder.exists() and (trash[0][1]/'lead.jianpu').exists()
    assert kept.exists()


def test_delete_blocks_external_paths_root_and_symlinks(tmp_path, trash):
    project = ProjectWorkspace.create(tmp_path, 'project')
    outside = tmp_path / 'outside.jianpu'
    outside.write_text(SCORE, encoding='utf8')
    project.new_score('score.jianpu', SCORE)
    for relative in ('.', '..', '../outside.jianpu', '/tmp/outside.jianpu', '.melody-project.json'):
        with pytest.raises(WorkspaceError):
            project.delete(relative)
    link = project.root / 'alias.jianpu'
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pass
    else:
        with pytest.raises(WorkspaceError):
            project.delete('alias.jianpu')
        assert link.is_symlink()
    assert outside.is_file() and not trash


def test_entire_project_deletion_requires_valid_manifest(tmp_path, monkeypatch, trash):
    ordinary = tmp_path / 'ordinary'
    ordinary.mkdir()
    with pytest.raises(WorkspaceError):
        ProjectWorkspace(ordinary).delete_project()
    assert ordinary.exists()

    project = ProjectWorkspace.create(tmp_path, 'project')
    project.new_score('x.jianpu', SCORE)
    monkeypatch.setenv('MELODY_RECENT_PROJECTS_FILE', str(tmp_path/'recents.json'))
    workspace.remember_project(project.root)
    deleted = project.delete_project()
    assert deleted == project.root
    assert not project.root.exists()
    assert (trash[0][1]/'x.jianpu').exists()
    assert workspace.load_recent_projects() == []
    assert json.loads((tmp_path/'recents.json').read_text(encoding='utf8')) == []


def test_invalid_manifest_and_trash_failure_preserve_files(tmp_path, trash, monkeypatch):
    project = ProjectWorkspace.create(tmp_path, 'project')
    (project.root/workspace.MANIFEST).write_text('{}', encoding='utf8')
    with pytest.raises(WorkspaceError):
        project.delete_project()
    assert project.root.exists()

    file = project.new_score('keep.jianpu', SCORE)
    def unavailable(_):
        raise OSError('Recycle Bin unavailable')
    monkeypatch.setattr(workspace, 'send2trash', unavailable)
    with pytest.raises(OSError):
        project.delete('keep.jianpu')
    assert file.is_file()
