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
    
    # Seed mock data if database is empty
    cursor.execute('SELECT COUNT(*) as count FROM users')
    if cursor.fetchone()['count'] == 0:
        # Create a mock landlord user
        password_hash = generate_password_hash('password123')
        cursor.execute('''
            INSERT INTO users (first_name, last_name, phone, email, password_hash, location, user_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('Rabin', 'Thapa', '9812345678', 'rabin@provider.com', password_hash, '{"street": "Koteshwor", "city": "Kathmandu"}', 'provider'))
        
        provider_id = cursor.lastrowid
        
        # Insert 3 mock properties in Kathmandu
        cursor.execute('''
            INSERT INTO properties (title, price, bedrooms, bathrooms, area, location, description, image_url, status, provider_id, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Premium Koteshwor Flat', 
            450.0, 
            '2 Beds', 
            '1 Bath', 
            850.0, 
            'Koteshwor, Kathmandu', 
            'Beautiful flat with 24/7 water resource, rooftop view, and car parking space.', 
            'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&q=80&w=400', 
            'available', 
            provider_id, 
            27.6835, 
            85.3486
        ))
        
        cursor.execute('''
            INSERT INTO properties (title, price, bedrooms, bathrooms, area, location, description, image_url, status, provider_id, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Cozy Kalanki Room Studio', 
            300.0, 
            '1 Bed', 
            '1 Bath', 
            500.0, 
            'Kalanki, Kathmandu', 
            'Warm, newly painted room near ring road, perfect for students or single professionals.', 
            'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&q=80&w=400', 
            'available', 
            provider_id, 
            27.6938, 
            85.2817
        ))
        
        cursor.execute('''
            INSERT INTO properties (title, price, bedrooms, bathrooms, area, location, description, image_url, status, provider_id, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            'Modern Thamel Penthouse', 
            800.0, 
            '3 Beds', 
            '2 Baths', 
            1350.0, 
            'Thamel, Kathmandu', 
            'Luxury penthouse in the heart of tourist district with complete backup power, private balcony, and premium fixtures.', 
            'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&q=80&w=400', 
            'available', 
            provider_id, 
            27.7154, 
            85.3123
        ))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("Initializing Database...")
    init_db()
    print("Database Initialized Successfully!")
