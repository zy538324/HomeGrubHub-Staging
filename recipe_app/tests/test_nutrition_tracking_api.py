import pytest
from recipe_app.db import db
from recipe_app import create_app
from flask import json

def get_auth_headers():
    # Replace with actual auth logic if needed
    return {}

@pytest.fixture
def client():
    app = create_app('testing')
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        with app.app_context():
            db.drop_all()

def test_add_food(client):
    food_data = {
        'name': 'Banana',
        'brand': 'Dole',
        'barcode': '1234567890123',
        'calories': 89,
        'protein': 1.1,
        'carbs': 22.8,
        'fat': 0.3,
        'serving_size': '100g'
    }
    response = client.post('/nutrition/api/foods', data=json.dumps(food_data), content_type='application/json', headers=get_auth_headers())
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Banana'
    assert data['calories'] == 89

def test_get_foods(client):
    response = client.get('/nutrition/api/foods', headers=get_auth_headers())
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
