from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Avg, Count, Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from ..models import Detailer, Job, Earning, Review, ServiceType
import json

class DashboardView(APIView):
    permission_classes = [IsAuthenticated] 

    action_handler = {
        "get_today_overview": '_get_today_overview',
        "get_quick_stats": '_get_quick_stats',
        "get_recent_jobs": '_get_recent_jobs',
    }   

    def get(self, request, *args, **kwargs):
        action = kwargs.get('action')
        if action not in self.action_handler:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
        handler = getattr(self, self.action_handler[action])
        return handler(request)
        

    def _get_today_overview(self, request):
        """Get today's overview data which will include the total appointments, completed jobs, pending jobs, next appointment and current job. 
        """
        today = timezone.now().date()

        # Get today's jobs
        today_jobs = Job.objects.filter(
            detailer= Detailer.objects.get(user=request.user),
            appointment_date__date=today
        )
        
        total_appointments = today_jobs.count()
        completed_jobs = today_jobs.filter(status='completed').count()
        pending_jobs = today_jobs.filter(status__in=['pending', 'accepted', 'in_progress']).count()
        
        # Get next appointment
        next_appointment = None
        next_job = today_jobs.filter(
            appointment_date__gt=timezone.now(),
            status__in=['pending', 'accepted']
        ).order_by('appointment_date').first()
        
        if next_job:
            next_appointment = {
                "id": str(next_job.id) if next_job.id else None,
                "clientName": next_job.client_name if next_job.client_name else None,
                "serviceType": next_job.service_type.name if next_job.service_type else None,
                "appointmentTime": next_job.appointment_time.strftime("%H:%M") if next_job.appointment_time else None,
                "duration": next_job.service_type.duration if next_job.service_type else None,
                "address": next_job.address if next_job.address else None,
                "vehicleInfo": f"{next_job.vehicle_make} {next_job.vehicle_model} ({next_job.vehicle_registration})" if next_job.vehicle_registration else None
            }
        
        # Get current job
        current_job = None
        in_progress_job = today_jobs.filter(status=['in_progress', 'accepted']).first()
        
        if in_progress_job:
            # Calculate progress (simplified - you might want to track actual progress)
            progress = 50  # Default progress
            current_job = {
                "id": str(in_progress_job.id),
                "clientName": in_progress_job.client_name,
                "serviceType": in_progress_job.service_type.name,
                "startTime": in_progress_job.appointment_time.strftime("%H:%M"),
                "estimatedEndTime": (datetime.combine(today, in_progress_job.appointment_time) + 
                                   timedelta(minutes=in_progress_job.service_type.duration)).strftime("%H:%M"),
                "progress": progress,
                "status": "in_progress"
            }
        
        return {
            "totalAppointments": total_appointments if total_appointments else None,
            "completedJobs": completed_jobs if completed_jobs else None,
            "pendingJobs": pending_jobs if pending_jobs else None,
            "nextAppointment": next_appointment if next_appointment else None,
            "currentJob": current_job if current_job else None
        }



    def _get_quick_stats(self, request):
        """Get quick stats for the detailer which will include the weekly earnings, monthly earnings, completed jobs this week, completed jobs this month, pending jobs count, average rating and total reviews.
        """
        detailer = Detailer.objects.get(user=request.user)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Weekly earnings
        weekly_earnings = Earning.objects.filter(
            detailer=detailer,
            payout_date__gte=week_start,
            payout_date__lte=today
        ).aggregate(total=Sum('net_amount'))['total'] or 0
        
        # Monthly earnings
        monthly_earnings = Earning.objects.filter(
            detailer=detailer,
            payout_date__gte=month_start,
            payout_date__lte=today
        ).aggregate(total=Sum('net_amount'))['total'] or 0
        
        # Completed jobs this week
        completed_jobs_this_week = Job.objects.filter(
            detailer=detailer,
            status='completed',
            appointment_date__date__gte=week_start,
            appointment_date__date__lte=today
        ).count()
        
        # Completed jobs this month
        completed_jobs_this_month = Job.objects.filter(
            detailer=detailer,
            status='completed',
            appointment_date__date__gte=month_start,
            appointment_date__date__lte=today
        ).count()
        
        # Pending jobs count
        pending_jobs_count = Job.objects.filter(
            detailer=detailer,
            status__in=['pending', 'accepted']
        ).count()
        
        # Average rating and total reviews
        reviews = Review.objects.filter(detailer=detailer)
        average_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        total_reviews = reviews.count()

        print(weekly_earnings, monthly_earnings, completed_jobs_this_week, completed_jobs_this_month, pending_jobs_count, average_rating, total_reviews)
        
        return {
            "weeklyEarnings": float(weekly_earnings) if weekly_earnings else None,
            "monthlyEarnings": float(monthly_earnings) if monthly_earnings else None,
            "completedJobsThisWeek": completed_jobs_this_week if completed_jobs_this_week else None,
            "completedJobsThisMonth": completed_jobs_this_month if completed_jobs_this_month else None,
            "pendingJobsCount": pending_jobs_count if pending_jobs_count else None,
            "averageRating": float(average_rating) if average_rating else None,
            "totalReviews": total_reviews if total_reviews else None
        }


    def _get_recent_jobs(self, request):
        """Get recent jobs data which will include the recent jobs, recent earnings and recent clients.
        """
        detailer = Detailer.objects.get(user=request.user)

        # Recent jobs (last 7 days)
        seven_days_ago = timezone.now().date() - timedelta(days=7)
        recent_jobs = Job.objects.filter(
            detailer=detailer,
            appointment_date__date__gte=seven_days_ago
        ).order_by('-appointment_date')
        
        recent_jobs_data = []
        for job in recent_jobs:
            # Get earnings for this job
            earning = Earning.objects.filter(job=job).first()
            earnings_amount = float(earning.net_amount) if earning else 0
            
            # Get rating for this job
            review = Review.objects.filter(job=job).first()
            rating = float(review.rating) if review else None
            
            recent_jobs_data.append({
                "id": str(job.id),
                "clientName": job.client_name if job.client_name else None, 
                "serviceType": job.service_type.name if job.service_type else None,
                "completedAt": job.appointment_date.isoformat() if job.appointment_date else None,
                "earnings": earnings_amount if earnings_amount else None,
                "rating": rating if rating else None,
                "status": job.status if job.status else None
            })
        
        return {
            "recentJobs": recent_jobs_data,
        }
