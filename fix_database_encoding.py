#!/usr/bin/env python3
"""
Script to fix database encoding for emoji support.
Run this script to update your database tables to support emojis.
"""

import os
import sys
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def fix_database_encoding():
    # Get database configuration
    db_host = os.getenv("DB_HOST")
    db_database = os.getenv("DB_DATABASE") 
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    
    if not all([db_host, db_database, db_user, db_password]):
        print("❌ Missing database environment variables.")
        print("Please ensure DB_HOST, DB_DATABASE, DB_USER, and DB_PASSWORD are set in your .env file")
        return False
    
    try:
        # Connect to MySQL server (without specifying database first)
        connection = pymysql.connect(
            host=db_host or 'localhost',
            user=db_user or 'root',
            password=db_password or '',
            charset='utf8mb4'
        )
        
        cursor = connection.cursor()
        
        print(f"✅ Connected to MySQL server at {db_host}")
        
        # First, alter the database charset
        print(f"Updating database '{db_database}' charset to utf8mb4...")
        cursor.execute(f"ALTER DATABASE `{db_database}` CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;")
        print(f"✅ Database '{db_database}' charset updated")
        
        # Now select the database
        cursor.execute(f"USE `{db_database}`;")
        
        # List of tables to update
        tables_to_fix = [
            'instagram_conversation_messages',
            'instagram_conversation_summaries', 
            'deals',
            'contacts',
            'instagram_conversations',
            'instagram_users'
        ]
        
        for table in tables_to_fix:
            try:
                print(f"Fixing encoding for table: {table}")
                cursor.execute(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
                print(f"✅ Table '{table}' encoding updated")
            except Exception as e:
                print(f"⚠️  Warning: Could not update table '{table}': {e}")
                # Continue with other tables
        
        connection.commit()
        print("\n🎉 Database encoding fix completed successfully!")
        print("Emojis and special characters should now work properly.")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nIf automatic fix failed, manually run these SQL commands in your MySQL client:")
        print(f"USE `{db_database if db_database else 'your_database_name'}`;")
        print(f"ALTER DATABASE `{db_database if db_database else 'your_database_name'}` CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;")
        
        tables = [
            'instagram_conversation_messages',
            'instagram_conversation_summaries', 
            'deals',
            'contacts',
            'instagram_conversations',
            'instagram_users'
        ]
        
        for table in tables:
            print(f"ALTER TABLE `{table}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        
        return False

if __name__ == "__main__":
    print("🔧 Starting database encoding fix for emoji support...")
    print("=" * 60)
    
    success = fix_database_encoding()
    
    if success:
        print("\n✅ All done! Your database now supports emojis and special characters.")
    else:
        print("\n❌ Automatic fix failed. Please run the SQL commands manually in your MySQL client.")
        print("After running the commands, restart your Flask application.") 