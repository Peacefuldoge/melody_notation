from pathlib import Path
import json
import pytest
from melody_notation.workspace import ProjectWorkspace, WorkspaceError, ScoreTab
from melody_notation.core import parse_text

SCORE='title: 第一个\nkey: C\ntime: 4/4\nbpm: 120\nnotes:\n| 1 2 3 4 |'


def test_create_project_and_nested_scores(tmp_path):
    project=ProjectWorkspace.create(tmp_path,'歌曲合集')
    assert project.name=='歌曲合集'
    assert json.loads((project.root/'.melody-project.json').read_text(encoding='utf-8'))['version']==1
    sub=project.new_folder('主线音乐')
    a=project.new_score('a.jianpu',SCORE)
    b=project.new_score('主线音乐/b.jianpu',SCORE)
    assert project.list_dirs()==[sub]
    assert project.list_scores()==[a,b]
    assert parse_text(b.read_text(encoding='utf-8')).title=='第一个'
    assert ProjectWorkspace(project.root).list_scores()==[a,b]


def test_no_accidental_overwrite_and_name_validation(tmp_path):
    project=ProjectWorkspace.create(tmp_path,'test')
    project.new_score('a.jianpu',SCORE)
    with pytest.raises(FileExistsError):project.new_score('a.jianpu',SCORE)
    with pytest.raises(WorkspaceError):project.new_score('../escaping.jianpu',SCORE)
    with pytest.raises(WorkspaceError):project.new_folder('..\\outside')
    with pytest.raises(WorkspaceError):project.new_score('invalid.txt',SCORE)
    with pytest.raises(WorkspaceError):ProjectWorkspace.create(tmp_path,'bad:name')


def test_project_rename_preserves_other_scores(tmp_path):
    project=ProjectWorkspace.create(tmp_path,'test')
    project.new_folder('part1')
    a=project.new_score('part1/intro.jianpu',SCORE)
    project.new_score('other.jianpu',SCORE)
    renamed=project.rename('part1','first movement')
    assert (renamed/'intro.jianpu').exists()
    assert not a.exists()
    assert (project.root/'other.jianpu').exists()
    assert project.rename('other.jianpu','last').suffix=='.jianpu'


def test_tab_supports_independent_draft_and_history():
    a=ScoreTab(score_model=parse_text(SCORE),label='A')
    b=ScoreTab(score_model=parse_text(SCORE),label='B')
    a.source_text='unfinished'; a.source_dirty=True
    assert a.dirty and not b.dirty
    a.undo_stack.append(a.score_model)
    assert len(a.undo_stack)==1 and b.undo_stack==[]
