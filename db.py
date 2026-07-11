import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kothabada.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        location TEXT, -- JSON structure of coords or address
        user_type TEXT NOT NULL CHECK (user_type IN ('user', 'provider')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create properties table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        price REAL NOT NULL,
        bedrooms TEXT NOT NULL,
        bathrooms TEXT NOT NULL,
        area REAL NOT NULL,
        location TEXT NOT NULL,
        description TEXT,
        image_url TEXT DEFAULT 'https://via.placeholder.com/300x200?text=Property+Image',
        status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'rented')),
        provider_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        latitude REAL DEFAULT 27.7172,
        longitude REAL DEFAULT 85.3240,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create messages table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create bookings / tour requests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
        booking_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Initializing Database...")
    init_db()
    print("Database Initialized Successfully!")
