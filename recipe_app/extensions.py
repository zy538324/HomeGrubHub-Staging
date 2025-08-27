from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from authlib.integrations.flask_client import OAuth

# Central place for Flask extension instances

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bootstrap = Bootstrap()
oauth = OAuth()
csrf = CSRFProtect()

__all__ = [
    "db",
    "login_manager",
    "migrate",
    "bootstrap",
    "oauth",
    "csrf",
]
