from datetime import datetime

from django.template import Context, Engine

TEMPLATE = """
Список покупок
Дата: {{ date }}

Продукты:
{% for n, row in products %}
{{ n }}. {{ row.name|capfirst }} — {{ row.total }} {{ row.unit }}
{% endfor %}

Рецепты:
{% for n, r in recipes %}
{{ n }}. {{ r.name }} ({{ r.author.get_full_name|default:r.author.username }})
{% endfor %}
""".strip()


def render_shopping_list(products, recipes):
    engine = Engine.get_default()
    template = engine.from_string(TEMPLATE)

    context = Context(
        {
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "products": list(enumerate(products, start=1)),
            "recipes": list(enumerate(recipes, start=1)),
        }
    )

    return template.render(context)
