from markupsafe import Markup

import pytest

from tdom import Conditions, cond, html
from tdom.nodes import Fragment, Text


# ---------------------------------------------------------------------------
# Conditions — basic matching
# ---------------------------------------------------------------------------


def test_when_first_truthy_wins():
    result = Conditions().when(True, "a").when(True, "b").default("c").__html__()
    assert result == Markup("a")


def test_when_skips_falsy():
    result = Conditions().when(False, "a").when(True, "b").default("c").__html__()
    assert result == Markup("b")


def test_when_uses_default_when_no_match():
    result = Conditions().when(False, "a").when(False, "b").default("default").__html__()
    assert result == Markup("default")


def test_when_empty_when_no_match_and_no_default():
    result = Conditions().when(False, "a").__html__()
    assert result == Markup("")


def test_when_no_cases_no_default():
    result = Conditions().__html__()
    assert result == Markup("")


# ---------------------------------------------------------------------------
# When — lazy callables
# ---------------------------------------------------------------------------


def test_when_lazy_value_called_on_match():
    called = []

    def factory():
        called.append(True)
        return "lazy"

    Conditions().when(True, factory).__html__()
    assert called == [True]


def test_when_lazy_value_not_called_when_not_matched():
    called = []

    def factory():
        called.append(True)
        return "lazy"

    Conditions().when(False, factory).default("other").__html__()
    assert called == []


def test_when_lazy_default_called_when_no_match():
    called = []

    def factory():
        called.append(True)
        return "default"

    Conditions().when(False, "a").default(factory).__html__()
    assert called == [True]


def test_when_lazy_default_not_called_when_matched():
    called = []

    def factory():
        called.append(True)
        return "default"

    Conditions().when(True, "a").default(factory).__html__()
    assert called == []


# ---------------------------------------------------------------------------
# When — __html__ markup output
# ---------------------------------------------------------------------------


def test_when_wraps_plain_string_with_escape():
    result = Conditions().when(True, "<b>bold</b>").__html__()
    assert result == Markup("&lt;b&gt;bold&lt;/b&gt;")


def test_when_passes_through_markup():
    markup = Markup("<b>safe</b>")
    result = Conditions().when(True, markup).__html__()
    assert result == Markup("<b>safe</b>")


def test_when_uses_html_dunder_on_value():
    node = html(t"<span>hi</span>")
    result = Conditions().when(True, node).__html__()
    assert result == Markup("<span>hi</span>")


def test_when_default_plain_string_escaped():
    result = Conditions().when(False, "ok").default("<xss>").__html__()
    assert result == Markup("&lt;xss&gt;")


# ---------------------------------------------------------------------------
# When — tdom integration
# ---------------------------------------------------------------------------


def test_when_composable_in_tstring():
    is_admin = True
    node = html(t"<div>{Conditions().when(is_admin, html(t'<span>ADMIN</span>')).default(html(t'<span>USER</span>'))}</div>")
    assert str(node) == "<div><span>ADMIN</span></div>"


def test_when_default_branch_in_tstring():
    is_admin = False
    node = html(t"<div>{Conditions().when(is_admin, html(t'<span>ADMIN</span>')).default(html(t'<span>USER</span>'))}</div>")
    assert str(node) == "<div><span>USER</span></div>"


def test_when_no_match_renders_empty_in_tstring():
    node = html(t"<div>{Conditions().when(False, html(t'<span>x</span>'))}</div>")
    assert str(node) == "<div></div>"


def test_when_multi_branch_in_tstring():
    def badge(is_admin: bool, is_premium: bool) -> str:
        return str(
            html(
                t"<div>{
                    Conditions()
                    .when(is_admin,   html(t'<span class="admin">ADMIN</span>'))
                    .when(is_premium, html(t'<span class="pro">PRO</span>'))
                    .default(         html(t'<span>FREE</span>'))
                }</div>"
            )
        )

    assert badge(True, False) == '<div><span class="admin">ADMIN</span></div>'
    assert badge(False, True) == '<div><span class="pro">PRO</span></div>'
    assert badge(False, False) == "<div><span>FREE</span></div>"


def test_when_lazy_in_tstring():
    is_admin = True
    node = html(
        t"<div>{
            Conditions()
            .when(is_admin, lambda: html(t'<span>ADMIN</span>'))
            .default(lambda: html(t'<span>FREE</span>'))
        }</div>"
    )
    assert str(node) == "<div><span>ADMIN</span></div>"


# ---------------------------------------------------------------------------
# cond — basic
# ---------------------------------------------------------------------------


def test_cond_first_truthy_wins():
    result = cond((True, "a"), (True, "b"), default="c")
    assert result == "a"


def test_cond_skips_falsy():
    result = cond((False, "a"), (True, "b"), default="c")
    assert result == "b"


def test_cond_uses_default():
    result = cond((False, "a"), (False, "b"), default="default")
    assert result == "default"


def test_cond_returns_none_when_no_match_and_no_default():
    result = cond((False, "a"), (False, "b"))
    assert result is None


def test_cond_empty_pairs_no_default():
    result = cond()
    assert result is None


def test_cond_empty_pairs_with_default():
    result = cond(default="fallback")
    assert result == "fallback"


# ---------------------------------------------------------------------------
# cond — lazy callables
# ---------------------------------------------------------------------------


def test_cond_lazy_value_called_on_match():
    called = []

    def factory():
        called.append(True)
        return "lazy"

    cond((True, factory))
    assert called == [True]


def test_cond_lazy_value_not_called_when_not_matched():
    called = []

    def factory():
        called.append(True)
        return "lazy"

    cond((False, factory), default="other")
    assert called == []


def test_cond_lazy_default_called_when_no_match():
    called = []

    def factory():
        called.append(True)
        return "default"

    cond((False, "a"), default=factory)
    assert called == [True]


def test_cond_lazy_default_not_called_when_matched():
    called = []

    def factory():
        called.append(True)
        return "default"

    cond((True, "a"), default=factory)
    assert called == []


# ---------------------------------------------------------------------------
# cond — tdom integration
# ---------------------------------------------------------------------------


def test_cond_composable_in_tstring():
    is_admin = True
    node = html(t"<div>{cond(
        (is_admin, html(t'<span>ADMIN</span>')),
        default=html(t'<span>USER</span>'),
    )}</div>")
    assert str(node) == "<div><span>ADMIN</span></div>"


def test_cond_none_renders_empty_in_tstring():
    node = html(t"<div>{cond((False, html(t'<span>x</span>')))}</div>")
    assert str(node) == "<div></div>"


def test_cond_multi_branch():
    def badge(is_admin: bool, is_premium: bool) -> str:
        return str(
            html(
                t"<div>{cond(
                    (is_admin,   html(t'<span class="admin">ADMIN</span>')),
                    (is_premium, html(t'<span class="pro">PRO</span>')),
                    default=     html(t'<span>FREE</span>'),
                )}</div>"
            )
        )

    assert badge(True, False) == '<div><span class="admin">ADMIN</span></div>'
    assert badge(False, True) == '<div><span class="pro">PRO</span></div>'
    assert badge(False, False) == "<div><span>FREE</span></div>"


# ---------------------------------------------------------------------------
# Sentinel — explicit None/falsy default is respected
# ---------------------------------------------------------------------------


def test_when_explicit_none_default_renders_empty():
    # Passing None explicitly as the default value should render empty,
    # not be confused with "no default provided".
    result = Conditions().when(False, "a").default(None).__html__()
    assert result == Markup("")


def test_cond_explicit_none_default_returns_none():
    result = cond((False, "a"), default=None)
    assert result is None


def test_cond_explicit_false_default_returns_false():
    result = cond((False, "a"), default=False)
    assert result is False
