from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.exceptions import ValidationError
from ..serializer import CustomTokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from main.models import User, Detailer

# This simply handles the login process and returns the user data
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


""" This class is designed to handle the users registration, training, and other onboarding processes.
    Note: only the registration login is handled for now
"""
class AuthenticationView(APIView):
    permission_classes = [AllowAny]
    """ Create the action handler to route the user to the appropriate view, given the action """
    action_handler = {
        'create_new_user' : 'create_new_user',
    }

    """ Override the post method to route the user to the appropriate view, given the action """
    def post(self, request, *args, **kwargs):
        action = kwargs.get('action')
        if action not in self.action_handler:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
        
        view = getattr(self, self.action_handler[action])
        return view(request)
    
    """ Create a new user """
    def create_new_user(self, request):
        print("Received request data:", request.data)  # Debug print
        try:
            credentials = request.data.get('credentials')
            if not credentials:
                return Response({'error': 'Credentials are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate required fields
            required_fields = ['email', 'password', 'first_name', 'last_name', 'phone', 'address', 'city', 'postcode', 'country']
            missing_fields = [field for field in required_fields if not credentials.get(field)]
            if missing_fields:
                return Response({'error': f'Missing required fields: {", ".join(missing_fields)}'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.create_user(
                email=credentials.get('email'),
                password=credentials.get('password'),
                first_name=credentials.get('first_name'),
                last_name=credentials.get('last_name'),
                phone=credentials.get('phone'),
                is_detailer=True,
                username=credentials.get('email'),
            )
            user.save()
            # Create the new user profile and then create the detailer profile
            # using the user object
            profile = Detailer.objects.create(
                user=user,
                address=credentials.get('address'),
                city=credentials.get('city'),
                post_code=credentials.get('postcode'),  # Frontend sends 'postcode', not 'post_code'
                country=credentials.get('country'),
            )

            # Create the token for the user and the refresh token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Save the user and the profile, then return the token and the user data
            user.save()
            profile.save()

            return Response({
                'user' :{
                    'first_name' : user.first_name,
                    'last_name' : user.last_name,
                    'email' : user.email,
                    'phone' : user.phone,
                    'address' : profile.address,
                    'city' : profile.city,
                    'postcode' : profile.post_code,
                    'country' : profile.country,
                },
                'access' : access_token,
                'refresh' : refresh_token,
            }, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error creating user: {str(e)}")  # Debug print
            return Response({'error': f'An error occurred while creating the user: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
