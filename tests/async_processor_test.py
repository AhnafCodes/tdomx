import pytest
import asyncio

from tdom import html_async, create_context

@pytest.mark.asyncio
async def test_async_component_invocation():
    async def AsyncComp():
        await asyncio.sleep(0.001)
        return t"<span>Async Content</span>"

    node = await html_async(t"<div><{AsyncComp} /></div>")
    assert str(node) == "<div><span>Async Content</span></div>"

@pytest.mark.asyncio
async def test_sync_component_through_async_html():
    def SyncComp():
        return t"<span>Sync Content</span>"

    node = await html_async(t"<div><{SyncComp} /></div>")
    assert str(node) == "<div><span>Sync Content</span></div>"

@pytest.mark.asyncio
async def test_mixed_sync_async_components():
    async def AsyncComp():
        return t"<span>Async</span>"

    def SyncComp():
        return t"<span>Sync</span>"

    node = await html_async(t"<div><{AsyncComp} /><{SyncComp} /></div>")
    assert str(node) == "<div><span>Async</span><span>Sync</span></div>"

@pytest.mark.asyncio
async def test_async_component_with_children():
    async def Wrapper(children):
        return t"<div class='wrapper'>{children}</div>"

    node = await html_async(t"<{Wrapper}><span>Child</span></{Wrapper}>")
    assert str(node) == "<div class=\"wrapper\"><span>Child</span></div>"

@pytest.mark.asyncio
async def test_async_iterable_children():
    async def async_gen():
        yield t"<li>Item 1</li>"
        await asyncio.sleep(0.001)
        yield t"<li>Item 2</li>"

    node = await html_async(t"<ul>{async_gen()}</ul>")
    assert str(node) == "<ul><li>Item 1</li><li>Item 2</li></ul>"

@pytest.mark.asyncio
async def test_async_zero_arg_callable_child():
    async def get_data():
        await asyncio.sleep(0.001)
        return "Dynamic Data"

    node = await html_async(t"<p>{get_data}</p>")
    assert str(node) == "<p>Dynamic Data</p>"

@pytest.mark.asyncio
async def test_error_handling_non_callable():
    with pytest.raises(TypeError):
        await html_async(t"<{'not a callable'} />")

@pytest.mark.asyncio
async def test_context_api_with_async():
    Ctx = create_context("test")
    
    async def AsyncConsumer():
        val = Ctx.get()
        return t"<span>{val}</span>"

    with Ctx.provide("Context Value"):
        node = await html_async(t"<div><{AsyncConsumer} /></div>")
        assert str(node) == "<div><span>Context Value</span></div>"

@pytest.mark.asyncio
async def test_plain_html_through_async_html():
    node = await html_async(t"<div class='static'>Content</div>")
    assert str(node) == "<div class=\"static\">Content</div>"

@pytest.mark.asyncio
async def test_async_component_returning_none():
    async def NoRender():
        return None

    node = await html_async(t"<div><{NoRender} /></div>")
    assert str(node) == "<div></div>"

@pytest.mark.asyncio
async def test_async_component_returning_list():
    async def ListRender():
        return [t"<span>A</span>", t"<span>B</span>"]

    node = await html_async(t"<div><{ListRender} /></div>")
    assert str(node) == "<div><span>A</span><span>B</span></div>"
