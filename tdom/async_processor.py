import inspect
import typing as t
from collections.abc import AsyncIterable, Iterable, Sequence
from string.templatelib import Interpolation, Template

from markupsafe import Markup

from .callables import get_callable_info
from .format import format_template
from .nodes import Fragment, Node, Text
from .placeholders import TemplateRef
from .processor import (
    HasHTMLDunder,
    _flatten_nodes,
    _parse_and_cache,
    _resolve_attrs,
    _resolve_ref,
    _resolve_t_attrs,
    format_interpolation,
    _kebab_to_snake,
) # _ needs to remove in future as these are no more private to the class
from .processor import AttributesDict
from .utils import CachableTemplate

from .parser import (
    TComment,
    TComponent,
    TDocumentType,
    TElement,
    TFragment,
    TNode,
    TText,
)
from .nodes import Comment, DocumentType, Element


async def _node_from_value(value: object) -> Node:
    """
    Convert an arbitrary value to a Node, with async support.

    Handles AsyncIterable, awaitable callable results, and Template values
    via html_async recursion.
    """
    match value:
        case str():
            return Text(value)
        case Node():
            return value
        case Template():
            return await html_async(value)
        case False | None:
            return Fragment(children=[])
        case AsyncIterable():
            children = [await _node_from_value(v) async for v in value]
            return Fragment(children=children)
        case Iterable():
            children = [await _node_from_value(v) for v in value]
            return Fragment(children=children)
        case HasHTMLDunder():
            return Text(Markup(value.__html__()))
        case c if callable(c):
            result = c()
            if inspect.isawaitable(result):
                result = await result
            return await _node_from_value(result)
        case _:
            return Text(str(value))


async def _invoke_component(
    attrs: AttributesDict,
    children: Sequence[Node],
    interpolation: Interpolation,
) -> Node:
    """
    Invoke a component callable with async support.

    Calls the callable, then awaits the result if it is awaitable.
    """
    component_name = interpolation.expression or "unknown component"
    value = format_interpolation(interpolation)
    if not callable(value):
        raise TypeError(
            f"Expected a callable for component invocation, got {type(value).__name__}"
        )
    callable_info = get_callable_info(value)

    if callable_info.requires_positional:
        err = TypeError(
            "Component callables cannot have required positional arguments."
        )
        err.add_note(f"While invoking component: {component_name}")
        raise err

    kwargs: AttributesDict = {}

    for attr_name, attr_value in attrs.items():
        snake_name = _kebab_to_snake(attr_name)
        if snake_name in callable_info.named_params or callable_info.kwargs:
            kwargs[snake_name] = attr_value

    if "children" in callable_info.named_params or callable_info.kwargs:
        kwargs["children"] = tuple(children)

    missing = callable_info.required_named_params - kwargs.keys()
    if missing:
        err = TypeError(
            f"Missing required parameters for component: {', '.join(missing)}"
        )
        err.add_note(f"While invoking component: {component_name}")
        raise err

    try:
        result = value(**kwargs)
        if inspect.isawaitable(result):
            result = await result
    except TypeError as e:
        e.add_note(f"While invoking component: {component_name}")
        raise
    return await _node_from_value(result)


async def _resolve_t_text_ref(
    ref: TemplateRef, interpolations: tuple[Interpolation, ...]
) -> Text | Fragment:
    """Resolve a TText ref into Text or Fragment, with async _node_from_value."""
    if ref.is_literal:
        return Text(ref.strings[0])

    parts: list[Node] = []
    for part in _resolve_ref(ref, interpolations):
        if isinstance(part, str):
            parts.append(Text(part))
        else:
            parts.append(await _node_from_value(format_interpolation(part)))

    flat = _flatten_nodes(parts)

    if len(flat) == 1 and isinstance(flat[0], Text):
        return flat[0]

    return Fragment(children=flat)


async def _substitute_and_flatten_children(
    children: t.Iterable[TNode], interpolations: tuple[Interpolation, ...]
) -> list[Node]:
    """Substitute placeholders in children sequentially and flatten fragments."""
    resolved = [await _resolve_t_node(child, interpolations) for child in children]
    return _flatten_nodes(resolved)


async def _resolve_t_node(
    t_node: TNode, interpolations: tuple[Interpolation, ...]
) -> Node:
    """Resolve a TNode tree into a Node tree, with async support."""
    match t_node:
        case TText(ref=ref):
            return await _resolve_t_text_ref(ref, interpolations)
        case TComment(ref=ref):
            comment_t = _resolve_ref(ref, interpolations)
            comment = format_template(comment_t)
            return Comment(comment)
        case TDocumentType(text=text):
            return DocumentType(text)
        case TFragment(children=children):
            resolved_children = await _substitute_and_flatten_children(
                children, interpolations
            )
            return Fragment(children=resolved_children)
        case TElement(tag=tag, attrs=attrs, children=children):
            resolved_attrs = _resolve_attrs(attrs, interpolations)
            resolved_children = await _substitute_and_flatten_children(
                children, interpolations
            )
            return Element(tag=tag, attrs=resolved_attrs, children=resolved_children)
        case TComponent(
            start_i_index=start_i_index,
            end_i_index=end_i_index,
            attrs=t_attrs,
            children=children,
        ):
            start_interpolation = interpolations[start_i_index]
            end_interpolation = (
                None if end_i_index is None else interpolations[end_i_index]
            )
            resolved_attrs = _resolve_t_attrs(t_attrs, interpolations)
            resolved_children = await _substitute_and_flatten_children(
                children, interpolations
            )
            if (
                end_interpolation is not None
                and end_interpolation.value != start_interpolation.value
            ):
                raise TypeError("Mismatched component start and end callables.")
            return await _invoke_component(
                attrs=resolved_attrs,
                children=resolved_children,
                interpolation=start_interpolation,
            )
        case _:
            raise ValueError(f"Unknown TNode type: {type(t_node).__name__}")


async def html_async(template: Template) -> Node:
    """Parse an HTML t-string, substitute values, and return a tree of Nodes (async)."""
    cachable = CachableTemplate(template)
    t_node = _parse_and_cache(cachable)
    return await _resolve_t_node(t_node, template.interpolations)


async def svg_async(template: Template) -> Node:
    """Parse a standalone SVG fragment and return a tree of Nodes (async).

    Async counterpart of ``svg()``. Use when the template does not contain
    an ``<svg>`` wrapper element.
    """
    cachable = CachableTemplate(template, svg_context=True)
    t_node = _parse_and_cache(cachable)
    return await _resolve_t_node(t_node, template.interpolations)
