import asyncio

import pytest
from tdom import html, html_async, html_stream, html_stream_async
from tdom.nodes import Element, Text, Fragment, Comment, DocumentType


def test_streaming_basic_element():
    template = t"<div id='main'>Hello</div>"
    chunks = list(html_stream(template))
    assert "".join(chunks) == '<div id="main">Hello</div>'
    # Verify chunk structure: open tag, content, close tag
    assert chunks == ['<div id="main">', 'Hello', '</div>']


def test_streaming_void_element():
    template = t"<br class='break' />"
    chunks = list(html_stream(template))
    assert "".join(chunks) == '<br class="break" />'
    assert len(chunks) == 1


def test_streaming_nested_elements():
    template = t"<ul><li>A</li><li>B</li></ul>"
    chunks = list(html_stream(template))
    assert "".join(chunks) == "<ul><li>A</li><li>B</li></ul>"
    # Expected: <ul>, <li>, A, </li>, <li>, B, </li>, </ul>
    assert chunks == ['<ul>', '<li>', 'A', '</li>', '<li>', 'B', '</li>', '</ul>']


def test_streaming_fragment():
    template = t"<span>1</span><span>2</span>"
    chunks = list(html_stream(template))
    assert "".join(chunks) == "<span>1</span><span>2</span>"
    assert chunks == ['<span>', '1', '</span>', '<span>', '2', '</span>']


def test_streaming_script_tag():
    # Scripts are special, they yield content as a single escaped block
    template = t"<script>console.log('test');</script>"
    chunks = list(html_stream(template))
    assert "".join(chunks) == "<script>console.log('test');</script>"
    # Expected: <script>, content, </script>
    assert len(chunks) == 3
    assert chunks[1] == "console.log('test');"


def test_streaming_comment():
    template = t"<!-- comment -->"
    chunks = list(html_stream(template))
    assert "".join(chunks) == "<!-- comment -->"
    assert len(chunks) == 1


def test_streaming_doctype():
    template = t"<!DOCTYPE html>"
    chunks = list(html_stream(template))
    assert "".join(chunks) == "<!DOCTYPE html>"
    assert len(chunks) == 1


def test_streaming_with_interpolation():
    name = "World"
    chunks = list(html_stream(t"<div>Hello {name}</div>"))
    assert "".join(chunks) == "<div>Hello World</div>"


@pytest.mark.asyncio
async def test_async_streaming():
    template = t"<div>Async Stream</div>"
    chunks = []
    async for chunk in html_stream_async(template):
        chunks.append(chunk)

    assert "".join(chunks) == "<div>Async Stream</div>"
    assert chunks == ['<div>', 'Async Stream', '</div>']


@pytest.mark.asyncio
async def test_async_streaming_with_async_component():
    async def AsyncGreeting(name: str):
        await asyncio.sleep(0.001)
        return t"<span>Hello, {name}!</span>"

    chunks = []
    async for chunk in html_stream_async(t"<div><{AsyncGreeting} name='Alice' /></div>"):
        chunks.append(chunk)

    joined = "".join(chunks)
    assert joined == "<div><span>Hello, Alice!</span></div>"
    # The inner template's interpolation produces separate text nodes,
    # so we verify the overall output rather than exact chunk boundaries.
    assert chunks[0] == '<div>'
    assert chunks[-1] == '</div>'
