class ThemeMiddleware:
    """Middleware to set the theme from user profile or cookie on every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.theme = request.user.theme_preference
        else:
            request.theme = request.COOKIES.get('theme', 'light')
        response = self.get_response(request)
        return response
