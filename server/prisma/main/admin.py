from django.contrib import admin
from django import forms
from .models import ServiceType, Job, Earning, BankAccount, Review, TrainingRecord, Detailer, User, TimeSlot, Availability

# Custom form for ServiceType to handle description as textarea
class ServiceTypeForm(forms.ModelForm):
    description_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'cols': 50}),
        help_text="Enter each service item on a new line. These will be stored as an array.",
        required=False
    )
    
    class Meta:
        model = ServiceType
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Convert JSON array back to text for editing
            if self.instance.description:
                self.fields['description_text'].initial = '\n'.join(self.instance.description)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Convert textarea input to JSON array
        description_text = self.cleaned_data.get('description_text', '')
        if description_text:
            # Split by newlines and filter out empty lines
            description_array = [line.strip() for line in description_text.split('\n') if line.strip()]
            instance.description = description_array
        else:
            instance.description = []
        
        if commit:
            instance.save()
        return instance
    
@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    form = ServiceTypeForm
    list_display = ('name', 'description', 'wash_type', 'duration', 'price')
    search_fields = ('name', 'description')
    list_filter = ('wash_type',)

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'booking_reference', 'client_name', 'vehicle_registration', 'address', 'city', 'post_code','appointment_date','detailer')
    search_fields = ('booking_reference', 'client_name', 'vehicle_registration',)
    list_filter = ('booking_reference', 'client_name')

@admin.register(Earning)
class EarningAdmin(admin.ModelAdmin):
    list_display = ('detailer', 'gross_amount', 'commission', 'net_amount', 'tip_amount', 'payout_date', 'payment_status')
    search_fields = ('detailer__user__first_name', 'detailer__user__last_name', 'job__booking_reference', 'job__client_name', 'job__vehicle_registration')
    list_filter = ('payment_status', 'payout_date')

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('detailer', 'account_name', 'account_number', 'sort_code', 'bank_name')
    search_fields = ('detailer__user__first_name', 'detailer__user__last_name', 'account_name', 'account_number')
    list_filter = ('bank_name',)

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('job', 'rating', 'comment', 'created_at')
    search_fields = ('job__client_name', 'job__vehicle_registration', 'comment')
    list_filter = ('rating', 'created_at')

@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = ('detailer', 'title', 'status', 'date_completed')
    search_fields = ('detailer__user__first_name', 'detailer__user__last_name', 'title')
    list_filter = ('status', 'date_completed')

@admin.register(Detailer)
class DetailerAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'city', 'is_active', 'is_verified', 'commission_rate')
    search_fields = ('user__first_name', 'user__last_name', 'user__email', 'city')
    list_filter = ('is_active', 'is_verified', 'city')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone', 'is_detailer', 'is_admin', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    list_filter = ('is_detailer', 'is_admin', 'is_active', 'date_joined')

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('detailer', 'date', 'start_time', 'end_time', 'is_available', 'is_booked')
    search_fields = ('detailer__user__first_name', 'detailer__user__last_name')
    list_filter = ('date', 'is_available', 'is_booked')

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('detailer', 'date', 'start_time', 'end_time', 'is_available')
    search_fields = ('detailer__user__first_name', 'detailer__user__last_name')
    list_filter = ('date', 'is_available')