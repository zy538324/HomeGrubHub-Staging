import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

    # Auth0 Configuration
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL')
    AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')

    # Image Storage Configuration
    IMAGE_STORAGE_TYPE = os.environ.get('IMAGE_STORAGE_TYPE', 'filesystem')  # 'filesystem' or 'database'
    IMAGE_STORAGE_PATH = os.environ.get('IMAGE_STORAGE_PATH', 'D:/HomeGrubHub_Images')
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024))  # 5MB default
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}

    # Database Configuration - Priority: Environment > AWS RDS > SQLite
    @staticmethod
    def get_database_uri():
        logger = logging.getLogger(__name__)

        # Highest priority: explicit DATABASE_URL override
        explicit_url = os.environ.get('DATABASE_URL')
        if explicit_url:
            logger.info("Using DATABASE_URL override for database connection")
            return explicit_url

        # Check if AWS RDS should be used (via environment variable)
        use_aws_rds = os.environ.get('USE_AWS_RDS', 'false').lower() == 'true'

        if use_aws_rds:
            try:
                from .aws_db_config import get_aws_database_uri
                aws_uri = get_aws_database_uri()
                if aws_uri:
                    logger.info("Using AWS RDS database connection")
                    return aws_uri
            except Exception as e:
                logger.warning(
                    "AWS RDS connection failed, falling back to environment variables: %s",
                    e,
                )

        # Next priority: individual Postgres environment variables
        postgres_host = os.environ.get('POSTGRES_HOST')
        postgres_port = os.environ.get('POSTGRES_PORT')
        postgres_db = os.environ.get('POSTGRES_DB')
        postgres_user = os.environ.get('POSTGRES_USER')
        postgres_password = os.environ.get('POSTGRES_PASSWORD')

        if all([postgres_host, postgres_port, postgres_db, postgres_user, postgres_password]):
            logger.info("Using environment variable database connection")
            return f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'

        # Final fallback to SQLite for development
        logger.warning("Using SQLite fallback for development")
        return 'sqlite:///recipes.db'

    # Set the database URI using the priority system
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy Engine Configuration for better connection handling
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {}
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,  # Test connections before use
            'pool_recycle': 300,    # Recycle connections every 5 minutes
            'pool_timeout': 20,     # Wait up to 20 seconds for a connection
            'max_overflow': 0,      # Don't allow overflow connections
            'pool_size': 10,        # Number of connections to maintain
            'connect_args': {
                'connect_timeout': 10,  # Connection timeout in seconds
                'application_name': 'HomeGrubHub'  # For connection identification
            }
        }

    # SendGrid Configuration
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
    SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@homegrubhub.co.uk')
    SENDGRID_FROM_NAME = os.environ.get('SENDGRID_FROM_NAME', 'HomeGrubHub')

    # SendGrid template IDs (optional - for using SendGrid templates)
    SENDGRID_REGISTRATION_TEMPLATE_ID = os.environ.get('SENDGRID_REGISTRATION_TEMPLATE_ID')
    SENDGRID_PASSWORD_RESET_TEMPLATE_ID = os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID')
    SENDGRID_WELCOME_TEMPLATE_ID = os.environ.get('SENDGRID_WELCOME_TEMPLATE_ID')
    SENDGRID_BILLING_TEMPLATE_ID = os.environ.get('SENDGRID_BILLING_TEMPLATE_ID')


# Required settings for startup validation
REQUIRED_SETTINGS = [
    'SECRET_KEY',
    'STRIPE_PUBLISHABLE_KEY',
    'STRIPE_SECRET_KEY',
    'STRIPE_WEBHOOK_SECRET',
    'AUTH0_CLIENT_ID',
    'AUTH0_CLIENT_SECRET',
    'AUTH0_DOMAIN',
    'AUTH0_CALLBACK_URL',
    'AUTH0_AUDIENCE',
    'SENDGRID_API_KEY',
]


def validate_config(config_obj=None):
    config_obj = config_obj or Config
    getter = config_obj.get if isinstance(config_obj, dict) else getattr
    missing = [key for key in REQUIRED_SETTINGS if not getter(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

