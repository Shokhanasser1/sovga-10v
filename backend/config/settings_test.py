import os

os.environ.setdefault("SECRET_KEY", "test-only-not-a-secret")
# Тестовый клиент ходит с 127.0.0.1 — общий счётчик не должен влиять на остальные тесты.
# Сами лимиты проверяются в apps/core/tests/test_throttling.py со своими значениями.
os.environ.setdefault("THROTTLE_ANON", "100000/min")
os.environ.setdefault("THROTTLE_SEARCH", "100000/min")
os.environ.setdefault("THROTTLE_OTP", "100000/min")

from config.settings import *  # noqa: E402,F403
