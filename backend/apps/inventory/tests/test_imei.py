import pytest

from apps.inventory.imei import is_valid_imei


@pytest.mark.parametrize("imei", ["490154203237518", "356938035643809"])
def test_valid_imeis(imei):
    assert is_valid_imei(imei)


@pytest.mark.parametrize(
    "imei", ["490154203237519", "49015420323751", "4901542032375180", "49015420323751a", "", "٤٩٠١٥٤٢٠٣٢٣٧٥١٨"]
)
def test_invalid_imeis(imei):
    assert not is_valid_imei(imei)


def test_check_digit_completes_valid_imei():
    from apps.inventory.imei import with_check_digit

    assert with_check_digit("49015420323751") == "490154203237518"
