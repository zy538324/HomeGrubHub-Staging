#!/usr/bin/env python3
"""
AWS RDS Security Group Setup Helper

This script helps you identify what security group rule you need to add
to allow connections to your AWS RDS instance.
"""

import requests
import json

def get_current_ip():
    """Get your current public IP address"""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        ip_data = response.json()
        return ip_data['ip']
    except Exception as e:
        print(f"❌ Failed to get current IP: {e}")
        try:
            # Fallback method
            response = requests.get('https://httpbin.org/ip', timeout=10)
            ip_data = response.json()
            return ip_data['origin']
        except Exception as e2:
            print(f"❌ Fallback IP check also failed: {e2}")
            return None

def main():
    print("🔍 AWS RDS Security Group Setup Helper")
    print("=" * 50)
    
    # Get current IP
    print("📡 Getting your current public IP address...")
    current_ip = get_current_ip()
    
    if current_ip:
        print(f"✅ Your current IP address: {current_ip}")
    else:
        print("❌ Could not determine your IP address")
        print("💡 You can find it manually at: https://whatismyipaddress.com/")
        current_ip = "YOUR_IP_ADDRESS"
    
    print("\n🔧 AWS Security Group Configuration Needed:")
    print("=" * 50)
    
    print("1. Go to AWS Console: https://console.aws.amazon.com/ec2/")
    print("2. Navigate to: Security Groups")
    print("3. Find security group: sg-08aea55cf5d9e19b4")
    print("4. Click 'Edit inbound rules'")
    print("5. Add a new rule with these settings:")
    print(f"   - Type: PostgreSQL")
    print(f"   - Protocol: TCP")
    print(f"   - Port: 5432")
    print(f"   - Source: {current_ip}/32")
    print(f"   - Description: HomeGrubHub RDS access")
    print("6. Click 'Save rules'")
    
    print("\n📋 Alternative: Allow from anywhere (less secure)")
    print("   - Source: 0.0.0.0/0 (allows from any IP)")
    print("   - Only use this for testing!")
    
    print("\n🧪 After updating the security group:")
    print("   cd g:\\Dev\\HomeGrubHub\\configs")
    print("   C:/Python312/python.exe aws_db_config.py")
    
    print(f"\n📊 Connection Details:")
    print(f"   - Host: homegrubhub.chm4wokokhxh.eu-west-2.rds.amazonaws.com")
    print(f"   - Port: 5432")
    print(f"   - Your IP: {current_ip}")
    print(f"   - Security Group: sg-08aea55cf5d9e19b4")
    print(f"   - VPC: vpc-074fb754251c08115")

if __name__ == "__main__":
    main()
