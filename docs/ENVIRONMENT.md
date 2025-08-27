# Environment Configuration

The application reads all secrets from environment variables. Set the following
variables before starting the server:

- `SECRET_KEY`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_DOMAIN`
- `AUTH0_CALLBACK_URL`
- `AUTH0_AUDIENCE`
- `SENDGRID_API_KEY`

For PostgreSQL deployments, also provide:

- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
