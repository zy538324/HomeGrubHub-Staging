import pytest
from recipe_app.db import db
from recipe_app import create_app
from flask import json

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

def test_progress_chart_gating(client):
    # Simulate Free tier
    with client.session_transaction() as sess:
        sess['user_tier'] = 'Free'
        sess['_user_id'] = 1
    response = client.get('/nutrition/progress-chart-extended?days=30')
    assert response.status_code == 403
    assert b'Feature not available for your tier' in response.data

    # Simulate Home tier
    with client.session_transaction() as sess:
        sess['user_tier'] = 'Home'
        sess['_user_id'] = 1
    response = client.get('/nutrition/progress-chart-extended?days=30')
    assert response.status_code == 200
