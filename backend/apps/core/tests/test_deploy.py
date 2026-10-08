import os
import secrets
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]


def test_production_settings_pass_django_deploy_checks():
    env = {
        **os.environ, "DEBUG": "false", "SECRET_KEY": secrets.token_urlsafe(50), "ALLOWED_HOSTS": "sovga.uz,127.0.0.1",
        "TELEGRAM_GATEWAY_TOKEN": "x", "OTP_FIXED_CODE": "",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8", timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
