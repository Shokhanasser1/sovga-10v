"""Проверка IMEI: 15 цифр, последняя — контрольная по алгоритму Луна."""

from django.core.exceptions import ValidationError


def _luhn_digit(payload: str) -> int:
    total = 0
    for index, char in enumerate(reversed(payload)):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10


def with_check_digit(payload: str) -> str:
    """14 цифр → полный IMEI с контрольной цифрой."""
    return payload + str(_luhn_digit(payload))


def is_valid_imei(value: str) -> bool:
    if len(value) != 15 or not (value.isascii() and value.isdigit()):
        return False
    return _luhn_digit(value[:-1]) == int(value[-1])


def validate_imei(value: str) -> None:
    if value and not is_valid_imei(value):
        raise ValidationError("Некорректный IMEI: нужно 15 цифр с верной контрольной цифрой")
