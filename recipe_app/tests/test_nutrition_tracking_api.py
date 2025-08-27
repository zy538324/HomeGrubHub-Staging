import pytest
from flask import json
from recipe_app.db import db, create_app

def get_auth_headers():
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
    response = client.post(
        '/nutrition/api/foods',
        data=json.dumps(food_data),
        content_type='application/json',
        headers=get_auth_headers(),
    )
    assert response.status_code in (200, 201)

def test_get_foods(client):
    response = client.get('/nutrition/api/foods', headers=get_auth_headers())
    assert response.status_code == 200
