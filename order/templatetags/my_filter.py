from django import template

register = template.Library()


@register.filter
def search_dict(order_dict, sku_id):
    return order_dict.pop(sku_id, 0)
