from django import template
from django.template.loader import get_template

from forms_builder.forms.forms import FormForForm

register = template.Library()

class BuiltFormNode(template.Node):

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def render(self, context):
        request = context["request"]
        post = getattr(request, "POST", None)
        form = template.Variable(self.value).resolve(context)
        t = get_template("forms/includes/built_form.html")
        context["form"] = form
        form_args = (form, context, post or None)
        context["form_for_form"] = FormForForm(*form_args)
        return t.render(context)


@register.tag
def render_form(parser, token):
    """
    render_form takes one argument in one of the following formats:

    {% render_build_form form_instance %}

    """
    try:
        _, arg = token.split_contents()
        arg = "form=" + arg
        name, value = arg.split("=", 1)
    except ValueError:
        raise template.TemplateSyntaxError(render_form.__doc__)
    return BuiltFormNode(name, value)
