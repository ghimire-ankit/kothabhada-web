from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import sqlite3
from functools import wraps
from geopy.geocoders import Nominatim
from db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize geocoder
try:
    geolocator = Nominatim(user_agent="kothabada-modern-app")
except Exception as e:
    geolocator = None
    print(f"Error initializing Geopy Geolocator: {e}")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login_view'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def login_view():
    if 'user' in session:
        user_type = session['user'].get('user_type', 'user')
        if user_type == 'provider':
            return redirect(url_for('provider_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return render_template('login.html')

@app.route('/check-email', methods=['POST'])
def check_email():
    data = request.json
    email = data.get('email')
    user_type = data.get('user_type', 'user')
    
    if not email:
        return jsonify({'exists': False, 'error': 'Email is required'})
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND user_type = ?', (email, user_type)).fetchone()
    conn.close()
    
    if user:
        return jsonify({'exists': True})
    return jsonify({'exists': False})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type', 'user')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password are required'})
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ? AND user_type = ?', (email, user_type)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        user_data = {
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'email': user['email'],
            'phone': user['phone'],
            'user_type': user['user_type'],
            'location': user['location']
        }
        session['user'] = user_data
        redirect_url = '/provider-dashboard' if user_type == 'provider' else '/user-dashboard'
        return jsonify({'success': True, 'redirect_url': redirect_url})
        
    return jsonify({'success': False, 'message': 'Invalid email or password'})

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    phone = data.get('phone')
    email = data.get('email')
    password = data.get('password')
    location = data.get('location', {})
    user_type = data.get('user_type', 'user')
    
    if not all([first_name, last_name, phone, email, password]):
        return jsonify({'success': False, 'message': 'All fields are required'})
    
    # Process location
    location_data = {}
    if location and location.get('manual'):
        location_data = {
            'street': location.get('street'),
            'city': location.get('city'),
            'formatted_address': f"{location.get('street')}, {location.get('city')}"
        }
    else:
        # GPS location
        try:
            latitude = location.get('latitude') if location else None
            longitude = location.get('longitude') if location else None
            if latitude and longitude and geolocator:
                location_obj = geolocator.reverse(f"{latitude}, {longitude}")
                if location_obj:
                    location_data = {
                        'latitude': latitude,
                        'longitude': longitude,
                        'formatted_address': location_obj.address
                    }
                else:
                    location_data = {'latitude': latitude, 'longitude': longitude, 'formatted_address': 'GPS Location'}
            else:
                location_data = {'formatted_address': 'Unknown Location'}
        except Exception as e:
            print(f"Error resolving GPS address: {e}")
            location_data = {'formatted_address': 'GPS Coordinates'}

    password_hash = generate_password_hash(password)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO users (first_name, last_name, phone, email, password_hash, location, user_type) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (first_name, last_name, phone, email, password_hash, json.dumps(location_data), user_type)
        )
        user_id = cursor.lastrowid
        conn.commit()
        
        user_data = {
            'id': user_id,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'user_type': user_type,
            'location': json.dumps(location_data)
        }
        session['user'] = user_data
        redirect_url = '/provider-dashboard' if user_type == 'provider' else '/user-dashboard'
        return jsonify({'success': True, 'redirect_url': redirect_url})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'An account with this email/phone already exists.'})
    except Exception as e:
        print(f"Registration Error: {e}")
        return jsonify({'success': False, 'message': f'Failed to register: {str(e)}'})
    finally:
        conn.close()

@app.route('/user-dashboard')
@login_required
def user_dashboard():
    user = session.get('user', {})
    if user.get('user_type') != 'user':
        return redirect(url_for('provider_dashboard'))
    
    conn = get_db_connection()
    # Fetch all available properties
    properties = conn.execute('SELECT p.*, u.first_name || " " || u.last_name as provider_name, u.phone as provider_phone FROM properties p JOIN users u ON p.provider_id = u.id WHERE p.status = "available" ORDER BY p.id DESC').fetchall()
    
    # Fetch my bookings
    bookings = conn.execute('''
        SELECT b.*, p.title as property_title, p.price as property_price, p.location as property_location, p.image_url as property_image, u.first_name || " " || u.last_name as provider_name, u.phone as provider_phone
        FROM bookings b
        JOIN properties p ON b.property_id = p.id
        JOIN users u ON p.provider_id = u.id
        WHERE b.user_id = ?
        ORDER BY b.id DESC
    ''', (user.get('id'),)).fetchall()
    
    # Fetch my conversations
    messages = conn.execute('''
        SELECT m.*, p.title as property_title, u.first_name || " " || u.last_name as counterparty_name
        FROM messages m
        JOIN properties p ON m.property_id = p.id
        JOIN users u ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
        GROUP BY m.property_id, u.id
        ORDER BY m.id DESC
    ''', (user.get('id'), user.get('id'), user.get('id'))).fetchall()
    
    conn.close()
    
    return render_template('user_dashboard.html', user=user, properties=properties, bookings=bookings, messages=messages)

@app.route('/provider-dashboard')
@login_required
def provider_dashboard():
    user = session.get('user', {})
    if user.get('user_type') != 'provider':
        return redirect(url_for('user_dashboard'))
    
    conn = get_db_connection()
    # Fetch listed properties
    properties = conn.execute('SELECT * FROM properties WHERE provider_id = ? ORDER BY id DESC', (user.get('id'),)).fetchall()
    
    # Fetch booking requests
    bookings = conn.execute('''
        SELECT b.*, p.title as property_title, p.price as property_price, u.first_name || " " || u.last_name as user_name, u.phone as user_phone
        FROM bookings b
        JOIN properties p ON b.property_id = p.id
        JOIN users u ON b.user_id = u.id
        WHERE p.provider_id = ?
        ORDER BY b.id DESC
    ''', (user.get('id'),)).fetchall()
    
    # Fetch customer messages
    messages = conn.execute('''
        SELECT m.*, p.title as property_title, u.first_name || " " || u.last_name as counterparty_name, u.phone as counterparty_phone
        FROM messages m
        JOIN properties p ON m.property_id = p.id
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        GROUP BY m.property_id, m.sender_id
        ORDER BY m.id DESC
    ''', (user.get('id'),)).fetchall()
    
    conn.close()
    
    return render_template('provider_dashboard.html', user=user, properties=properties, bookings=bookings, messages=messages)

@app.route('/property', methods=['POST'])
@login_required
def add_property():
    user = session.get('user', {})
    if user.get('user_type') != 'provider':
        return jsonify({'success': False, 'message': 'Only providers can add properties'})
    
    data = request.json
    title = data.get('title')
    price = data.get('price')
    bedrooms = data.get('bedrooms')
    bathrooms = data.get('bathrooms')
    area = data.get('area')
    location = data.get('location')
    description = data.get('description', '')
    image_url = data.get('image_url') or 'https://via.placeholder.com/300x200?text=Property+Image'
    status = data.get('status', 'available')
    latitude = data.get('latitude') or 27.7172
    longitude = data.get('longitude') or 85.3240
    
    if not all([title, price, bedrooms, bathrooms, area, location]):
        return jsonify({'success': False, 'message': 'All required fields must be supplied'})
        
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO properties (title, price, bedrooms, bathrooms, area, location, description, image_url, status, provider_id, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (title, float(price), bedrooms, bathrooms, float(area), location, description, image_url, status, user.get('id'), float(latitude), float(longitude))
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error adding property: {e}")
        return jsonify({'success': False, 'message': f'Failed to add property: {str(e)}'})
    finally:
        conn.close()

@app.route('/property/<int:property_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def property_operations(property_id):
    user = session.get('user', {})
    
    conn = get_db_connection()
    property_data = conn.execute('SELECT * FROM properties WHERE id = ?', (property_id,)).fetchone()
    
    if not property_data:
        conn.close()
        return jsonify({'success': False, 'message': 'Property not found'})
        
    if request.method == 'GET':
        data = dict(property_data)
        conn.close()
        return jsonify(data)
        
    elif request.method == 'PUT':
        if property_data['provider_id'] != user.get('id'):
            conn.close()
            return jsonify({'success': False, 'message': 'Unauthorized'})
            
        data = request.json
        try:
            conn.execute('''
                UPDATE properties 
                SET title = ?, price = ?, bedrooms = ?, bathrooms = ?, area = ?, location = ?, description = ?, image_url = ?, status = ?, latitude = ?, longitude = ?
                WHERE id = ?
            ''', (
                data.get('title'),
                float(data.get('price')),
                data.get('bedrooms'),
                data.get('bathrooms'),
                float(data.get('area')),
                data.get('location'),
                data.get('description', ''),
                data.get('image_url') or property_data['image_url'],
                data.get('status', 'available'),
                float(data.get('latitude', 27.7172)),
                float(data.get('longitude', 85.3240)),
                property_id
            ))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': f'Update failed: {str(e)}'})
            
    elif request.method == 'DELETE':
        if property_data['provider_id'] != user.get('id'):
            conn.close()
            return jsonify({'success': False, 'message': 'Unauthorized'})
            
        try:
            conn.execute('DELETE FROM properties WHERE id = ?', (property_id,))
            conn.commit()
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': f'Delete failed: {str(e)}'})

@app.route('/booking', methods=['POST'])
@login_required
def create_booking():
    user = session.get('user', {})
    if user.get('user_type') != 'user':
        return jsonify({'success': False, 'message': 'Only seekers/users can request bookings/tours'})
        
    data = request.json
    property_id = data.get('property_id')
    booking_date = data.get('booking_date')
    
    if not property_id or not booking_date:
        return jsonify({'success': False, 'message': 'Property ID and date are required'})
        
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO bookings (user_id, property_id, booking_date, status) VALUES (?, ?, ?, "pending")',
            (user.get('id'), property_id, booking_date)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/booking/<int:booking_id>/status', methods=['POST'])
@login_required
def update_booking_status(booking_id):
    user = session.get('user', {})
    data = request.json
    new_status = data.get('status') # 'approved' or 'rejected'
    
    if new_status not in ['approved', 'rejected']:
        return jsonify({'success': False, 'message': 'Invalid status'})
        
    conn = get_db_connection()
    booking = conn.execute('''
        SELECT b.*, p.provider_id 
        FROM bookings b 
        JOIN properties p ON b.property_id = p.id 
        WHERE b.id = ?
    ''', (booking_id,)).fetchone()
    
    if not booking:
        conn.close()
        return jsonify({'success': False, 'message': 'Booking not found'})
        
    if booking['provider_id'] != user.get('id'):
        conn.close()
        return jsonify({'success': False, 'message': 'Unauthorized to change this booking'})
        
    try:
        conn.execute('UPDATE bookings SET status = ? WHERE id = ?', (new_status, booking_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/message', methods=['POST'])
@login_required
def send_message():
    user = session.get('user', {})
    data = request.json
    receiver_id = data.get('receiver_id')
    property_id = data.get('property_id')
    message_text = data.get('message')
    
    if not all([receiver_id, property_id, message_text]):
        return jsonify({'success': False, 'message': 'Incomplete message data'})
        
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO messages (sender_id, receiver_id, property_id, message) VALUES (?, ?, ?, ?)',
            (user.get('id'), receiver_id, property_id, message_text)
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/messages/<int:counterparty_id>/<int:property_id>', methods=['GET'])
@login_required
def get_messages(counterparty_id, property_id):
    user = session.get('user', {})
    conn = get_db_connection()
    messages = conn.execute('''
        SELECT m.*, 
               sender.first_name || " " || sender.last_name as sender_name,
               receiver.first_name || " " || receiver.last_name as receiver_name
        FROM messages m
        JOIN users sender ON m.sender_id = sender.id
        JOIN users receiver ON m.receiver_id = receiver.id
        WHERE m.property_id = ? AND 
              ((m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?))
        ORDER BY m.id ASC
    ''', (property_id, user.get('id'), counterparty_id, counterparty_id, user.get('id'))).fetchall()
    
    data = [dict(m) for m in messages]
    conn.close()
    return jsonify(data)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
    session.pop('user', None)
    if request.method == 'POST':
        return jsonify({'success': True})
    return redirect(url_for('login_view'))

if __name__ == '__main__':
    app.run(debug=True)