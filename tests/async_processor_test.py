import asyncio
from string.templatelib import Template

import pytest

from tdom import html, html_async
from tdom.nodes import Element, Text


async def AsyncComponent(name: str) -> Template:
    await asyncio.sleep(0.001)
    return t"<div>Hello, {name}!</div>"


async def AsyncComponentReturningNode(name: str) -> Element:
    await asyncio.sleep(0.001)
    return Element("div", children=[Text(f"Hello, {name}!")])


async def AsyncComponentReturningString(name: str) -> str:
    await asyncio.sleep(0.001)
    return f"Hello, {name}!"


def SyncComponent(name: str) -> Template:
    return t"<div>Hello, {name}!</div>"


@pytest.mark.asyncio
async def test_async_component_returning_template():
    node = await html_async(t"<{AsyncComponent} name='Alice' />")
    assert str(node) == "<div>Hello, Alice!</div>"


@pytest.mark.asyncio
async def test_async_component_returning_node():
    node = await html_async(t"<{AsyncComponentReturningNode} name='Bob' />")
    assert str(node) == "<div>Hello, Bob!</div>"


@pytest.mark.asyncio
async def test_async_component_returning_string():
    node = await html_async(t"<{AsyncComponentReturningString} name='Charlie' />")
    assert str(node) == "Hello, Charlie!"


@pytest.mark.asyncio
async def test_mixed_sync_and_async_components():
    node = await html_async(
        t"<div><{AsyncComponent} name='Async' /><{SyncComponent} name='Sync' /></div>"
    )
    assert (
        str(node)
        == "<div><div>Hello, Async!</div><div>Hello, Sync!</div></div>"
    )


@pytest.mark.asyncio
async def test_nested_async_components():
    async def Wrapper(children):
        await asyncio.sleep(0.001)
        return t"<div class='wrapper'>{children}</div>"

    node = await html_async(
        t"<{Wrapper}><{AsyncComponent} name='Nested' /></{Wrapper}>"
    )
    assert str(node) == '<div class="wrapper"><div>Hello, Nested!</div></div>'


@pytest.mark.asyncio
async def test_async_zero_arg_callable_in_child_position():
    async def get_data():
        await asyncio.sleep(0.001)
        return "Async Data"

    node = await html_async(t"<div>{get_data}</div>")
    assert str(node) == "<div>Async Data</div>"


@pytest.mark.asyncio
async def test_async_coroutine_in_child_position():
    async def get_data():
        await asyncio.sleep(0.001)
        return "Coroutine Data"

    # Calling the function returns a coroutine object
    node = await html_async(t"<div>{get_data()}</div>")
    assert str(node) == "<div>Coroutine Data</div>"


def test_sync_html_raises_error_for_async_component():
    with pytest.raises(TypeError, match="Async component AsyncComponent cannot be used in synchronous html"):
        html(t"<{AsyncComponent} name='Error' />")
