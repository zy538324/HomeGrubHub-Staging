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

def test_log_meal(client):
    # Add a food first
    food_data = {
        'name': 'Egg',
        'brand': 'Generic',
        'barcode': '0000000000000',
        'calories': 70,
        'protein': 6,
        'carbs': 1,
        'fat': 5,
        'serving_size': '1 large'
    }
    client.post('/api/foods', data=json.dumps(food_data), content_type='application/json', headers=get_auth_headers())
    # Log a meal
    meal_data = {
        'meal_type': 'breakfast',
        'meal_date': '2025-08-13',
        'food_ids': [1]
    }
    response = client.post('/api/meals', data=json.dumps(meal_data), content_type='application/json', headers=get_auth_headers())
    assert response.status_code == 201
    data = response.get_json()
    assert data['meal_type'] == 'breakfast'
    assert data['foods'][0]['name'] == 'Egg'
