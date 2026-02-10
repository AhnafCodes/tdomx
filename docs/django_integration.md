# Django Integration

`tdom` can be integrated into Django as a custom template backend. This allows you to use `tdom` components in your views just like standard Django templates.

## ⚠️ Limitations & Requirements

*   **Python 3.14+**: Required for `tdom`. Ensure your Django version is compatible.
*   **No Context Processors**: Standard Django context processors (e.g., `auth`, `messages`) are **not** automatically executed. You must pass required data (like `user` or `messages`) explicitly from your views.
*   **No Template Tags**: Django template tags and filters (e.g., `{% url %}`, `|date`) do not work. Use their Python equivalents directly (e.g., `django.urls.reverse`, `django.templatetags.static.static`).
*   **Caching**: Since components are Python modules, changes in development may require a server restart to reflect updates due to Python's module caching.
*   **Security**: Never pass unvalidated user input to the `:safe` format specifier.

## 1. Create the Backend

Create a file named `tdom_backend.py` in one of your Django apps (e.g., `your_app/tdom_backend.py`).

This backend handles the critical conversion of Django's `SafeString` (used for CSRF tokens) to `markupsafe.Markup` so `tdom` doesn't escape them.

```python
import importlib
from string.templatelib import Template as TStringTemplate

from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.backends.base import BaseEngine
from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy
from django.utils.safestring import SafeString
from markupsafe import Markup
from tdom import html

class TdomBackend(BaseEngine):
    app_dirname = 'tdom_templates'

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS', {}).copy()
        super().__init__(params)

    def get_template(self, template_name):
        """
        Load a template from a Python dotted path like 'my_app.components.HomePage'
        """
        try:
            module_path, func_name = template_name.rsplit('.', 1)
            module = importlib.import_module(module_path)
            template_func = getattr(module, func_name)
            return TdomTemplate(template_func)
        except (ImportError, AttributeError, ValueError) as exc:
            raise TemplateDoesNotExist(
                f"Could not load '{template_name}': {exc}",
                backend=self
            )

class TdomTemplate:
    def __init__(self, template_func):
        self.template_func = template_func

    def render(self, context=None, request=None):
        if context is None:
            context = {}

        # Flatten Django Context to dict if needed
        if hasattr(context, 'flatten'):
            context = context.flatten()

        # Add request and CSRF tokens to context (Django convention)
        if request is not None:
            context['request'] = request
            context['csrf_input'] = csrf_input_lazy(request)
            context['csrf_token'] = csrf_token_lazy(request)

        # CRITICAL: Convert Django SafeStrings to MarkupSafe Markup
        # This ensures CSRF tokens and other safe Django content aren't escaped by tdom
        for key, value in context.items():
            if isinstance(value, SafeString):
                context[key] = Markup(str(value))

        try:
            # Call the component function with context as kwargs
            result = self.template_func(**context)
        except TypeError as exc:
            raise TemplateSyntaxError(f"Error rendering tdom component: {exc}")

        # Handle different return types
        if isinstance(result, TStringTemplate):
            return str(html(result))
        elif hasattr(result, '__html__'):
            return str(result)
        else:
            return str(result)
```

## 2. Configure Settings

Add the backend to your `TEMPLATES` setting in `settings.py`.

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            # ... standard options
        },
    },
    {
        'BACKEND': 'your_app.tdom_backend.TdomBackend',
        'DIRS': [],
        'APP_DIRS': False,
        'OPTIONS': {},
        'NAME': 'tdom',
    },
]
```

## 3. Create Components

Define your components in a Python module (e.g., `your_app/components.py`).

**Important**:
*   Accept `**kwargs` to handle extra context injected by Django (like `request`, `csrf_token`).
*   Use `csrf_input` directly; the backend has already converted it to a safe string for you.
*   Use `static()` for assets.

```python
from tdom import html, Node
from django.templatetags.static import static

def HomePage(user_name: str, csrf_input: str, **kwargs) -> Node:
    """Home page component."""
    logo_url = static('images/logo.png')

    return html(t"""
        <div class="home-page">
            <img src="{logo_url}" alt="Logo" />
            <h1>Welcome, {user_name}!</h1>
            <form method="post">
                {csrf_input}
                <button type="submit">Submit</button>
            </form>
        </div>
    """)
```

## 4. Use in Views

Render the component using its dotted Python path.

```python
from django.shortcuts import render

def home(request):
    # Pass data explicitly; context processors are not run.
    return render(request, 'your_app.components.HomePage', {'user_name': 'Alice'})
```

## Testing & Debugging

*   **Testing**: Test components as pure Python functions. You can mock context variables like `csrf_input` with simple strings.
*   **Debugging**: Enable Django's `DEBUG` mode. `tdom` errors will appear in the standard Django traceback.
*   **Migration**: You can mix `tdom` and Django templates in the same project. Start by migrating leaf components or specific views.
