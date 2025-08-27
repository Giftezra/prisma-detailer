from django.urls import path
from .views.authentication import AuthenticationView, CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView 
from .views.availability import AvailabilityView    
from .views.dashboard import DashboardView

urlpatterns = [
    path('onboard/<str:action>/', AuthenticationView.as_view(), name='onboard'),
    path('authentication/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('authentication/refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('availability/<str:action>/', AvailabilityView.as_view(), name='availability'),
    path('dashboard/<str:action>/', DashboardView.as_view(), name='dashboard'),
]