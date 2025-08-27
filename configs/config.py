import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_live_51RQlonAJtC1Fz22fXESr7pBtCfdXYMirGnN0nKIMY0agY7jmAtWUZX7WKOngaKzTCqdGq55RefUsf7Po91qbkby100oE3PBkJF')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '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')
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    # Auth0 Configuration
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID', 'bBmSCBCAZkPQSWKoZ6zzzvFPnGoB06oy')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET', 'tggLjE53v8SRZWTP-WUs2qUDymj2kOU2kowqXRKw2rKXg04hVmk0q1PDYAJIw2kB')
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN', 'flavorio.uk.auth0.com')
    AUTH0_CALLBACK_URL = os.environ.get('AUTH0_CALLBACK_URL', 'https://homegrubhub.co.uk/callback')
    AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE', 'homegrubhub-api')
    
    # Image Storage Configuration
    IMAGE_STORAGE_TYPE = os.environ.get('IMAGE_STORAGE_TYPE', 'filesystem')  # 'filesystem' or 'database'
    IMAGE_STORAGE_PATH = os.environ.get('IMAGE_STORAGE_PATH', 'D:/HomeGrubHub_Images')
    MAX_IMAGE_SIZE = int(os.environ.get('MAX_IMAGE_SIZE', 5 * 1024 * 1024))  # 5MB default
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    
    # Database Configuration - Priority: Environment > AWS RDS > SQLite
    @staticmethod
    def get_database_uri():
        # Check if AWS RDS should be used (via environment variable)
        use_aws_rds = os.environ.get('USE_AWS_RDS', 'false').lower() == 'true'
        
        if use_aws_rds:
            try:
                from .aws_db_config import get_aws_database_uri
                aws_uri = get_aws_database_uri()
                if aws_uri:
                    print("✅ Using AWS RDS database connection")
                    return aws_uri
            except Exception as e:
                print(f"⚠️  AWS RDS connection failed, falling back to environment variables: {e}")
        
        # Primary: Use environment variables (current Supabase setup)
        postgres_host = os.environ.get('POSTGRES_HOST', 'aws-0-eu-west-2.pooler.supabase.com')
        postgres_port = os.environ.get('POSTGRES_PORT', '6543')
        postgres_db = os.environ.get('POSTGRES_DB', 'postgres')
        postgres_user = os.environ.get('POSTGRES_USER', 'postgres.eysnqwxgrsspbnkkosoq')
        postgres_password = os.environ.get('POSTGRES_PASSWORD', 'Unfitted6-Outsider-Dividable-Trickery-Wrinkly-Helium-Affluent-Providing-Garland-Outshine')
        
        if postgres_password:
            print("✅ Using environment variable database connection (Supabase)")
            return f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
        else:
            # Final fallback to SQLite for development
            print("⚠️  Using SQLite fallback for development")
            return os.environ.get('DATABASE_URL', 'sqlite:///recipes.db')
    
    # Set the database URI using the priority system
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # SQLAlchemy Engine Configuration for better connection handling
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
    SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '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')
    SENDGRID_FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@homegrubhub.co.uk')
    SENDGRID_FROM_NAME = os.environ.get('SENDGRID_FROM_NAME', 'HomeGrubHub')
    
    # SendGrid template IDs (optional - for using SendGrid templates)
    SENDGRID_REGISTRATION_TEMPLATE_ID = os.environ.get('SENDGRID_REGISTRATION_TEMPLATE_ID')
    SENDGRID_PASSWORD_RESET_TEMPLATE_ID = os.environ.get('SENDGRID_PASSWORD_RESET_TEMPLATE_ID')
    SENDGRID_WELCOME_TEMPLATE_ID = os.environ.get('SENDGRID_WELCOME_TEMPLATE_ID')
    SENDGRID_BILLING_TEMPLATE_ID = os.environ.get('SENDGRID_BILLING_TEMPLATE_ID')
    