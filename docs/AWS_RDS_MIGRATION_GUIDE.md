# AWS RDS Migration Guide for HomeGrubHub

## Overview

Your HomeGrubHub application now supports AWS RDS migration with a flexible configuration system that allows you to:
- Keep using your current Supabase database (default)
- Switch to AWS RDS when ready
- Migrate data between databases
- Easily revert if needed

## Current Setup

### Database Priority System
1. **Environment Variables (Supabase)** - *Currently Active*
2. **AWS RDS** - *Available when enabled*
3. **SQLite** - *Fallback for development*

### Files Created
- `configs/aws_db_config.py` - AWS RDS connection configuration
- `scripts/aws_rds_setup.py` - Migration utility script
- `scripts/migrate_to_aws_rds.py` - Data migration script
- Updated `configs/config.py` - Flexible database selection
- Updated `.env` - AWS RDS toggle setting

## AWS RDS Connection Details

```python
Host: homegrubhub.chm4wokokhxh.eu-west-2.rds.amazonaws.com
Port: 5432
Database: homegrubhub
Username: postgres
Password: )-]_peMDn?MY$gnZG.2<n73Hx5C:
```

## Current Issue: Connection Timeout

The AWS RDS instance is currently not accessible due to network configuration. This usually means:

### 🔧 Fix Required: Make RDS Publicly Accessible

1. **AWS RDS Console:**
   - Go to AWS RDS Console
   - Select your `homegrubhub` instance
   - Click "Modify"
   - Under "Connectivity" → Set "Public access" to "Yes"
   - Apply changes (may require reboot)

2. **Security Group Configuration:**
   - Go to EC2 Console → Security Groups
   - Find your RDS security group
   - Add inbound rule:
     - Type: PostgreSQL
     - Port: 5432
     - Source: Your IP address (get from https://whatismyipaddress.com/)

3. **Database Setup:**
   - Ensure database 'homegrubhub' exists
   - If not, create it: `CREATE DATABASE homegrubhub;`

## How to Use the Migration System

### Step 1: Test Connection (When RDS is Ready)
```bash
cd g:\Dev\HomeGrubHub
C:/Python312/python.exe scripts/aws_rds_setup.py --test
```

### Step 2: Set Up Database Schema
```bash
C:/Python312/python.exe scripts/aws_rds_setup.py --setup-schema
```

### Step 3: Migrate Your Data
```bash
C:/Python312/python.exe scripts/aws_rds_setup.py --migrate-data
```

### Step 4: Switch to AWS RDS
```bash
C:/Python312/python.exe scripts/aws_rds_setup.py --enable-aws-rds
```

### Or Do Everything at Once:
```bash
C:/Python312/python.exe scripts/aws_rds_setup.py --full-migration
```

## Manual Control

### Enable AWS RDS
Edit `.env` file:
```
USE_AWS_RDS=true
```
Then restart your application.

### Disable AWS RDS (Revert to Supabase)
Edit `.env` file:
```
USE_AWS_RDS=false
```
Then restart your application.

## Testing the System

### Current Setup Test
Your application should work normally with Supabase:
```bash
cd g:\Dev\HomeGrubHub
C:/Python312/python.exe run.py
```

### AWS Connection Test (When Ready)
```bash
cd g:\Dev\HomeGrubHub\configs
C:/Python312/python.exe aws_db_config.py
```

## Migration Features

### Data Backup
- Automatic CSV backups before migration
- Backup directory with timestamp
- Individual table exports

### Verification
- Row count verification after migration
- Data integrity checks
- Rollback capability

### Selective Migration
```bash
# Migrate specific tables only
C:/Python312/python.exe scripts/migrate_to_aws_rds.py --tables "users,recipes,meals"

# Dry run (test without changes)
C:/Python312/python.exe scripts/migrate_to_aws_rds.py --dry-run
```

## Current Status

✅ **Working Now:**
- Supabase database connection
- AWS RDS configuration prepared
- Migration scripts ready
- Flexible configuration system

⏳ **Pending (AWS RDS Network Issue):**
- AWS RDS connectivity (timeout)
- Requires security group + public access fix

🎯 **Next Steps:**
1. Fix AWS RDS network configuration
2. Test connection
3. Run migration when ready

## Safety Features

- **Non-destructive:** Original database remains unchanged
- **Reversible:** Easy switch back to Supabase
- **Backup:** Automatic data backups before migration
- **Verification:** Data integrity checks after migration

## Support

If you encounter issues:
1. Check network connectivity to AWS RDS
2. Verify security group settings
3. Ensure RDS instance is running and publicly accessible
4. Test connection with: `python configs/aws_db_config.py`

---

Your HomeGrubHub application will continue working normally with Supabase until you're ready to switch to AWS RDS!
