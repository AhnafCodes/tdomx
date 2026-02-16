from dataclasses import dataclass, field
from typing import Sequence
from .escaping import (
    escape_html_comment,
    escape_html_script,
    escape_html_style,
    escape_html_text,
)

# See https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = frozenset(
    [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]
)


CDATA_CONTENT_ELEMENTS = frozenset(["script", "style"])
RCDATA_CONTENT_ELEMENTS = frozenset(["textarea", "title"])
CONTENT_ELEMENTS = CDATA_CONTENT_ELEMENTS | RCDATA_CONTENT_ELEMENTS

SVG_TAG_FIX = {
    "altglyph": "altGlyph",
    "altglyphdef": "altGlyphDef",
    "altglyphitem": "altGlyphItem",
    "animatecolor": "animateColor",
    "animatemotion": "animateMotion",
    "animatetransform": "animateTransform",
    "clippath": "clipPath",
    "feblend": "feBlend",
    "fecolormatrix": "feColorMatrix",
    "fecomponenttransfer": "feComponentTransfer",
    "fecomposite": "feComposite",
    "feconvolvematrix": "feConvolveMatrix",
    "fediffuselighting": "feDiffuseLighting",
    "fedisplacementmap": "feDisplacementMap",
    "fedistantlight": "feDistantLight",
    "fedropshadow": "feDropShadow",
    "feflood": "feFlood",
    "fefunca": "feFuncA",
    "fefuncb": "feFuncB",
    "fefuncg": "feFuncG",
    "fefuncr": "feFuncR",
    "fegaussianblur": "feGaussianBlur",
    "feimage": "feImage",
    "femerge": "feMerge",
    "femergenode": "feMergeNode",
    "femorphology": "feMorphology",
    "feoffset": "feOffset",
    "fepointlight": "fePointLight",
    "fespecularlighting": "feSpecularLighting",
    "fespotlight": "feSpotLight",
    "fetile": "feTile",
    "feturbulence": "feTurbulence",
    "foreignobject": "foreignObject",
    "glyphref": "glyphRef",
    "lineargradient": "linearGradient",
    "radialgradient": "radialGradient",
    "textpath": "textPath",
}

SVG_CASE_FIX = {
    "attributename": "attributeName",
    "attributetype": "attributeType",
    "basefrequency": "baseFrequency",
    "baseprofile": "baseProfile",
    "calcmode": "calcMode",
    "clippathunits": "clipPathUnits",
    "diffuseconstant": "diffuseConstant",
    "edgemode": "edgeMode",
    "filterunits": "filterUnits",
    "glyphref": "glyphRef",
    "gradienttransform": "gradientTransform",
    "gradientunits": "gradientUnits",
    "kernelmatrix": "kernelMatrix",
    "kernelunitlength": "kernelUnitLength",
    "keypoints": "keyPoints",
    "keysplines": "keySplines",
    "keytimes": "keyTimes",
    "lengthadjust": "lengthAdjust",
    "limitingconeangle": "limitingConeAngle",
    "markerheight": "markerHeight",
    "markerunits": "markerUnits",
    "markerwidth": "markerWidth",
    "maskcontentunits": "maskContentUnits",
    "maskunits": "maskUnits",
    "numoctaves": "numOctaves",
    "pathlength": "pathLength",
    "patterncontentunits": "patternContentUnits",
    "patterntransform": "patternTransform",
    "patternunits": "patternUnits",
    "pointsatx": "pointsAtX",
    "pointsaty": "pointsAtY",
    "pointsatz": "pointsAtZ",
    "preservealpha": "preserveAlpha",
    "preserveaspectratio": "preserveAspectRatio",
    "primitiveunits": "primitiveUnits",
    "refx": "refX",
    "refy": "refY",
    "repeatcount": "repeatCount",
    "repeatdur": "repeatDur",
    "requiredextensions": "requiredExtensions",
    "requiredfeatures": "requiredFeatures",
    "specularconstant": "specularConstant",
    "specularexponent": "specularExponent",
    "spreadmethod": "spreadMethod",
    "startoffset": "startOffset",
    "stddeviation": "stdDeviation",
    "stitchtiles": "stitchTiles",
    "surfacescale": "surfaceScale",
    "systemlanguage": "systemLanguage",
    "tablevalues": "tableValues",
    "targetx": "targetX",
    "targety": "targetY",
    "textlength": "textLength",
    "viewbox": "viewBox",
    "viewtarget": "viewTarget",
    "xchannelselector": "xChannelSelector",
    "ychannelselector": "yChannelSelector",
    "zoomandpan": "zoomAndPan",
}


# FUTURE: add a pretty-printer to nodes for debugging
# FUTURE: make nodes frozen (and have the parser work with mutable builders)


def _serialize_into(node: "Node", parts: list[str]) -> None:
    """Serialize a Node into a list of string parts (linear, non-recursive style).

    Instead of each __str__ building intermediate strings that get concatenated
    up the call stack, this writes directly into a shared parts list.
    One join() at the end produces the final string.
    """
    match node:
        case Text(text=text):
            parts.append(escape_html_text(text))
        case Fragment(children=children):
            for child in children:
                _serialize_into(child, parts)
        case Comment(text=text):
            parts.append("<!--")
            parts.append(escape_html_comment(text))
            parts.append("-->")
        case DocumentType(text=text):
            parts.append("<!DOCTYPE ")
            parts.append(text)
            parts.append(">")
        case Element(tag=tag, attrs=attrs, children=children):
            # Open tag
            parts.append("<")
            parts.append(tag)
            # Attributes
            for key, value in attrs.items():
                if value is None:
                    parts.append(" ")
                    parts.append(key)
                else:
                    parts.append(' ')
                    parts.append(key)
                    parts.append('="')
                    parts.append(escape_html_text(value))
                    parts.append('"')
            # Void elements: self-close
            if tag in VOID_ELEMENTS:
                parts.append(" />")
                return
            parts.append(">")
            # Children with script/style bulk escaping
            if children and tag in ("script", "style"):
                chunks: list[str] = []
                for child in children:
                    if isinstance(child, Text):
                        chunks.append(child.text)
                    else:
                        raise ValueError(
                            "Cannot serialize non-text content inside a script tag."
                        )
                raw = "".join(chunks)
                if tag == "script":
                    parts.append(escape_html_script(raw))
                else:
                    parts.append(escape_html_style(raw))
            else:
                for child in children:
                    _serialize_into(child, parts)
            # Close tag
            parts.append("</")
            parts.append(tag)
            parts.append(">")


def serialize(node: "Node") -> str:
    """Serialize a Node tree to an HTML string.

    Uses linear list-accumulation instead of recursive string concatenation.
    """
    parts: list[str] = []
    _serialize_into(node, parts)
    return "".join(parts)


@dataclass(slots=True)
class Node:
    def __html__(self) -> str:
        """Return the HTML representation of the node."""
        return serialize(self)

    def __str__(self) -> str:
        return serialize(self)


@dataclass(slots=True)
class Text(Node):
    text: str  # which may be markupsafe.Markup in practice.

    def __str__(self) -> str:
        return escape_html_text(self.text)

    def __eq__(self, other: object) -> bool:
        # This is primarily of use for testing purposes. We only consider
        # two Text nodes equal if their string representations match.
        return isinstance(other, Text) and str(self) == str(other)


@dataclass(slots=True)
class Fragment(Node):
    children: Sequence[Node] = ()

    def __post_init__(self):
        # Ensure children are always an immutable tuple internally
        if not isinstance(self.children, tuple):
            self.children = tuple(self.children)


@dataclass(slots=True)
class Comment(Node):
    text: str


@dataclass(slots=True)
class DocumentType(Node):
    text: str = "html"


@dataclass(slots=True)
class Element(Node):
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: Sequence[Node] = ()

    def __post_init__(self):
        """Ensure all preconditions are met."""
        if not self.tag:
            raise ValueError("Element tag cannot be empty.")

        # Void elements cannot have children
        if self.is_void and self.children:
            raise ValueError(f"Void element <{self.tag}> cannot have children.")

        if not isinstance(self.children, tuple):
            self.children = tuple(self.children)

    @property
    def is_void(self) -> bool:
        return self.tag in VOID_ELEMENTS

    @property
    def is_content(self) -> bool:
        return self.tag in CONTENT_ELEMENTS
