import boto3
import json
from botocore.exceptions import ClientError


def get_aws_db_credentials():
    """
    Get AWS RDS database credentials - Direct connection method
    Using the provided RDS endpoint and credentials
    """
    return {
        'username': 'postgres',
        'password': ')-]_peMDn?MY$gnZG.2<n73Hx5C:',
        'engine': 'postgres',
        'host': 'homegrubhub.chm4wokokhxh.eu-west-2.rds.amazonaws.com',
        'port': 5432,
        'dbname': 'homegrubhub'  # Using 'homegrubhub' as the database name
    }


def get_aws_database_uri():
    """
    Build database URI from AWS RDS credentials
    """
    try:
        # Use direct credentials (simpler approach)
        credentials = get_aws_db_credentials()
        
        # Extract database connection details
        username = credentials.get('username')
        password = credentials.get('password')
        engine = credentials.get('engine')
        host = credentials.get('host')
        port = credentials.get('port')
        dbname = credentials.get('dbname')
        
        # Build PostgreSQL connection string
        if engine == 'postgres':
            # URL encode the password to handle special characters
            from urllib.parse import quote_plus
            encoded_password = quote_plus(password)
            return f"postgresql://{username}:{encoded_password}@{host}:{port}/{dbname}"
        else:
            raise ValueError(f"Unsupported database engine: {engine}")
            
    except Exception as e:
        print(f"Failed to get AWS database URI: {e}")
        # Return None to fall back to environment variables
        return None


def test_aws_connection():
    """
    Test the AWS RDS connection
    """
    try:
        credentials = get_aws_db_credentials()
        print("✅ Successfully retrieved AWS RDS credentials:")
        print(f"   Engine: {credentials.get('engine')}")
        print(f"   Host: {credentials.get('host')}")
        print(f"   Port: {credentials.get('port')}")
        print(f"   Database: {credentials.get('dbname')}")
        print(f"   Username: {credentials.get('username')}")
        print(f"   Password: {'*' * len(credentials.get('password', ''))}")
        
        # Test actual database connection
        print("\n🔍 Testing database connection...")
        from sqlalchemy import create_engine, text
        db_uri = get_aws_database_uri()
        if db_uri:
            print(f"Connection URI: postgresql://{credentials.get('username')}:***@{credentials.get('host')}:{credentials.get('port')}/{credentials.get('dbname')}")
            
            # Try with longer timeout and connection retries
            engine = create_engine(
                db_uri,
                connect_args={
                    "connect_timeout": 60,  # 60 second timeout
                    "options": "-c statement_timeout=60000"  # 60 second statement timeout
                },
                pool_timeout=60
            )
            
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"✅ Database connection successful!")
                print(f"   PostgreSQL Version: {version}")
                
                # Test if we can list tables
                result = conn.execute(text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"))
                table_count = result.fetchone()[0]
                print(f"   Tables in database: {table_count}")
                
            return True
        else:
            print("❌ Failed to build database URI")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to AWS RDS: {e}")
        print("\n🔧 Troubleshooting info:")
        print("   - RDS Instance is publicly accessible: ✅ Yes")
        print("   - VPC: vpc-074fb754251c08115")
        print("   - Security Group: default (sg-08aea55cf5d9e19b4)")
        print("   - Availability Zone: eu-west-2b")
        print("\n💡 Next steps:")
        print("   1. Check security group inbound rules allow PostgreSQL (5432) from your IP")
        print("   2. Verify the database 'homegrubhub' exists in the RDS instance")
        print("   3. Test connection from another PostgreSQL client")
        return False


def create_database_if_not_exists():
    """
    Create the homegrubhub database if it doesn't exist
    """
    try:
        print("🔍 Checking if 'homegrubhub' database exists...")
        credentials = get_aws_db_credentials()
        
        # Connect to the default 'postgres' database first
        temp_credentials = credentials.copy()
        temp_credentials['dbname'] = 'postgres'
        
        from urllib.parse import quote_plus
        encoded_password = quote_plus(temp_credentials['password'])
        temp_uri = f"postgresql://{temp_credentials['username']}:{encoded_password}@{temp_credentials['host']}:{temp_credentials['port']}/{temp_credentials['dbname']}"
        
        from sqlalchemy import create_engine, text
        engine = create_engine(temp_uri, connect_args={"connect_timeout": 60})
        
        with engine.connect() as conn:
            # Check if homegrubhub database exists
            result = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'homegrubhub'"))
            if not result.fetchone():
                # Create the database
                conn.execute(text("COMMIT"))  # End current transaction
                conn.execute(text("CREATE DATABASE homegrubhub"))
                print("✅ Created 'homegrubhub' database")
            else:
                print("✅ Database 'homegrubhub' already exists")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create/check database: {e}")
        return False


if __name__ == "__main__":
    print("🚀 AWS RDS Connection Test")
    print("=" * 50)
    
    # First try to create database if needed
    print("📋 Step 1: Database Setup")
    create_success = create_database_if_not_exists()
    
    print("\n📋 Step 2: Connection Test")
    # Then test the connection
    connection_success = test_aws_connection()
    
    print("\n" + "=" * 50)
    if create_success and connection_success:
        print("🎉 AWS RDS is ready to use!")
        print("💡 You can now migrate your data using:")
        print("   python ../scripts/aws_rds_setup.py --full-migration")
    else:
        print("⚠️  AWS RDS setup needs attention")
        print("💡 Check the troubleshooting tips above")
