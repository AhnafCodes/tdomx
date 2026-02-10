from markupsafe import Markup, escape

from .async_processor import html_async, html_stream_async
from .context import create_context
from .nodes import Comment, DocumentType, Element, Fragment, Node, Text
from .processor import html, html_stream

# We consider `Markup` and `escape` to be part of this module's public API

__all__ = [
    "Comment",
    "DocumentType",
    "Element",
    "escape",
    "Fragment",
    "html",
    "html_async",
    "html_stream",
    "html_stream_async",
    "create_context",
    "Markup",
    "Node",
    "Text",
]
