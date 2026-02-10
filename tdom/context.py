import contextvars
from collections.abc import Iterator
from contextlib import contextmanager

_MISSING = object()


class Context[T]:
    """A scoped context for sharing data across components without prop drilling."""

    def __init__(self, name: str, *, default: T = _MISSING):
        if default is _MISSING:
            self._var: contextvars.ContextVar[T] = contextvars.ContextVar(name)
        else:
            self._var: contextvars.ContextVar[T] = contextvars.ContextVar(
                name, default=default
            )
        self.name = name

    def get(self) -> T:
        """Get the current context value. Raises LookupError if no value and no default."""
        return self._var.get()

    @contextmanager
    def provide(self, value: T) -> Iterator[T]:
        """Set the context value for the duration of a block."""
        token = self._var.set(value)
        try:
            yield value
        finally:
            self._var.reset(token)


def create_context[T](name: str, *, default: T = _MISSING) -> Context[T]:
    """Create a new Context."""
    return Context(name, default=default)
