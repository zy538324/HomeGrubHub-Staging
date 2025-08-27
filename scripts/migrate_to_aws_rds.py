#!/usr/bin/env python3
"""
HomeGrubHub Database Migration Script
Migrate from current database to AWS RDS

Usage:
python migrate_to_aws_rds.py [--dry-run] [--tables table1,table2]
"""

import argparse
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd


def get_source_connection():
    """Get connection to source database (current Supabase)"""
    # Environment variables for source database
    postgres_host = os.environ.get('POSTGRES_HOST', 'homegrubhub.chm4wokokhxh.eu-west-2.rds.amazonaws.com')
    postgres_port = os.environ.get('POSTGRES_PORT', '5432')
    postgres_db = os.environ.get('POSTGRES_DB', 'postgres')
    postgres_user = os.environ.get('POSTGRES_USER', 'postgres.eysnqwxgrsspbnkkosoq')
    postgres_password = os.environ.get('POSTGRES_PASSWORD', ')-]_peMDn?MY$gnZG.2<n73Hx5C:@')
    
    if not postgres_password:
        raise ValueError("Source database password not found in environment variables")
    
    source_uri = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    return create_engine(source_uri)


def get_target_connection():
    """Get connection to target AWS RDS database"""
    from configs.aws_db_config import get_aws_database_uri
    
    target_uri = get_aws_database_uri()
    if not target_uri:
        raise ValueError("Could not retrieve AWS RDS connection details")
    
    return create_engine(target_uri)


def get_table_list(engine):
    """Get list of all tables in the database"""
    inspector = inspect(engine)
    return inspector.get_table_names()


def backup_table_to_csv(source_engine, table_name, backup_dir):
    """Backup a table to CSV file"""
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Export table to CSV
        backup_file = os.path.join(backup_dir, f"{table_name}.csv")
        df = pd.read_sql_table(table_name, source_engine)
        df.to_csv(backup_file, index=False)
        
        print(f"✅ Backed up table '{table_name}' to {backup_file} ({len(df)} rows)")
        return backup_file
    except Exception as e:
        print(f"❌ Failed to backup table '{table_name}': {e}")
        return None


def migrate_table_data(source_engine, target_engine, table_name, dry_run=False):
    """Migrate data from source to target table"""
    try:
        # Read data from source
        df = pd.read_sql_table(table_name, source_engine)
        
        if dry_run:
            print(f"🔍 DRY RUN: Would migrate {len(df)} rows to table '{table_name}'")
            return True
        
        # Write data to target
        df.to_sql(table_name, target_engine, if_exists='append', index=False)
        print(f"✅ Migrated {len(df)} rows to table '{table_name}'")
        return True
        
    except Exception as e:
        print(f"❌ Failed to migrate table '{table_name}': {e}")
        return False


def verify_migration(source_engine, target_engine, table_name):
    """Verify that migration was successful"""
    try:
        # Count rows in both databases
        source_count = pd.read_sql(f"SELECT COUNT(*) as count FROM {table_name}", source_engine).iloc[0]['count']
        target_count = pd.read_sql(f"SELECT COUNT(*) as count FROM {table_name}", target_engine).iloc[0]['count']
        
        if source_count == target_count:
            print(f"✅ Verification passed for '{table_name}': {source_count} rows in both databases")
            return True
        else:
            print(f"❌ Verification failed for '{table_name}': {source_count} source vs {target_count} target rows")
            return False
            
    except Exception as e:
        print(f"❌ Verification error for table '{table_name}': {e}")
        return False


def run_migration(tables_to_migrate=None, dry_run=False, backup=True):
    """Run the complete migration process"""
    print("🚀 Starting HomeGrubHub Database Migration to AWS RDS")
    print("=" * 60)
    
    try:
        # Test connections
        print("📡 Testing database connections...")
        source_engine = get_source_connection()
        target_engine = get_target_connection()
        
        # Test source connection
        with source_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Source database (Supabase) connection successful")
        
        # Test target connection
        with target_engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Target database (AWS RDS) connection successful")
        
        # Get table list
        if tables_to_migrate is None:
            tables_to_migrate = get_table_list(source_engine)
            print(f"📋 Found {len(tables_to_migrate)} tables to migrate")
        else:
            print(f"📋 Migrating specific tables: {tables_to_migrate}")
        
        print(f"Tables: {', '.join(tables_to_migrate)}")
        
        if dry_run:
            print("\n🔍 DRY RUN MODE - No actual data will be moved")
        
        # Create backup directory
        backup_dir = None
        if backup and not dry_run:
            backup_dir = f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"\n💾 Creating backups in: {backup_dir}")
        
        # Migration statistics
        successful_migrations = 0
        failed_migrations = 0
        
        # Process each table
        for table in tables_to_migrate:
            print(f"\n📦 Processing table: {table}")
            
            # Backup if requested
            if backup and not dry_run:
                backup_table_to_csv(source_engine, table, backup_dir)
            
            # Migrate data
            if migrate_table_data(source_engine, target_engine, table, dry_run):
                successful_migrations += 1
                
                # Verify migration (skip in dry run mode)
                if not dry_run:
                    if not verify_migration(source_engine, target_engine, table):
                        print(f"⚠️  Warning: Verification failed for table '{table}'")
            else:
                failed_migrations += 1
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Migration Summary")
        print(f"✅ Successful: {successful_migrations} tables")
        print(f"❌ Failed: {failed_migrations} tables")
        
        if failed_migrations == 0:
            print("🎉 Migration completed successfully!")
            if backup_dir:
                print(f"💾 Backups saved in: {backup_dir}")
        else:
            print("⚠️  Migration completed with errors. Please review failed tables.")
        
        return failed_migrations == 0
        
    except Exception as e:
        print(f"💥 Migration failed with error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Migrate HomeGrubHub database to AWS RDS')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Perform a dry run without actually migrating data')
    parser.add_argument('--tables', type=str,
                       help='Comma-separated list of specific tables to migrate')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip creating CSV backups')
    
    args = parser.parse_args()
    
    # Parse tables list
    tables_to_migrate = None
    if args.tables:
        tables_to_migrate = [table.strip() for table in args.tables.split(',')]
    
    # Run migration
    success = run_migration(
        tables_to_migrate=tables_to_migrate,
        dry_run=args.dry_run,
        backup=not args.no_backup
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
