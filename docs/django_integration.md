# Django Integration

`tdom` can be integrated into Django as a custom template backend. This allows you to use `tdom` components in your views just like standard Django templates.

## 1. Create the Backend

Create a file named `tdom_backend.py` in one of your Django apps (e.g., `your_app/tdom_backend.py`).

```python
import importlib
from string.templatelib import Template as TStringTemplate

from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.backends.base import BaseEngine
from django.template.backends.utils import csrf_input_lazy, csrf_token_lazy
from tdom import html

class TdomBackend(BaseEngine):
    app_dirname = 'tdom_templates'  # Required by BaseEngine

    def __init__(self, params):
        params = params.copy()
        options = params.pop('OPTIONS', {}).copy()
        super().__init__(params)

    def from_string(self, template_code):
        """
        Create a template from a Python code string that defines a component.
        Note: This expects the code to define a callable named 'component'.
        """
        try:
            # Create a temporary module to execute the code
            namespace = {}
            exec(template_code, namespace)
            if 'component' not in namespace:
                raise ValueError("Template code must define a 'component' callable")
            return TdomTemplate(namespace['component'])
        except Exception as exc:
            raise TemplateSyntaxError(f"Failed to compile tdom template: {exc}")

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

        try:
            # Call the component function with context as kwargs
            result = self.template_func(**context)
        except TypeError as exc:
            raise TemplateSyntaxError(f"Error rendering tdom component: {exc}")

        # Handle different return types
        if isinstance(result, TStringTemplate):
            # It's a t-string Template, process it with html()
            return str(html(result))
        elif hasattr(result, '__html__'):
            # It's already a Node or Markup object
            return str(result)
        else:
            # Assume it's a string
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
        'APP_DIRS': False,  # tdom uses Python imports
        'OPTIONS': {},
        'NAME': 'tdom',
    },
]
```

## 3. Create Components

Define your components in a Python module (e.g., `your_app/components.py`). Ensure they accept `**kwargs` to handle the extra context Django injects (like `request`, `csrf_token`, etc.).

```python
from tdom import html
from django.middleware.csrf import get_token
from django.templatetags.static import static

def HomePage(user_name, request=None, **kwargs):
    """Home page component with proper CSRF handling."""
    csrf_token = get_token(request) if request else ''

    return html(t"""
        <div class="home-page">
            <h1>Welcome, {user_name}!</h1>
            <form method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}" />
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
    return render(request, 'your_app.components.HomePage', {'user_name': 'Alice'})
```

## Utilities

To bridge Django's `SafeString` with `tdom`'s `Markup`, you can use a helper:

```python
from markupsafe import Markup
from django.utils.safestring import SafeString

def django_safe_to_markup(safe_string):
    """Convert Django SafeString to MarkupSafe Markup."""
    if isinstance(safe_string, SafeString):
        return Markup(str(safe_string))
    return safe_string
```
