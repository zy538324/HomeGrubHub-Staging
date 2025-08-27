import os

# Auth0 configuration values loaded from environment
AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')  # Replace with your Auth0 domain
AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL')
AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')  # Optional, for API access

