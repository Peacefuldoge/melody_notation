"""Theme token regression coverage for ChatGPT-style navigation layout."""
from melody_notation.ui_theme import PALETTES
from melody_notation.workspace_gui import WorkspaceMixin

def test_sidebar_palette_is_derived_from_original_workstation_theme():
    for theme in ('light', 'dark'):
        p=PALETTES[theme]
        colors=WorkspaceMixin._nav_colors(p)
        assert colors['BG']==p['surface']
        assert colors['RAIL']==p['window']
        assert colors['HOVER']==p['hover']
        assert colors['SELECT']==p['accent_faint']
        assert colors['TEXT']==p['text']
        assert colors['MUTED']==p['secondary']
        assert colors['SEARCH']==p['raised']

def test_sidebar_themes_have_different_contrast_and_no_fixed_black_skin():
    light=WorkspaceMixin._nav_colors(PALETTES['light'])
    dark=WorkspaceMixin._nav_colors(PALETTES['dark'])
    assert light != dark
    assert light['TEXT'] != dark['TEXT']
    assert light['BG'] != dark['BG']
    assert light['SELECT'] != dark['SELECT']
