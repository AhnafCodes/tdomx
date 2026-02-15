import pytest
from tdom import create_context, html, html_async

def test_context_basic_roundtrip():
    Ctx = create_context("test")
    with Ctx.provide("value"):
        assert Ctx.get() == "value"

def test_context_missing_raises_lookup_error():
    Ctx = create_context("test")
    with pytest.raises(LookupError):
        Ctx.get()

def test_context_default_value():
    Ctx = create_context("test", default="default")
    assert Ctx.get() == "default"

def test_context_nested_override():
    Ctx = create_context("test", default="root")
    
    assert Ctx.get() == "root"
    with Ctx.provide("level1"):
        assert Ctx.get() == "level1"
        with Ctx.provide("level2"):
            assert Ctx.get() == "level2"
        assert Ctx.get() == "level1"
    assert Ctx.get() == "root"

def test_context_in_component():
    UserCtx = create_context("user")
    
    def UserGreeting():
        user = UserCtx.get()
        return html(t"<span>Hello, {user}!</span>")
    
    with UserCtx.provide("Alice"):
        node = html(t"<div><{UserGreeting} /></div>")
        assert str(node) == "<div><span>Hello, Alice!</span></div>"

def test_context_isolation():
    # Ensure contexts don't leak
    Ctx = create_context("test")
    
    def Component():
        return html(t"{Ctx.get()}")

    with Ctx.provide("A"):
        node1 = html(t"<{Component} />")
    
    with Ctx.provide("B"):
        node2 = html(t"<{Component} />")
        
    assert str(node1) == "A"
    assert str(node2) == "B"

@pytest.mark.asyncio
async def test_context_async_propagation():
    # contextvars should propagate to async tasks automatically
    Ctx = create_context("async")
    
    async def AsyncComp():
        val = Ctx.get()
        return t"Async: {val}"
        
    with Ctx.provide("propagated"):
        node = await html_async(t"<{AsyncComp} />")
        assert str(node) == "Async: propagated"
