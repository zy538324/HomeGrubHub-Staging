import pytest
from flask import Flask
from datetime import date
import types
import sys

# Stub configuration modules before importing application code
config_module = types.ModuleType("configs.config")

class TestConfig:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SECRET_KEY = 'test'

def validate_config(config):
    return True

config_module.Config = TestConfig
config_module.validate_config = validate_config
sys.modules['configs.config'] = config_module

auth_module = types.ModuleType('configs.auth0_config')
auth_module.AUTH0_CLIENT_ID = ''
auth_module.AUTH0_CLIENT_SECRET = ''
auth_module.AUTH0_DOMAIN = ''
auth_module.AUTH0_CALLBACK_URL = ''
sys.modules['configs.auth0_config'] = auth_module

from recipe_app.db import db
from recipe_app.models import User, WaterLog
from recipe_app.routes.nutrition_routes import nutrition_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test'
    db.init_app(app)
    app.register_blueprint(nutrition_bp)
    with app.app_context():
        db.create_all()
        user = User(username='water', email='water@example.com')
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_water_log_crud_and_summary(app, client):
    with client.session_transaction() as sess:
        sess['_user_id'] = 1

    resp = client.post('/log-water', json={'amount_ml': 500})
    assert resp.status_code == 200
    log_id1 = resp.get_json()['log']['id']

    resp = client.post('/log-water', json={'amount_ml': 300})
    log_id2 = resp.get_json()['log']['id']

    today = date.today().isoformat()
    resp = client.get(f'/water-summary/{today}')
    assert resp.status_code == 200
    assert resp.get_json()['total_ml'] == 800

    resp = client.put(f'/water-log/{log_id1}', json={'amount_ml': 600})
    assert resp.get_json()['log']['amount_ml'] == 600

    resp = client.get(f'/water-summary/{today}')
    assert resp.get_json()['total_ml'] == 900

    client.delete(f'/water-log/{log_id2}')
    resp = client.get(f'/water-summary/{today}')
    assert resp.get_json()['total_ml'] == 600
