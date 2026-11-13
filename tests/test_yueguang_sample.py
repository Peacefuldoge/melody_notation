from importlib import resources

from melody_notation.core import parse_text
from melody_notation.audio import synthesize


def test_bundled_yueguang_sample_parses_and_synthesizes():
    text = resources.files('melody_notation').joinpath('samples/yueguang.jianpu').read_text(encoding='utf-8')
    score = parse_text(text, strict=True)
    assert score.title.startswith('月光')
    assert score.numerator == 2 and score.denominator == 4
    arr = synthesize(score, instrument='piano')
    assert len(arr) > 1000
    assert float(abs(arr).max()) > 0.001
