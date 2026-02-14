import pytest
from tdom import html

def test_svg_case_sensitivity():
    # SVG attributes like viewBox are case-sensitive
    node = html(t'<svg viewBox="0 0 100 100"></svg>')
    # We expect viewBox, not viewbox
    assert 'viewBox' in str(node)

def test_svg_tag_case_sensitivity():
    # SVG tags like linearGradient are case-sensitive
    node = html(t'<svg><linearGradient></linearGradient></svg>')
    assert 'linearGradient' in str(node)

def test_svg_tag_case_sensitivity_outside_svg():
    # Outside SVG, tags should be lowercased
    node = html(t'<linearGradient></linearGradient>')
    assert 'lineargradient' in str(node)

def test_svg_attr_case_sensitivity_outside_svg():
    # Outside SVG, attributes should be lowercased
    node = html(t'<div viewBox="0 0 100 100"></div>')
    assert 'viewbox' in str(node)
