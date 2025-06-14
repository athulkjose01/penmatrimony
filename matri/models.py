# models.py
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User




class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    def __str__(self):
        return f'{self.user.username} Profile (Basic)'

class UserProfile(models.Model):
    # Define CHOICES as static attributes for easier access in forms
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    MARITAL_STATUS_CHOICES = [
        ('Never Married', 'Never Married'), ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'), ('Separated', 'Separated'),
    ]
    DIET_CHOICES = [('Vegetarian', 'Vegetarian'), ('Non-Vegetarian', 'Non-Vegetarian')]
    SMOKING_CHOICES = [('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')] # Added Occasionally
    DRINKING_CHOICES = [('Yes', 'Yes'), ('No', 'No'), ('Occasionally', 'Occasionally')] # Added Occasionally
    FAMILY_STATUS_CHOICES = [
        ('Middle Class', 'Middle Class'), ('Upper Middle Class', 'Upper Middle Class'),
        ('Rich', 'Rich'), ('Affluent', 'Affluent'),
    ]
    FAMILY_TYPE_CHOICES = [('Joint', 'Joint'), ('Nuclear', 'Nuclear')]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    religion = models.CharField(max_length=50, default="Christian", editable=False)
    category = models.CharField(max_length=50, default="Pentecost", editable=False)
    mother_tongue = models.CharField(max_length=50, default="Malayalam")
    marital_status = models.CharField(max_length=20, choices=MARITAL_STATUS_CHOICES)
    height = models.IntegerField(help_text="Height in Cm (e.g. 172)", null=True, blank=True)
    weight = models.IntegerField(help_text="Weight in kg (e.g. 70)", null=True, blank=True)
    education = models.CharField(max_length=100, blank=True, null=True)
    profession = models.CharField(max_length=100, blank=True, null=True)
    Monthly_income = models.CharField(max_length=50, blank=True)
    country = models.CharField(default="India", max_length=50, blank=True)
    state = models.CharField(default="Kerala", max_length=50, blank=True)
    city = models.CharField(max_length=50, blank=True)
    housename = models.CharField(max_length=50, blank=True)
    current_location = models.CharField(max_length=50, blank=True)
    diet = models.CharField(max_length=20, choices=DIET_CHOICES, blank=True)
    smoking = models.CharField(max_length=20, choices=SMOKING_CHOICES, blank=True)
    drinking = models.CharField(max_length=20, choices=DRINKING_CHOICES, blank=True)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    family_status = models.CharField(max_length=50, choices=FAMILY_STATUS_CHOICES, blank=True)
    family_type = models.CharField(max_length=50, choices=FAMILY_TYPE_CHOICES, blank=True)
    siblings = models.PositiveIntegerField(default=0, null=True, blank=True)
    looking_for = models.CharField(max_length=10, choices=GENDER_CHOICES[:2], blank=True) # Only Male/Female for looking_for
    about_me = models.TextField(blank=True, null=True)
    hobbies = models.CharField(max_length=255, blank=True, null=True)
    has_own_a_car = models.BooleanField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_profile_in_index = models.BooleanField(default=False) # Default to False for new profiles
    is_premium_member = models.BooleanField(default=False)

    @property
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - \
                   ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

    def __str__(self):
        return f"{self.full_name or self.user.username} (ID: {self.id} / UserID: {self.user.id})"


class PartnerPreference(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='partner_preferences')
    preferred_age_min = models.PositiveIntegerField(null=True, blank=True, verbose_name="Preferred Minimum Age")
    preferred_age_max = models.PositiveIntegerField(null=True, blank=True, verbose_name="Preferred Maximum Age")
    preferred_height_min = models.IntegerField(null=True, blank=True, help_text="e.g., 150 (in cm)", verbose_name="Preferred Min Height (cm)")
    preferred_height_max = models.IntegerField(null=True, blank=True, help_text="e.g., 190 (in cm)", verbose_name="Preferred Max Height (cm)")
    preferred_weight_min_kg = models.IntegerField(null=True, blank=True, help_text="e.g., 50 (in kg)", verbose_name="Preferred Min Weight (kg)")
    preferred_weight_max_kg = models.IntegerField(null=True, blank=True, help_text="e.g., 80 (in kg)", verbose_name="Preferred Max Weight (kg)")
    
    PREFERRED_MARITAL_STATUS_CHOICES = [('Any', 'Any')] + UserProfile.MARITAL_STATUS_CHOICES
    preferred_marital_status = models.CharField(max_length=20, choices=PREFERRED_MARITAL_STATUS_CHOICES, default='Any', blank=True, null=True, verbose_name="Preferred Marital Status")
    
    preferred_education = models.CharField(max_length=255, blank=True, verbose_name="Preferred Education Level(s)")
    preferred_profession = models.CharField(max_length=255, blank=True, verbose_name="Preferred Profession(s)")
    
    PREFERRED_DIET_CHOICES = [('Any', 'Any')] + UserProfile.DIET_CHOICES
    preferred_diet = models.CharField(max_length=20, choices=PREFERRED_DIET_CHOICES, default='Any', blank=True, null=True, verbose_name="Preferred Diet")
    
    PREFERRED_SMOKING_CHOICES = [('Any', 'Any')] + UserProfile.SMOKING_CHOICES
    preferred_smoking = models.CharField(max_length=20, choices=PREFERRED_SMOKING_CHOICES, default='Any', blank=True, null=True, verbose_name="Preferred Smoking Habit")
    
    PREFERRED_DRINKING_CHOICES = [('Any', 'Any')] + UserProfile.DRINKING_CHOICES
    preferred_drinking = models.CharField(max_length=20, choices=PREFERRED_DRINKING_CHOICES, default='Any', blank=True, null=True, verbose_name="Preferred Drinking Habit")
    
    expectations_about_partner = models.TextField(blank=True, verbose_name="A Few Words About Your Ideal Partner")

    def __str__(self):
        return f"Preferences for {self.user_profile.full_name or self.user_profile.user.username}"





class UserPost(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='posts')
    image = models.ImageField(upload_to='user_posts/') # Images will be saved in MEDIA_ROOT/user_posts/
    caption = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at'] # Show newest posts first

    def __str__(self):
        return f"Post by {self.user_profile.full_name or self.user_profile.user.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"




class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    post = models.ForeignKey('UserPost', on_delete=models.CASCADE, null=True)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username} - {self.message}"
    
    



# models.py (Add this new model at the end of the file)

class InterestRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_interests')
    receiver = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='received_interests')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Ensure a user can only send one request to another user
        unique_together = ('sender', 'receiver')
        ordering = ['-created_at']

    def __str__(self):
        return f"Interest from {self.sender.full_name} to {self.receiver.full_name} ({self.status})"
    




class ChatRoom(models.Model):
    """
    A chat room for two users.
    Ensures that only one room exists for a pair of users.
    """
    participants = models.ManyToManyField(UserProfile, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_profiles = self.participants.all()
        if user_profiles.count() == 2:
            return f"Chat between {user_profiles[0].full_name} and {user_profiles[1].full_name}"
        return f"Chat Room {self.id}"

class ChatMessage(models.Model):
    """
    A message within a chat room.
    """
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.full_name} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"




class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100)
    razorpay_signature = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} by {self.user.username}"
    





