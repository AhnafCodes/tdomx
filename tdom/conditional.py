from typing import Self
from collections.abc import Callable

from markupsafe import Markup, escape

from .processor import HasHTMLDunder

# Sentinel distinguishing "no default provided" from an explicit None/falsy value.
_UNSET: object = object()

type _Value = object | Callable[[], object]


def _resolve_value(val: object) -> object:
    return val() if callable(val) else val


def _to_markup(result: object) -> Markup:
    match result:
        case None:
            return Markup("")
        case HasHTMLDunder():
            return Markup(result.__html__())
        case _:
            return escape(str(result))


class Conditions:
    """
    Evaluates cases in order and resolves the value paired with the first
    truthy condition.  Values may be plain objects (evaluated eagerly) or
    zero-argument callables (evaluated lazily at resolution time).

    Usage::

        html(t"<div>{
            Conditions()
            .when(user.is_admin,   html(t'<badge class="admin">ADMIN</badge>'))
            .when(user.is_premium, html(t'<badge class="prp">PRO</badge>'))
            .default(              html(t'<badge>FREE</badge>'))
        }</div>")

    Lazy (deferred) form::

        html(t"<div>{
            Conditions()
            .when(user.is_admin,   lambda: expensive_admin_component(user))
            .when(user.is_premium, lambda: db_query_component(user))
            .default(              lambda: fallback_component())
        }</div>")

    ``When`` implements ``__html__`` so tdom's ``_node_from_value`` picks it up
    via the ``HasHTMLDunder`` protocol — no ``.end()`` call needed.
    """

    __slots__ = ("_cases", "_default")

    def __init__(self) -> None:
        self._cases: list[tuple[bool, _Value]] = []
        self._default: _Value = _UNSET

    def when(self, condition: bool, value: _Value) -> Self:
        """Add a conditional branch.  First truthy condition wins."""
        self._cases.append((condition, value))
        return self

    def default(self, value: _Value) -> Self:
        """Set the fallback value used when no condition matches."""
        self._default = value
        return self

    def _resolve(self) -> object:
        for cond, val in self._cases:
            if cond:
                return _resolve_value(val)
        if self._default is not _UNSET:
            return _resolve_value(self._default)
        return None

    def __html__(self) -> str:
        return _to_markup(self._resolve())


def cond(
    *pairs: tuple[bool, _Value],
    default: _Value = _UNSET,
) -> object | None:
    """Return the value paired with the first truthy condition, or *default*.

    Values and *default* may be plain objects or zero-argument callables;
    callables are invoked only if their branch is selected.

    Returns ``None`` (renders as empty) when no condition matches and no
    default is provided.

    Usage::

        html(t"<div>{cond(
            (user.is_admin,              html(t'<badge class="admin">ADMIN</badge>')),
            (user.is_premium and c > 100, html(t'<badge class="vip">VIP</badge>')),
            (user.is_premium,             html(t'<badge class="premium">PREMIUM</badge>')),
            default=html(t'<badge>FREE</badge>'),
        )}</div>")
    """
    for condition, value in pairs:
        if condition:
            return _resolve_value(value)
    if default is not _UNSET:
        return _resolve_value(default)
    return None
