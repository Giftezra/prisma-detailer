from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from main.models import Detailer, Availability, Job, ServiceType
from datetime import datetime, time, timedelta
import json

""" The class is used to handle all of the users availability related actions

    It is also used to handle the commuinication between the client app stack and the server
    through the internal docker container network
 """
class AvailabilityView(APIView):
    permission_classes = [AllowAny]
    action_handler = {
        'get_timeslots': 'get_timeslots',
    }

    def get(self, request, *args, **kwargs):
        action = kwargs.get('action')
        if action not in self.action_handler:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        handler = getattr(self, self.action_handler[action])
        return handler(request)
    
    def post(self, request, *args, **kwargs):
        action = kwargs.get('action')
        if action not in self.action_handler:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        handler = getattr(self, self.action_handler[action])
        return handler(request)
    
    
    def get_timeslots(self, request):
        """
        Get available time slots for detailers in a specific location
        
        Query Parameters:
        - date: YYYY-MM-DD format
        - service_duration: Duration in minutes
        - country: Country name
        - city: City name
        
        Returns:
        - slots: Array of available time slots
        """
        try:
            print('request', request.query_params)
            data = request.query_params
            date_str = data.get('date')
            service_duration = int(data.get('service_duration', 60))
            country = data.get('country')
            city = data.get('city')

            # Validate required parameters
            if not all([date_str, country, city]):
                return Response({
                    "error": "Missing required parameters: date, country, city"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Parse date
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    "error": "Invalid date format. Use YYYY-MM-DD"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get detailers in the specified location
            detailers = Detailer.objects.filter(
                city__iexact=city,
                is_active=True
            )

            if not detailers.exists():
                return Response({
                    "error": f"No active detailers found in {city}, {country} we are currently working to bring PRISMA closer to you. Please check back another time.",
                    "slots": []
                }, status=status.HTTP_200_OK)

            # Business hours: 6 AM to 9 PM (default if no availability set)
            business_start = time(6, 0)  # 6:00 AM
            business_end = time(21, 0)   # 9:00 PM
            
            # Travel time interval between jobs (30 minutes)
            travel_interval = 30
            
            # Get detailers' availability for the target date
            detailer_availability = Availability.objects.filter(
                detailer__in=detailers,
                date=target_date,
                is_available=True
            ).select_related('detailer')

            # If no specific availability is set, use default business hours
            if not detailer_availability.exists():
                # Generate all possible time slots for the day using default business hours
                all_slots = self._generate_time_slots(
                    business_start, 
                    business_end, 
                    service_duration, 
                    travel_interval
                )
            else:
                # Use detailers' set availability times
                all_slots = self._generate_slots_from_availability(
                    detailer_availability,
                    service_duration,
                    travel_interval
                )

            # Get existing appointments for all detailers on the target date
            existing_jobs = Job.objects.filter(
                detailer__in=detailers,
                appointment_date__date=target_date,
                status__in=['completed', 'accepted', 'in_progress']
            ).select_related('detailer')

            # Calculate available slots by removing booked times
            available_slots = self._calculate_available_slots(
                all_slots, 
                existing_jobs, 
                service_duration, 
                travel_interval
            )

            if not available_slots:
                return Response({
                    "error": "No available slots found",
                    "slots": []
                }, status=status.HTTP_200_OK)
            
            print('available_slots', available_slots)
            return Response({
                "slots": available_slots,
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                "error": f"Invalid parameter: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({
                "error": f"Server error: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


    def _generate_time_slots(self, start_time, end_time, service_duration, travel_interval):
        """
        Generate all possible time slots for a given day
        
        Args:
            start_time: Business start time (time object)
            end_time: Business end time (time object)
            service_duration: Service duration in minutes
            travel_interval: Travel time interval in minutes
            
        Returns:
            List of time slot dictionaries
        """
        slots = []
        current_time = start_time
        
        while current_time < end_time:
            # Calculate end time for this slot
            start_minutes = current_time.hour * 60 + current_time.minute
            end_minutes = start_minutes + service_duration
            
            # Check if this slot would extend beyond business hours
            if end_minutes > (end_time.hour * 60 + end_time.minute):
                break
                
            end_time_slot = time(end_minutes // 60, end_minutes % 60)
            
            slots.append({
                "start_time": current_time.strftime("%H:%M"),
                "end_time": end_time_slot.strftime("%H:%M"),
                "is_available": True
            })
            
            # Move to next slot (service duration + travel interval)
            next_start_minutes = end_minutes + travel_interval
            current_time = time(next_start_minutes // 60, next_start_minutes % 60)
        
        return slots
    

    def _generate_slots_from_availability(self, detailer_availability, service_duration, travel_interval):
        """
        Generate time slots based on detailers' set availability
        
        Args:
            detailer_availability: QuerySet of Availability objects
            service_duration: Service duration in minutes
            travel_interval: Travel time interval in minutes
            
        Returns:
            List of time slot dictionaries
        """
        all_slots = []
        
        for availability in detailer_availability:
            # Generate slots for this detailer's availability window
            detailer_slots = self._generate_time_slots(
                availability.start_time,
                availability.end_time,
                service_duration,
                travel_interval
            )
            
            # Add detailer info to each slot
            for slot in detailer_slots:
                slot['detailer_id'] = availability.detailer.id
                slot['detailer_name'] = availability.detailer.user.get_full_name()
            
            all_slots.extend(detailer_slots)
        
        # Remove duplicates and sort by start time
        unique_slots = []
        seen_times = set()
        
        for slot in sorted(all_slots, key=lambda x: x['start_time']):
            time_key = f"{slot['start_time']}-{slot['end_time']}"
            if time_key not in seen_times:
                seen_times.add(time_key)
                unique_slots.append(slot)
        
        return unique_slots

    def _calculate_available_slots(self, all_slots, existing_jobs, service_duration, travel_interval):
        """
        Calculate available slots by removing booked times
        
        Args:
            all_slots: List of all possible time slots
            existing_jobs: QuerySet of existing jobs
            service_duration: Service duration in minutes
            travel_interval: Travel time interval in minutes
            
        Returns:
            List of available time slots
        """
        available_slots = []
        
        for slot in all_slots:
            slot_start = datetime.strptime(slot["start_time"], "%H:%M").time()
            slot_end = datetime.strptime(slot["end_time"], "%H:%M").time()
            
            # Check if this slot conflicts with any existing job
            is_conflicting = False
            
            for job in existing_jobs:
                job_start = job.appointment_time
                
                # Calculate job end time based on service duration
                job_start_minutes = job_start.hour * 60 + job_start.minute
                job_end_minutes = job_start_minutes + job.service_type.duration
                job_end = time(job_end_minutes // 60, job_end_minutes % 60)
                
                # Add travel interval after job
                travel_end_minutes = job_end_minutes + travel_interval
                travel_end = time(travel_end_minutes // 60, travel_end_minutes % 60)
                
                # Check for overlap
                # New slot starts before existing job ends + travel time
                # AND new slot ends after existing job starts
                if (slot_start < travel_end and slot_end > job_start):
                    is_conflicting = True
                    break
            
            if not is_conflicting:
                # Create a clean slot object without detailer info for the response
                clean_slot = {
                    "start_time": slot["start_time"],
                    "end_time": slot["end_time"],
                    "is_available": True
                }
                available_slots.append(clean_slot)
        
        return available_slots
    

    def _get_detailer_availability(self, request):
        """ The method is designed to get all of the detailers availability for a year
           ARGs None
           Returns:
           - List of detailers availability for a year
          """
        pass

    def _update_detailer_availability(self, request):
        """ The method is designed to update the availability of a detailer
        """
        pass
