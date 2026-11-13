"""Pure layout sizing helpers used by the Qt workstation.

The navigation rail remains fixed-width when its project sidebar is hidden;
the space is returned to the editor without changing inspector visibility.
"""
from __future__ import annotations


def navigation_split_sizes(sizes: list[int] | tuple[int, ...], navigation_width: int) -> list[int]:
    """Redistribute only the navigation/editor split, preserving inspector size.

    Qt's splitter still owns the exact number of pixels allocated to handles;
    passing a proportionally consistent setSizes() request avoids the blank
    navigation panel left by QWidget.hide() on its own.
    """
    if len(sizes) != 3:
        raise ValueError('Expected navigation, editor, inspector split sizes')
    nav, editor, inspector = (max(0, int(v)) for v in sizes)
    target = max(1, int(navigation_width))
    available = max(1, nav + editor)
    new_nav = min(target, max(1, available - 1))
    return [new_nav, available - new_nav, inspector]


def navigation_width_limits(rail_width: int, sidebar_min: int, sidebar_max: int) -> tuple[int, int]:
    """Bound the entire splitter pane by the width its visible children can fill.

    A sidebar with a maximum width smaller than the splitter allocation leaves
    an empty strip beside the tree when users drag the navigation separator.
    """
    rail = max(1, int(rail_width))
    low = max(1, int(sidebar_min))
    high = max(low, int(sidebar_max))
    return rail + low, rail + high
