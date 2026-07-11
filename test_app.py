import unittest
import json
import os
from app import app
from db import init_db, get_db_connection

class TestKothaBhadaRebuild(unittest.TestCase):
    def setUp(self):
        # Set up a testing config
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        
        # Reset the database for clean testing
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS bookings")
        cursor.execute("DROP TABLE IF EXISTS messages")
        cursor.execute("DROP TABLE IF EXISTS properties")
        cursor.execute("DROP TABLE IF EXISTS users")
        conn.commit()
        conn.close()
        
        init_db()
        
    def test_complete_flow(self):
        print("\n--- Starting End-to-End Programmatic Test ---")
        
        # 1. Register Landlord / Provider
        print("Testing: Register Landlord 'Rabin Thapa'")
        res = self.client.post('/register', json={
            'first_name': 'Rabin',
            'last_name': 'Thapa',
            'phone': '9812345678',
            'email': 'rabin@provider.com',
            'password': 'password123',
            'user_type': 'provider',
            'location': {'manual': True, 'street': 'Ward 32', 'city': 'Kathmandu'}
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'], f"Failed registration: {data.get('message')}")
        self.assertEqual(data['redirect_url'], '/provider-dashboard')
        print("Success: Landlord registered!")

        # 2. Login Landlord
        print("Testing: Login Landlord")
        res = self.client.post('/login', json={
            'email': 'rabin@provider.com',
            'password': 'password123',
            'user_type': 'provider'
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Landlord logged in!")

        # 3. Add Property Listing
        print("Testing: Add Property Listing")
        res = self.client.post('/property', json={
            'title': 'Deluxe Kathmandu Apartment',
            'price': 650.0,
            'bedrooms': '2',
            'bathrooms': '2',
            'area': 1200.0,
            'location': 'Koteshwor, Kathmandu',
            'description': 'Spacious fully furnished rooms with parking.',
            'image_url': 'https://example.com/apartment.jpg',
            'status': 'available',
            'latitude': 27.6835,
            'longitude': 85.3486
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Property listing created!")

        # 4. Register a Seeker / User
        print("Testing: Register Seeker 'Ankit Ghimire'")
        res = self.client.post('/register', json={
            'first_name': 'Ankit',
            'last_name': 'Ghimire',
            'phone': '9845678901',
            'email': 'ankit@seeker.com',
            'password': 'password123',
            'user_type': 'user',
            'location': {'manual': True, 'street': 'Ward 10', 'city': 'Kathmandu'}
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['redirect_url'], '/user-dashboard')
        print("Success: Seeker registered!")

        # 5. Fetch all properties from Seeker dashboard context
        print("Testing: View user-dashboard to inspect properties")
        res = self.client.get('/user-dashboard')
        self.assertEqual(res.status_code, 200)
        # Note: Since the test client handles session cookie automatically, they are logged in as seekver now
        print("Success: User dashboard loads property feeds correctly!")

        # Find property ID by querying DB directly for test workflow
        conn = get_db_connection()
        prop = conn.execute("SELECT id, provider_id FROM properties WHERE title = ?", ('Deluxe Kathmandu Apartment',)).fetchone()
        self.assertIsNotNone(prop)
        prop_id = prop['id']
        landlord_id = prop['provider_id']
        
        seeker_id = conn.execute("SELECT id FROM users WHERE email = 'ankit@seeker.com'").fetchone()['id']
        conn.close()

        # 6. Book Tour
        print("Testing: Request visit date / Tour booking")
        res = self.client.post('/booking', json={
            'property_id': prop_id,
            'booking_date': '2026-07-15'
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Tour booking requested!")

        # 7. Write Chat Message
        print("Testing: Send seeker message to landlord")
        res = self.client.post('/message', json={
            'receiver_id': landlord_id,
            'property_id': prop_id,
            'message': 'Hi Rabin, is the room still available?'
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Message sent!")

        # 8. Retrieve message conversation from customer dashboard views
        print("Testing: Get conversation messages history")
        res = self.client.get(f'/messages/{landlord_id}/{prop_id}')
        data = json.loads(res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['message'], 'Hi Rabin, is the room still available?')
        print("Success: Chat history parsed correctly!")

        # 9. Login as Landlord again to accept the booking and send reply
        print("Testing: Logging in back as Landlord to process actions")
        res = self.client.post('/login', json={
            'email': 'rabin@provider.com',
            'password': 'password123',
            'user_type': 'provider'
        })
        
        # Get booking ID from DB
        conn = get_db_connection()
        booking = conn.execute("SELECT id FROM bookings WHERE user_id = ?", (seeker_id,)).fetchone()
        self.assertIsNotNone(booking)
        booking_id = booking['id']
        conn.close()

        # 10. Landlord approves booking
        print("Testing: Landlord approves seeker appointment")
        res = self.client.post(f'/booking/{booking_id}/status', json={'status': 'approved'})
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Booking approved!")

        # 11. Landlord reply to seeker chat
        print("Testing: Landlord replies to seeker message thread")
        res = self.client.post('/message', json={
            'receiver_id': seeker_id,
            'property_id': prop_id,
            'message': 'Yes, you can visit tomorrow at 2 PM.'
        })
        data = json.loads(res.data)
        self.assertTrue(data['success'])
        print("Success: Landlord message reply successfully delivered!")

        # Final DB Validation
        conn = get_db_connection()
        booking_status = conn.execute("SELECT status FROM bookings WHERE id = ?", (booking_id,)).fetchone()['status']
        self.assertEqual(booking_status, 'approved')
        messages_count = conn.execute("SELECT count(*) as count FROM messages WHERE property_id = ?", (prop_id,)).fetchone()['count']
        self.assertEqual(messages_count, 2)
        conn.close()
        
        print("\n--- End-to-End Programmatic Test Passed! SUCCESS ---")

if __name__ == '__main__':
    unittest.main()
