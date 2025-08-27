from rest_framework import serializers
from .models import User, Detailer, ServiceType, TimeSlot, Job, Earning, BankAccount, Review, TrainingRecord, Availability
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import ValidationError
from .utils import get_full_media_url


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class DetailerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detailer
        fields = '__all__'

class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = '__all__'

class TimeSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeSlot
        fields = '__all__'

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = '__all__'

class EarningSerializer(serializers.ModelSerializer):
    class Meta:
        model = Earning
        fields = '__all__'

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = '__all__'

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        try:
            detailer = Detailer.objects.get(user=user)
        except Detailer.DoesNotExist:
            detailer = None

        data.update({
            'user': {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': getattr(user, 'phone', None),
                'address': detailer.address if detailer else None,
                'city': detailer.city if detailer else None,
                'post_code': detailer.post_code if detailer else None,
                'country': detailer.country if detailer else None,
                'image': get_full_media_url(user.image.url) if getattr(user, 'image', None) else None,
            }
        })
        return data
