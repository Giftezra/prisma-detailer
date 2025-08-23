from django.urls import path
from .views.authentication import AuthenticationView, CustomTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView 

urlpatterns = [
    path('onboard/<str:action>/', AuthenticationView.as_view(), name='onboard'),
    path('authentication/login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('authentication/refresh/', TokenRefreshView.as_view(), name='refresh'),
]