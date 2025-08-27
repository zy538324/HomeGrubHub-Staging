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

To override the database connection entirely, set `DATABASE_URL`. This takes
precedence over other database settings and is useful for local testing, e.g.:

```
export DATABASE_URL=sqlite:///test.db
```

If neither `DATABASE_URL` nor the PostgreSQL variables are provided, the
application falls back to a local SQLite database for development.

## Testing

The test suite configures the above variables automatically and uses a
temporary SQLite database. Running `pytest` locally therefore requires no
additional setup, but any provided environment variables will still take
precedence.

