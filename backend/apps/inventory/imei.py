"""Проверка IMEI: 15 цифр, последняя — контрольная по алгоритму Луна."""

from django.core.exceptions import ValidationError


def is_valid_imei(value: str) -> bool:
    if len(value) != 15 or not (value.isascii() and value.isdigit()):
        return False
    total = 0
    for index, char in enumerate(reversed(value[:-1])):
        digit = int(char)
        if index % 2 == 0:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return (10 - total % 10) % 10 == int(value[-1])


def validate_imei(value: str) -> None:
    if value and not is_valid_imei(value):
        raise ValidationError("Некорректный IMEI: нужно 15 цифр с верной контрольной цифрой")
