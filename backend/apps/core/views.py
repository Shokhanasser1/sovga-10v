from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def demo(request):
    """Витрина показывает плашку «Учебный магазин», если включён учебный режим."""
    return JsonResponse({"demo": settings.DEMO_MODE})
