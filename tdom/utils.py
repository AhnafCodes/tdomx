from collections import OrderedDict
from string.templatelib import Template


class LastUpdatedOrderedDict(OrderedDict):
    "Store items in the order the keys were last updated."

    def __setitem__(self, key, value):
        existing = key in self
        super().__setitem__(key, value)
        if existing:
            self.move_to_end(key)


class CachableTemplate:
    __slots__ = ("template", "svg_context")

    template: Template
    svg_context: bool

    # CONSIDER: what about interpolation format specs, convsersions, etc.?

    def __init__(self, template: Template, *, svg_context: bool = False) -> None:
        self.template = template
        self.svg_context = svg_context

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CachableTemplate):
            return NotImplemented
        return (
            self.template.strings == other.template.strings
            and self.svg_context == other.svg_context
        )

    def __hash__(self) -> int:
        return hash((self.template.strings, self.svg_context))
