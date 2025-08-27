
# Add this to your config.py file:

import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Load environment variables from .env file
load_dotenv()

class Config:
    # ... your existing config ...
    
    # PostgreSQL Configuration from environment variables
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'postgresql://postgres:+#"MI@)qkk:;vur$@T>9"d5]|DzojPkh5sU4f]<`B`]!@db.eysnqwxgrsspbnkkosoq.supabase.co:5432/postgres')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'flavorio')
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '+#"MI@)qkk:;vur$@T>9"d5]|DzojPkh5sU4f]<`B`]!')
    
    @staticmethod
    def get_postgres_uri():
        """Build PostgreSQL connection URI"""
        if not Config.POSTGRES_PASSWORD:
            raise ValueError("POSTGRES_PASSWORD environment variable is required")
        
        password = quote_plus(Config.POSTGRES_PASSWORD)
        return (
            f"postgresql://{Config.POSTGRES_USER}:{password}@"
            f"{Config.POSTGRES_HOST}:{Config.POSTGRES_PORT}/"
            f"{Config.POSTGRES_DB}"
        )
    
    # Replace SQLite with PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or get_postgres_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Keep your existing configuration options...
