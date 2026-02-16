from markupsafe import Markup, escape
from .async_processor import html_async
from .context import create_context
from .nodes import Comment, DocumentType, Element, Fragment, Node, Text, serialize
from .processor import html

# We consider `Markup` and `escape` to be part of this module's public API

__all__ = [
    "Comment",
    "DocumentType",
    "Element",
    "escape",
    "Fragment",
    "html",
    "html_async",
    "Markup",
    "Node",
    "serialize",
    "Text",
]
