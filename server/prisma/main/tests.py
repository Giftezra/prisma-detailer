from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from datetime import datetime, date, time
from main.models import Detailer, Availability, Job, ServiceType, User
import uuid

User = get_user_model()

class TimeslotsAPITestCase(APITestCase):
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1 = User.objects.create_user(
            username='detailer1',
            email='detailer1@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            phone='1234567890',
            is_detailer=True
        )
        
        self.user2 = User.objects.create_user(
            email='detailer2@test.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith',
            phone='0987654321',
            is_detailer=True
        )
        
        # Create detailers
        self.detailer1 = Detailer.objects.create(
            user=self.user1,
            country='UK',
            city='London',
            is_active=True,
        )
        
        self.detailer2 = Detailer.objects.create(
            user=self.user2,
            country='UK',
            city='London',
            is_active=True,
        )
        
        # Create service type
        self.service_type = ServiceType.objects.create(
            name='Basic Wash',
            wash_type='traditional',
            duration=60,  # 1 hour
            price=25.00
        )
        
        # Create availability for detailer1
        self.availability1 = Availability.objects.create(
            detailer=self.detailer1,
            date=date(2024, 1, 15),
            start_time=time(9, 0),  # 9:00 AM
            end_time=time(17, 0),   # 5:00 PM
            is_available=True
        )
        
        # Create availability for detailer2
        self.availability2 = Availability.objects.create(
            detailer=self.detailer2,
            date=date(2024, 1, 15),
            start_time=time(10, 0),  # 10:00 AM
            end_time=time(18, 0),    # 6:00 PM
            is_available=True
        )

    def test_get_timeslots_success(self):
        """Test successful timeslots retrieval"""
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'country': 'UK',
            'city': 'London'
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('slots', response.data)
        self.assertIn('total_slots', response.data)
        self.assertIsInstance(response.data['slots'], list)
        
        # Should have available slots
        self.assertGreater(len(response.data['slots']), 0)
        
        # Check slot format
        if response.data['slots']:
            slot = response.data['slots'][0]
            self.assertIn('start_time', slot)
            self.assertIn('end_time', slot)
            self.assertIn('is_available', slot)
            self.assertTrue(slot['is_available'])

    def test_get_timeslots_no_detailers(self):
        """Test timeslots when no detailers exist in location"""
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'country': 'UK',
            'city': 'Manchester'  # Different city
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('error', response.data)
        self.assertIn('slots', response.data)
        self.assertEqual(response.data['slots'], [])

    def test_get_timeslots_with_existing_job(self):
        """Test timeslots when there's an existing job"""
        # Create an existing job
        existing_job = Job.objects.create(
            service_type=self.service_type,
            booking_reference=uuid.uuid4(),
            client_name='Test Client',
            client_phone='1234567890',
            vehicle_registration='ABC123',
            vehicle_make='Toyota',
            vehicle_model='Camry',
            vehicle_color='White',
            address='123 Test St',
            city='London',
            post_code='SW1A 1AA',
            country='UK',
            appointment_date=datetime(2024, 1, 15, 14, 0),  # 2:00 PM
            appointment_time=time(14, 0),
            detailer=self.detailer1
        )
        
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'country': 'UK',
            'city': 'London'
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('slots', response.data)
        
        # Check that 2:00 PM slot is not available (job + travel time)
        slots = response.data['slots']
        conflicting_slots = [slot for slot in slots if slot['start_time'] == '14:00']
        self.assertEqual(len(conflicting_slots), 0)

    def test_get_timeslots_missing_parameters(self):
        """Test timeslots with missing required parameters"""
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        
        # Test missing date
        params = {
            'service_duration': '60',
            'country': 'UK',
            'city': 'London'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test missing country
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'city': 'London'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test missing city
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'country': 'UK'
        }
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_timeslots_invalid_date(self):
        """Test timeslots with invalid date format"""
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        params = {
            'date': 'invalid-date',
            'service_duration': '60',
            'country': 'UK',
            'city': 'London'
        }
        
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_get_timeslots_default_business_hours(self):
        """Test timeslots when no availability is set (uses default business hours)"""
        # Delete all availability records
        Availability.objects.all().delete()
        
        url = reverse('availability', kwargs={'action': 'get_timeslots'})
        params = {
            'date': '2024-01-15',
            'service_duration': '60',
            'country': 'UK',
            'city': 'London'
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('slots', response.data)
        
        # Should still have slots (using default 6 AM - 9 PM)
        self.assertGreater(len(response.data['slots']), 0)

    def test_get_timeslots_different_service_duration(self):
        """Test timeslots with different service duration"""
        url = '/api/v1/availability/get_timeslots/'
        params = {
            'date': '2024-01-15',
            'service_duration': '120',  # 2 hours
            'country': 'UK',
            'city': 'London'
        }
        
        response = self.client.get(url, params)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('slots', response.data)
        
        # Check that slots have correct duration
        if response.data['slots']:
            slot = response.data['slots'][0]
            start_time = datetime.strptime(slot['start_time'], '%H:%M')
            end_time = datetime.strptime(slot['end_time'], '%H:%M')
            duration_minutes = (end_time - start_time).seconds // 60
            self.assertEqual(duration_minutes, 120)
