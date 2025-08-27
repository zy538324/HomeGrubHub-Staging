import os
import tempfile
import sys
from pathlib import Path
import pytest

# Set defaults at import time so application config picks them up
_defaults = {
    "SECRET_KEY": "test",
    "STRIPE_PUBLISHABLE_KEY": "test",
    "STRIPE_SECRET_KEY": "test",
    "STRIPE_WEBHOOK_SECRET": "test",
    "AUTH0_CLIENT_ID": "test",
    "AUTH0_CLIENT_SECRET": "test",
    "AUTH0_DOMAIN": "test",
    "AUTH0_CALLBACK_URL": "http://localhost",
    "AUTH0_AUDIENCE": "test",
    "SENDGRID_API_KEY": "test",
}
for key, value in _defaults.items():
    os.environ.setdefault(key, value)

_db_fd, _db_path = tempfile.mkstemp(prefix="hgh_test_", suffix=".db")
os.close(_db_fd)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_db_path}")

# Ensure the project root is on the Python path for imports
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    try:
        os.remove(_db_path)
    except OSError:
        pass
