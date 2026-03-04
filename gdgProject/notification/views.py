from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def unread_count(request):
    """Lightweight endpoint for notification badge polling.
    Returns the number of unread notifications for the current user.
    When models are wired up, this should query Notification.objects.filter(
        user=request.user, read=False).count().
    """
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})

    # Stub: return a fixed count; replace with real query when Notification model exists
    count = 3
    return JsonResponse({'count': count})
