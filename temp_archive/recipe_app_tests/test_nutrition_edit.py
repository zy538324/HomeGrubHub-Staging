import pytest
from pathlib import Path
from flask import Flask
import types
import sys

# Stub configuration modules
config_module = types.ModuleType('configs.config')

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
from recipe_app.routes.nutrition_routes import nutrition_bp


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test'
    app.config['WTF_CSRF_ENABLED'] = False
    db.init_app(app)
    app.register_blueprint(nutrition_bp)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client):
    with client.session_transaction() as sess:
        sess['_user_id'] = 1


def test_edit_button_present():
    content = Path('recipe_app/templates/nutrition_tracker.html').read_text()
    assert 'onclick="editEntry(${entry.id})"' in content


def test_update_nutrition_entry(client):
    _login(client)
    payload = {
        'product_name': 'Apple',
        'brand': 'Test',
        'portion_size': 100,
        'servings': 1,
        'meal_type': 'snack',
        'notes': '',
        'nutrition': {
            'calories': 50,
            'protein': 1,
            'carbs': 10,
            'fat': 0,
            'fiber': 2,
            'sugar': 8,
            'sodium': 5,
            'cholesterol': 0
        }
    }

    resp = client.post('/log-nutrition', json=payload)
    assert resp.status_code == 200
    entry_id = resp.get_json()['entry_id']

    update_payload = payload.copy()
    update_payload['product_name'] = 'Green Apple'
    update_payload['nutrition'] = payload['nutrition'].copy()
    update_payload['nutrition']['calories'] = 60

    resp = client.put(f'/nutrition-entry/{entry_id}', json=update_payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['success'] is True
    assert data['entry']['product_name'] == 'Green Apple'
    assert data['entry']['calories'] == 60

    resp = client.get(f'/nutrition-entry/{entry_id}')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['entry']['product_name'] == 'Green Apple'
