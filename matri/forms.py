# matri/forms.py
from django import forms
from .models import UserProfile, PartnerPreference
from datetime import date # Make sure UserProfile and PartnerPreference models are imported
from .models import UserPost
from django.contrib.auth.forms import SetPasswordForm



# --- 1. UserProfileForm (for creating/editing UserProfile) ---
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile # Links to the UserProfile MODEL
        exclude = ['user', 'religion', 'category', 'Monthly_income', 'is_profile_in_index', 'is_premium_member']
        widgets = {
            'date_of_birth': forms.DateInput(
                attrs={
                    'type': 'date',
                    'max': '2010-01-01'
                }
            ),
            'about_me': forms.Textarea(attrs={'rows': 4}),
            'height': forms.NumberInput(attrs={'step': '1', 'onwheel': 'this.blur();'}),
            'weight': forms.NumberInput(attrs={'step': '1', 'onwheel': 'this.blur();'}),
            'profile_picture': forms.ClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        user_gender_from_view_post = kwargs.pop('user_gender', None)
        super().__init__(*args, **kwargs)

        # Pre-fill full_name
        if user and not self.instance.pk and not self.is_bound:
            user_full_name = user.get_full_name() or user.username
            self.initial['full_name'] = user_full_name

        # Determine current_gender for looking_for logic
        current_gender = None
        if self.instance and self.instance.pk and self.instance.gender:
            current_gender = self.instance.gender
        elif self.is_bound and 'gender' in self.data:
            current_gender = self.data.get('gender')
        elif user_gender_from_view_post:
            current_gender = user_gender_from_view_post
        elif not self.is_bound and 'gender' in self.initial: # Check initial data if not bound
            current_gender = self.initial.get('gender')


        # Adjust 'looking_for' choices
        looking_for_field = self.fields.get('looking_for')
        if looking_for_field:
            # Ensure choices are fetched from the model field, not UserProfile itself
            model_field_looking_for = UserProfile._meta.get_field('looking_for')
            original_model_choices = model_field_looking_for.choices
            blank_choice = [('', '---------')]

            if current_gender == 'Male':
                looking_for_field.choices = blank_choice + [choice for choice in original_model_choices if choice[0] == 'Female']
                if not (self.instance and self.instance.pk) and not self.is_bound:
                    looking_for_field.initial = 'Female'
            elif current_gender == 'Female':
                looking_for_field.choices = blank_choice + [choice for choice in original_model_choices if choice[0] == 'Male']
                if not (self.instance and self.instance.pk) and not self.is_bound:
                    looking_for_field.initial = 'Male'
            else:
                # Ensure original_model_choices is a list if it's a generator/tuple
                looking_for_field.choices = blank_choice + list(original_model_choices)


        # Make fields not required if blank=True in model
        for field_name, field_obj in self.fields.items():
            # Check if the field_name actually exists on the model before trying to get it
            try:
                model_field = UserProfile._meta.get_field(field_name)
                if hasattr(model_field, 'blank') and model_field.blank:
                    field_obj.required = False
            except forms.fields.FieldDoesNotExist: # Or django.core.exceptions.FieldDoesNotExist in older Django
                # This field might be an extra field not on the model, or from a parent.
                # Handle as needed or pass.
                pass
            except AttributeError: # UserProfile._meta might not be fully initialized in some rare cases during setup
                pass


    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob: # Only validate if a date is provided
            if dob.year >= 2011: # Year must be 2011 or earlier
                raise forms.ValidationError("Year of birth must be 2011 or earlier.")
            # You could add other validations, like not being in the future
            if dob > date.today():
                raise forms.ValidationError("Date of birth cannot be in the future.")
        return dob


# --- 2. PartnerPreferenceForm (for creating/editing PartnerPreference) ---
class PartnerPreferenceForm(forms.ModelForm):
    class Meta:
        model = PartnerPreference # Links to the PartnerPreference MODEL
        exclude = ['user_profile']
        widgets = {
            'preferred_age_min': forms.NumberInput(attrs={'placeholder': 'e.g., 25', 'onwheel': 'this.blur();'}),
            'preferred_age_max': forms.NumberInput(attrs={'placeholder': 'e.g., 35', 'onwheel': 'this.blur();'}),
            'preferred_height_min': forms.NumberInput(attrs={'step': '1', 'placeholder': 'e.g., 150', 'onwheel': 'this.blur();'}),
            'preferred_height_max': forms.NumberInput(attrs={'step': '1', 'placeholder': 'e.g., 180', 'onwheel': 'this.blur();'}),
            'preferred_weight_min_kg': forms.NumberInput(attrs={'step': '1', 'placeholder': 'e.g., 50', 'onwheel': 'this.blur();'}),
            'preferred_weight_max_kg': forms.NumberInput(attrs={'step': '1', 'placeholder': 'e.g., 100', 'onwheel': 'this.blur();'}),
            'preferred_education': forms.TextInput(attrs={'placeholder': 'e.g., Masters, PhD'}),
            'preferred_profession': forms.TextInput(attrs={'placeholder': 'e.g., Doctor, Engineer'}),
            'expectations_about_partner': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe your ideal partner...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Making all fields not required by default, as they are optional preferences
        for field_name in self.fields:
            self.fields[field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        age_min = cleaned_data.get('preferred_age_min')
        age_max = cleaned_data.get('preferred_age_max')
        height_min = cleaned_data.get('preferred_height_min')
        height_max = cleaned_data.get('preferred_height_max')
        weight_min = cleaned_data.get('preferred_weight_min_kg')
        weight_max = cleaned_data.get('preferred_weight_max_kg')

        # Validate Age Range
        if age_min is not None and age_max is not None:
            if age_min >= age_max:
                self.add_error('preferred_age_min', "Minimum age must be less than maximum age.")
                self.add_error('preferred_age_max', "Maximum age must be greater than minimum age.") # Optional: add error to both fields for clarity

        # Validate Height Range
        if height_min is not None and height_max is not None:
            if height_min >= height_max:
                self.add_error('preferred_height_min', "Minimum height must be less than maximum height.")
                self.add_error('preferred_height_max', "Maximum height must be greater than minimum height.")

        # Validate Weight Range
        if weight_min is not None and weight_max is not None:
            if weight_min >= weight_max:
                self.add_error('preferred_weight_min_kg', "Minimum weight must be less than maximum weight.")
                self.add_error('preferred_weight_max_kg', "Maximum weight must be greater than minimum weight.")
                
        return cleaned_data




# --- 3. UserSearchForm (for searching profiles) ---
class UserSearchForm(forms.Form):
    username_search = forms.CharField(
        label="Enter the username:",
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., user7654', 'class': 'form-control'})
    )
    gender = forms.ChoiceField(
        choices=[('', 'Any Gender')] + UserProfile.GENDER_CHOICES[:2], # Limit to Male/Female for search
        required=False, label="Looking for Gender",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    age_min = forms.IntegerField(
        label="Min Age", required=False, min_value=18, max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 25', 'class': 'form-control'})
    )
    age_max = forms.IntegerField(
        label="Max Age", required=False, min_value=18, max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': 'e.g., 35', 'class': 'form-control'})
    )
    marital_status = forms.ChoiceField(
        choices=[('', 'Any Marital Status')] + UserProfile.MARITAL_STATUS_CHOICES,
        required=False, label="Marital Status",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    height_min = forms.DecimalField(
        label="Min Height (cm)", required=False, max_digits=3, decimal_places=1,
        widget=forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'e.g., 150', 'class': 'form-control'})
    )
    height_max = forms.DecimalField(
        label="Max Height (cm)", required=False, max_digits=3, decimal_places=1,
        widget=forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'e.g., 170', 'class': 'form-control'})
    )
    weight_min_kg = forms.DecimalField(
        label="Min Weight (kg)", required=False, max_digits=5, decimal_places=1,
        widget=forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'e.g., 50.0', 'class': 'form-control'})
    )
    weight_max_kg = forms.DecimalField(
        label="Max Weight (kg)", required=False, max_digits=5, decimal_places=1,
        widget=forms.NumberInput(attrs={'step': '0.1', 'placeholder': 'e.g., 80.0', 'class': 'form-control'})
    )
    profession = forms.CharField(
        label="Profession", required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., Doctor, Engineer', 'class': 'form-control'})
    )
    drinking = forms.ChoiceField(
        choices=[('', 'Any Drinking Habit')] + UserProfile.DRINKING_CHOICES,
        required=False, label="Drinking Habit",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    smoking = forms.ChoiceField(
        choices=[('', 'Any Smoking Habit')] + UserProfile.SMOKING_CHOICES,
        required=False, label="Smoking Habit",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    family_type = forms.ChoiceField(
        choices=[('', 'Any Family Type')] + UserProfile.FAMILY_TYPE_CHOICES,
        required=False, label="Family Type",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    search_type = forms.CharField(widget=forms.HiddenInput(), required=False)

    def __init__(self, *args, **kwargs):
        user_gender = kwargs.pop('user_gender', None) # Current logged-in user's gender
        super().__init__(*args, **kwargs)

        # Auto-select opposite gender in "Looking for Gender" if user's gender is known
        # and the form is not bound (i.e., not a submission) and not pre-filled by GET params.
        if user_gender and not self.is_bound and not self.initial.get('gender') and not (args and args[0]):
            if user_gender == 'Male':
                self.initial['gender'] = 'Female'
            elif user_gender == 'Female':
                self.initial['gender'] = 'Male'
        
        # If form is bound (submitted), conditionally set 'required' for fields
        # based on the submitted 'search_type'.
        if self.is_bound:
            submitted_search_type = self.data.get('search_type')
            if submitted_search_type == 'username_search':
                # Only username_search is relevant for this search type.
                # All other advanced fields are effectively optional for this submission.
                for field_name in self.fields:
                    if field_name not in ['username_search', 'search_type']:
                        self.fields[field_name].required = False # Mark as not required for validation
            elif submitted_search_type == 'advanced_search':
                 # username_search is optional for advanced search.
                 self.fields['username_search'].required = False

    def clean_username_search(self):
        """
        Custom validation for the username_search field.
        If search_type is 'username_search', this field becomes mandatory.
        """
        data = self.cleaned_data.get('username_search')
        # Access self.data (raw request data) because cleaned_data for search_type might not be available yet
        # if search_type itself fails validation or is processed later.
        search_type_from_submission = self.data.get('search_type') 

        if search_type_from_submission == 'username_search' and not data:
             raise forms.ValidationError("Please enter a Username for Username Search.")
        # Optional: Add further format validation for username if needed (e.g., starts with 'user')
        # if data and not data.lower().startswith('user'):
        #     raise forms.ValidationError("Username should typically start with 'user'.")
        return data

    def clean(self):
        cleaned_data = super().clean()
        # The search_type from self.data is more reliable here than from cleaned_data
        # as cleaned_data might not have it if it's invalid or processed later.
        search_type_from_submission = self.data.get('search_type')

        # Only perform range validations if it's an advanced search
        # or if the fields have values (as they are all optional by default)
        # The 'required' status for specific search types is handled in __init__ and clean_FIELDNAME.

        age_min = cleaned_data.get('age_min')
        age_max = cleaned_data.get('age_max')
        if age_min is not None and age_max is not None and age_min > age_max: # Check for None
            self.add_error('age_min', "Min age cannot be greater than max age.")
            self.add_error('age_max', None)
        
        height_min = cleaned_data.get('height_min')
        height_max = cleaned_data.get('height_max')
        if height_min is not None and height_max is not None and height_min > height_max:
            self.add_error('height_min', "Min height cannot be greater than max height.")
            self.add_error('height_max', None)

        weight_min = cleaned_data.get('weight_min_kg')
        weight_max = cleaned_data.get('weight_max_kg')
        if weight_min is not None and weight_max is not None and weight_min > weight_max:
            self.add_error('weight_min_kg', "Min weight cannot be greater than max weight.")
            self.add_error('weight_max_kg', None)
        
        return cleaned_data
    





class UserPostForm(forms.ModelForm):
    class Meta:
        model = UserPost
        fields = ['image', 'caption']
        widgets = {
            'caption': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write a caption (optional)...',
                'class': 'form-control-dark' # Custom class for styling if needed
            }),
            'image': forms.ClearableFileInput(attrs={
                'accept': 'image/*', # Suggest to browser to filter for image files
                'class': 'form-control-dark'
            })
        }
        labels = {
            'image': 'Select Photo',
            'caption': 'Caption'
        }



class PasswordResetForm(forms.Form):
    email = forms.EmailField()



class CustomSetPasswordForm(SetPasswordForm):
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')

        # Check for at least one uppercase letter, one lowercase letter, and one special character
        if not re.search(r'[A-Z]', password1):
            raise ValidationError("Your password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password1):
            raise ValidationError("Your password must contain at least one lowercase letter.")
        if not re.search(r'\W', password1):
            raise ValidationError("Your password must contain at least one special character.")

        # Check for at least 8 characters
        if len(password1) < 8:
            raise ValidationError("Your password must contain at least 8 characters.")

        # Bypass the password strength check
        self._check_password_strength = lambda password: None

        return password1
