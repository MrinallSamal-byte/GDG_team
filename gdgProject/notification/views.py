from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import Notification


@require_GET
def unread_count(request):
    """Lightweight endpoint for notification badge polling."""
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0})

    count = Notification.objects.filter(user=request.user, read=False).count()
    return JsonResponse({'count': count})


@login_required
@require_POST
def mark_read(request, notification_id):
    """Mark a single notification as read for the current user."""
    updated = Notification.objects.filter(
        pk=notification_id, user=request.user
    ).update(read=True)
    if not updated:
        return JsonResponse({'error': 'not_found'}, status=404)
    return JsonResponse({'ok': True})


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read for the current user."""
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    return JsonResponse({'ok': True})
