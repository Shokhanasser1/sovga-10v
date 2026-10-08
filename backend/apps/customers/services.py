from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Customer


@transaction.atomic
def customer_for_phone(phone: str) -> Customer:
    """Покупатель по номеру; при первом входе создаётся вместе с пользователем без пароля."""
    existing = Customer.objects.select_related("user").filter(phone=phone).first()
    if existing:
        return existing
    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=phone)
    if user.has_usable_password():
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return Customer.objects.create(user=user, phone=phone)
