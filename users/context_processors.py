def theme_context(request):
    """Add theme to all template contexts for server-side rendering."""
    return {
        'theme': getattr(request, 'theme', 'light'),
    }
