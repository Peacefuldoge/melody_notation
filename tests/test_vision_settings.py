import pytest
from melody_notation.vision import vision_settings

@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    for key in ('DEEPSEEK_API_KEY','OPENAI_API_KEY','MELODY_VISION_BASE_URL',
                'MELODY_VISION_MODEL','MELODY_VISION_API_KEY'):
        monkeypatch.delenv(key, raising=False)

def test_deepseek_selected_without_gpt(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'fake-ds-token')
    assert vision_settings() == ('fake-ds-token', 'https://api.deepseek.com', 'deepseek-flash')

def test_openai_keeps_old_default(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-openai-token')
    assert vision_settings() == ('fake-openai-token', None, 'gpt-4.1-mini')

def test_deepseek_preferred_when_both_set(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-openai-token')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'fake-ds-token')
    assert vision_settings()[1:] == ('https://api.deepseek.com', 'deepseek-flash')

def test_local_vision_endpoint(monkeypatch):
    monkeypatch.setenv('MELODY_VISION_BASE_URL', 'http://localhost:8000/v1')
    monkeypatch.setenv('MELODY_VISION_MODEL', 'local-vlm')
    assert vision_settings() == ('local', 'http://localhost:8000/v1', 'local-vlm')

def test_missing_vision_provider():
    with pytest.raises(RuntimeError,match='DEEPSEEK_API_KEY'):
        vision_settings()

def test_custom_url_requires_model(monkeypatch):
    monkeypatch.setenv('MELODY_VISION_BASE_URL', 'http://localhost:8000/v1')
    with pytest.raises(RuntimeError,match='MELODY_VISION_MODEL'):
        vision_settings()
