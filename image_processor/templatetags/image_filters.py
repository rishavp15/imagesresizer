from django import template

register = template.Library()

@register.filter
def make_range(value):
    """
    Generate a range from 0 to value
    Usage: {% for i in 5|make_range %}
    """
    return list(range(int(value)))

@register.filter
def div(value, arg):
    """
    Divide value by arg
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def filename_only(value):
    """
    Extract filename from a path
    Usage: {{ path|filename_only }}
    """
    return value.split('/')[-1] if value else ''

@register.filter
def filesizeformat_mb(value):
    """
    Format file size in MB
    Usage: {{ size|filesizeformat_mb }}
    """
    try:
        size_mb = float(value) / (1024 * 1024)
        if size_mb < 1:
            return f"{size_mb * 1024:.1f} KB"
        else:
            return f"{size_mb:.2f} MB"
    except (ValueError, TypeError):
        return "0 B" 