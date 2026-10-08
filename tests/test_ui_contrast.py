"""
Tests verifying UI accessibility, color contrast ratios, and design token compliance
according to WCAG 2.2 AA (4.5:1 normal text, 3.0:1 large/controls) and AAA standards.
"""

import re
import pytest


def srgb_channel(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return 0.2126 * srgb_channel(r) + 0.7152 * srgb_channel(g) + 0.0722 * srgb_channel(b)


def contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = relative_luminance(hex1)
    l2 = relative_luminance(hex2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def extract_ui_tokens():
    with open("ui.py", "r", encoding="utf-8") as f:
        content = f.read()
    tokens = {}
    lines = content.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("COLOR_") and "=" in line:
            var_part, val_part = line.split("=", 1)
            var_name = var_part.strip()
            # remove inline comments
            val_part = val_part.split("#")[0].strip() if not val_part.strip().startswith('"#') and not val_part.strip().startswith("'#") else val_part.strip().split()[0]
            val_part = val_part.strip().strip("'\"")
            if val_part.startswith("#"):
                tokens[var_name] = val_part
            elif val_part in tokens:
                tokens[var_name] = tokens[val_part]
    return tokens


@pytest.fixture(scope="module")
def tokens():
    toks = extract_ui_tokens()
    assert len(toks) >= 15, f"Expected at least 15 color tokens in ui.py, got {len(toks)}"
    return toks


def test_primary_text_contrast_against_surfaces(tokens):
    ratio_page = contrast_ratio(tokens["COLOR_TEXT_PRIMARY"], tokens["COLOR_PAGE_BG"])
    ratio_surface = contrast_ratio(tokens["COLOR_TEXT_PRIMARY"], tokens["COLOR_BG_SURFACE"])
    assert ratio_page >= 7.0, f"Primary text on page bg ({ratio_page:.2f}:1) must achieve AAA (>=7.0)"
    assert ratio_surface >= 7.0, f"Primary text on card surface ({ratio_surface:.2f}:1) must achieve AAA (>=7.0)"


def test_secondary_text_contrast(tokens):
    ratio_page = contrast_ratio(tokens["COLOR_TEXT_SECONDARY"], tokens["COLOR_PAGE_BG"])
    ratio_surface = contrast_ratio(tokens["COLOR_TEXT_SECONDARY"], tokens["COLOR_BG_SURFACE"])
    assert ratio_page >= 7.0, f"Secondary text on page bg ({ratio_page:.2f}:1) must meet or exceed 7.0:1"
    assert ratio_surface >= 7.0, f"Secondary text on surface ({ratio_surface:.2f}:1) must meet or exceed 7.0:1"


def test_muted_text_contrast(tokens):
    ratio_page = contrast_ratio(tokens["COLOR_TEXT_MUTED"], tokens["COLOR_PAGE_BG"])
    ratio_surface = contrast_ratio(tokens["COLOR_TEXT_MUTED"], tokens["COLOR_BG_SURFACE"])
    assert ratio_page >= 4.5, f"Muted text on page bg ({ratio_page:.2f}:1) must meet WCAG AA (>=4.5:1)"
    assert ratio_surface >= 4.5, f"Muted text on surface ({ratio_surface:.2f}:1) must meet WCAG AA (>=4.5:1)"


def test_status_badge_combinations(tokens):
    good_badge = contrast_ratio(tokens["COLOR_STATUS_GOOD_TEXT"], tokens["COLOR_STATUS_GOOD_BG"])
    mod_badge = contrast_ratio(tokens["COLOR_STATUS_MOD_TEXT"], tokens["COLOR_STATUS_MOD_BG"])
    low_badge = contrast_ratio(tokens["COLOR_STATUS_LOW_TEXT"], tokens["COLOR_STATUS_LOW_BG"])
    assert good_badge >= 4.5, f"Good status badge text/bg ({good_badge:.2f}:1) must meet WCAG AA (>=4.5:1)"
    assert mod_badge >= 4.5, f"Moderate status badge text/bg ({mod_badge:.2f}:1) must meet WCAG AA (>=4.5:1)"
    assert low_badge >= 4.5, f"Low status badge text/bg ({low_badge:.2f}:1) must meet WCAG AA (>=4.5:1)"


def test_status_text_on_white(tokens):
    good_white = contrast_ratio(tokens["COLOR_STATUS_GOOD_TEXT"], "#FFFFFF")
    mod_white = contrast_ratio(tokens["COLOR_STATUS_MOD_TEXT"], "#FFFFFF")
    low_white = contrast_ratio(tokens["COLOR_STATUS_LOW_TEXT"], "#FFFFFF")
    assert good_white >= 7.0, f"Good text on white ({good_white:.2f}:1) should achieve AAA (>=7.0:1)"
    assert mod_white >= 7.0, f"Moderate text on white ({mod_white:.2f}:1) should achieve AAA (>=7.0:1)"
    assert low_white >= 7.0, f"Low text on white ({low_white:.2f}:1) should achieve AAA (>=7.0:1)"


def test_interactive_elements(tokens):
    button_text = contrast_ratio(tokens["COLOR_TEXT_INVERSE"], tokens["COLOR_PRIMARY"])
    border_ctrl = contrast_ratio(tokens["COLOR_BORDER_STRONG"], "#FFFFFF")
    assert button_text >= 4.5, f"Primary button text/bg ({button_text:.2f}:1) must meet WCAG AA (>=4.5:1)"
    assert border_ctrl >= 3.0, f"Interactive control border against surface ({border_ctrl:.2f}:1) must meet WCAG non-text contrast (>=3.0:1)"
