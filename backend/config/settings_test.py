import os

os.environ.setdefault("SECRET_KEY", "test-only-not-a-secret")

from config.settings import *  # noqa: E402,F403
