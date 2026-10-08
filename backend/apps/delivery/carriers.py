"""Адаптеры доставки (CarrierProvider из спецификации).

Сейчас без API: свой курьер (имя и телефон) и служба доставки, у которой накладную оформляют вручную.
Когда служба будет выбрана, её адаптер создаст накладную через API — модуль заказов не меняется.
"""

from dataclasses import dataclass, replace
from typing import Protocol

from apps.customers.phones import normalize_uz_phone

from .models import Shipment


class HandoverError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Handover:
    courier_name: str = ""
    courier_phone: str = ""
    service_name: str = ""
    tracking: str = ""
    cost_uzs: int = 0


class CarrierProvider(Protocol):
    code: str

    def prepare(self, handover: Handover) -> Handover:
        """Проверяет и нормализует данные передачи; ошибка — HandoverError."""

    def describe(self, handover: Handover) -> str:
        """Строка для истории заказа."""


class OwnCourier:
    code = Shipment.Carrier.OWN

    def prepare(self, handover: Handover) -> Handover:
        name = handover.courier_name.strip()
        phone = normalize_uz_phone(handover.courier_phone)
        if not name or phone is None:
            raise HandoverError("Укажите имя курьера и его узбекский мобильный номер")
        return Handover(courier_name=name[:100], courier_phone=phone, cost_uzs=handover.cost_uzs)

    def describe(self, handover: Handover) -> str:
        return f"Курьер {handover.courier_name}, {handover.courier_phone}"


class ManualService:
    code = Shipment.Carrier.SERVICE

    def prepare(self, handover: Handover) -> Handover:
        service, tracking = handover.service_name.strip(), handover.tracking.strip()
        if not service or not tracking:
            raise HandoverError("Укажите службу доставки и номер накладной")
        return replace(Handover(service_name=service[:100], tracking=tracking[:64]), cost_uzs=handover.cost_uzs)

    def describe(self, handover: Handover) -> str:
        return f"{handover.service_name}, накладная {handover.tracking}"


CARRIERS: dict[str, CarrierProvider] = {carrier.code: carrier for carrier in (OwnCourier(), ManualService())}
