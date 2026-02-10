import asyncio
import inspect
import typing as t
from collections.abc import Iterable
from string.templatelib import Interpolation, Template

from markupsafe import Markup

from .callables import get_callable_info
from .nodes import Comment, DocumentType, Element, Fragment, Node, Text
from .parser import (
    TComment,
    TComponent,
    TDocumentType,
    TElement,
    TFragment,
    TNode,
    TText,
)
from .placeholders import TemplateRef
from .processor import (
    HasHTMLDunder,
    flatten_nodes,
    kebab_to_snake,
    parse_and_cache,
    resolve_attrs,
    resolve_ref,
    resolve_t_attrs,
    format_interpolation,
    format_template,
    html,
)
from .utils import CachableTemplate


async def _node_from_value_async(value: object) -> Node:
    """
    Convert an arbitrary value to a Node asynchronously.
    """
    # Handle coroutines first
    if inspect.iscoroutine(value):
        value = await value

    match value:
        case str():
            return Text(value)
        case Node():
            return value
        case Template():
            # If we get a Template back, we process it asynchronously
            return await html_async(value)
        case False | None:
            return Fragment(children=[])
        case Iterable():
            # Process iterable items in parallel if they are awaitables,
            # or just recursively process them.
            # Since we don't know if the iterable yields coroutines or values,
            # we have to iterate and process.
            # To maximize parallelism, we can gather.
            tasks = [_node_from_value_async(v) for v in value]
            children = await asyncio.gather(*tasks)
            return Fragment(children=children)
        case HasHTMLDunder():
            return Text(Markup(value.__html__()))
        case c if callable(c):
            # Invoke callable, check if result is coroutine
            result = c()
            if inspect.iscoroutine(result):
                result = await result
            return await _node_from_value_async(result)
        case _:
            return Text(str(value))


async def _invoke_component_async(
    attrs: dict[str, object],
    children: list[Node],
    interpolation: Interpolation,
) -> Node:
    """
    Invoke a component callable asynchronously.
    """
    value = format_interpolation(interpolation)
    if not callable(value):
        raise TypeError(
            f"Expected a callable for component invocation, got {type(value).__name__}"
        )
    callable_info = get_callable_info(value)

    if callable_info.requires_positional:
        raise TypeError(
            "Component callables cannot have required positional arguments."
        )

    kwargs: dict[str, object] = {}

    for attr_name, attr_value in attrs.items():
        snake_name = kebab_to_snake(attr_name)
        if snake_name in callable_info.named_params or callable_info.kwargs:
            kwargs[snake_name] = attr_value

    if "children" in callable_info.named_params or callable_info.kwargs:
        kwargs["children"] = tuple(children)

    missing = callable_info.required_named_params - kwargs.keys()
    if missing:
        raise TypeError(
            f"Missing required parameters for component: {', '.join(missing)}"
        )

    result = value(**kwargs)
    if inspect.iscoroutine(result):
        result = await result
    return await _node_from_value_async(result)


async def _substitute_and_flatten_children_async(
    children: t.Iterable[TNode], interpolations: tuple[Interpolation, ...]
) -> list[Node]:
    """
    Substitute placeholders in a list of children and flatten any fragments asynchronously.
    """
    # Create tasks for all children to resolve them in parallel
    tasks = [_resolve_t_node_async(child, interpolations) for child in children]
    resolved = await asyncio.gather(*tasks)
    flat = flatten_nodes(resolved)
    return flat


async def _resolve_t_text_ref_async(
    ref: TemplateRef, interpolations: tuple[Interpolation, ...]
) -> Text | Fragment:
    """Resolve a TText ref into Text or Fragment by processing interpolations asynchronously."""
    if ref.is_literal:
        return Text(ref.strings[0])

    # Resolve interpolated parts in parallel; string literals don't need async.
    sync_parts: list[tuple[int, Node]] = []
    async_tasks: list[tuple[int, asyncio.Task]] = []
    for i, part in enumerate(resolve_ref(ref, interpolations)):
        if isinstance(part, str):
            sync_parts.append((i, Text(part)))
        else:
            val = format_interpolation(part)
            async_tasks.append((i, asyncio.create_task(_node_from_value_async(val))))

    async_results = await asyncio.gather(*(task for _, task in async_tasks))

    # Reassemble in original order
    parts: list[Node] = [None] * (len(sync_parts) + len(async_tasks))
    for idx, node in sync_parts:
        parts[idx] = node
    for (idx, _), node in zip(async_tasks, async_results):
        parts[idx] = node

    flat = flatten_nodes(parts)

    if len(flat) == 1 and isinstance(flat[0], Text):
        return flat[0]

    return Fragment(children=flat)


async def _resolve_t_node_async(
    t_node: TNode, interpolations: tuple[Interpolation, ...]
) -> Node:
    """Resolve a TNode tree into a Node tree by processing interpolations asynchronously."""
    match t_node:
        case TText(ref=ref):
            return await _resolve_t_text_ref_async(ref, interpolations)
        case TComment(ref=ref):
            comment_t = resolve_ref(ref, interpolations)
            comment = format_template(comment_t)
            return Comment(comment)
        case TDocumentType(text=text):
            return DocumentType(text)
        case TFragment(children=children):
            resolved_children = await _substitute_and_flatten_children_async(
                children, interpolations
            )
            return Fragment(children=resolved_children)
        case TElement(tag=tag, attrs=attrs, children=children):
            # Attributes are resolved synchronously as they shouldn't contain awaitables usually,
            # or at least the current design assumes attribute values are simple.
            # If we wanted to support async attribute values, we'd need to change resolve_attrs.
            # For now, we assume attributes are sync.
            resolved_attrs = resolve_attrs(attrs, interpolations)
            resolved_children = await _substitute_and_flatten_children_async(
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
            resolved_attrs = resolve_t_attrs(t_attrs, interpolations)
            resolved_children = await _substitute_and_flatten_children_async(
                children, interpolations
            )

            if (
                end_interpolation is not None
                and end_interpolation.value != start_interpolation.value
            ):
                raise TypeError("Mismatched component start and end callables.")
            return await _invoke_component_async(
                attrs=resolved_attrs,
                children=resolved_children,
                interpolation=start_interpolation,
            )
        case _:
            raise ValueError(f"Unknown TNode type: {type(t_node).__name__}")


async def html_async(template: Template) -> Node:
    """
    Parse an HTML t-string, substitute values, and return a tree of Nodes asynchronously.
    """
    cachable = CachableTemplate(template)
    t_node = parse_and_cache(cachable)
    return await _resolve_t_node_async(t_node, template.interpolations)


async def html_stream_async(template: Template) -> t.AsyncIterator[str]:
    """
    Parse an HTML t-string and stream the output chunks asynchronously.
    Note: This is buffered streaming; it waits for the full tree to resolve first.
    """
    node = await html_async(template)
    for chunk in node.render_chunks():
        yield chunk
