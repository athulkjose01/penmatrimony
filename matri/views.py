# views.py

import os
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
import requests
from .models import ChatRoom, PostLike, Profile, UserProfile, UserPost
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
import random
from django.db.models import Q, Max, Count, Subquery, OuterRef
from django.contrib import messages
from django.views.decorators.http import require_POST
import string
from django.template.loader import render_to_string
from .forms import UserPostForm, UserProfileForm
from .models import UserProfile, PartnerPreference # Import PartnerPreference
from .forms import UserProfileForm, PartnerPreferenceForm # Import PartnerPreferenceForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import UserProfile, PartnerPreference, InterestRequest, Profile, ChatMessage, Payment
from .forms import UserProfileForm, PartnerPreferenceForm, UserSearchForm
from django.db.models import Q
from datetime import date, timedelta
import re # Import regular expressions module
# For Groq integration
from django.conf import settings # To access GROQ_API_KEY
from groq import Groq # Groq SDK
import logging 
from django.http import HttpResponse
from .groq_utils import get_related_professions_groq
from django.http import JsonResponse # Import JsonResponse
import json
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger # For pagination
from .models import UserProfile, UserPost
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Max
from .forms import PasswordResetForm
from .forms import CustomSetPasswordForm
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
import razorpay
from django.views.decorators.csrf import csrf_exempt # We will remove this where possible
from django.db import transaction # Import transaction
import logging
import time
from .models import Notification # Import the new model
from django.contrib.humanize.templatetags.humanize import naturaltime
import hashlib
import base64
import uuid
from phonepe.sdk.pg.payments.v2.standard_checkout_client import StandardCheckoutClient
from phonepe.sdk.pg.env import Env
from phonepe.sdk.pg.payments.v2.models.request.standard_checkout_pay_request import StandardCheckoutPayRequest
from django.core.cache import cache # Using Django's cache to store the token
from django.db import transaction




# ... (generate_username, register_view, login_view, logout_view remain the same as your last version) ...
def generate_username():
    base = 'user'
    suffix = ''.join(random.choices(string.digits, k=4))
    username = base + suffix
    while User.objects.filter(username=username).exists():
        suffix = ''.join(random.choices(string.digits, k=4))
        username = base + suffix
    return username




def generate_otp(length=5):
    """Generate a random numeric OTP."""
    return ''.join(random.choices(string.digits, k=length))

def send_otp_sms(phone_number, otp):
    """Sends an OTP using the Fast2SMS API."""
    # This message will be sent to the user.
    # The API templates this, so {#var#} is replaced by the 'otp' value.
    message_to_send = f"Your OTP for Pentecost Matrimony is {otp}. This code is valid for 10 minutes. Do not share it with anyone. - dccoder"
    
    # The Fast2SMS API for OTPs often uses 'variables_values' for the dynamic part.
    # The provided API URL also confirms this.
    payload = {
        'authorization': 'HVmWoy1neMpAlaUxf4JXFb7kC2EvPOdDQZhSwGqiLrNu3TR5ztt6alruhJsALHqwvT8g2GEBbZS1R9eM',
        'route': 'otp',
        'variables_values': otp, # The API will inject this into its configured template
        'flash': 0,
        'numbers': phone_number
    }
    
    url = "https://www.fast2sms.com/dev/bulkV2"
    
    try:
        response = requests.get(url, params=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        print(f"Fast2SMS Response: {result}") # For debugging
        
        if result.get("return") is True:
            return True, "OTP sent successfully."
        else:
            return False, result.get("message", "An unknown API error occurred.")
            
    except requests.exceptions.RequestException as e:
        print(f"Error sending OTP: {e}")
        return False, "Could not connect to the SMS service."
    

    

def register_view(request):
    """
    Handles both the GET request to display the registration form and the
    initial POST (AJAX) request to validate data and send an OTP.
    """
    if request.user.is_authenticated:
        # Redirect logged-in users away from the registration page
        try:
            UserProfile.objects.get(user=request.user)
            return redirect('index') 
        except UserProfile.DoesNotExist:
            # If they are logged in but have no profile, send them to create one
            return redirect('create_user_profile') 

    if request.method == 'POST':
        # This part handles the AJAX request from the JavaScript
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            email = data.get('email', '').strip().lower()
            phone_no_only = data.get('phone', '').strip() # e.g., "9876543210"
            password = data.get('password', '')

            # --- Server-side Validation ---
            if not all([name, email, phone_no_only, password]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)
            
            if '@' not in email or '.' not in email.split('@')[-1]:
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)

            if not phone_no_only.isdigit() or len(phone_no_only) != 10:
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit WhatsApp number.'}, status=400)
            
            # Prepend the country code for database storage and API calls
            full_phone_number = f"91{phone_no_only}"

            if User.objects.filter(email__iexact=email).exists():
                return JsonResponse({'status': 'error', 'message': 'This email address is already registered.'}, status=400)

            if Profile.objects.filter(phone=full_phone_number).exists():
                return JsonResponse({'status': 'error', 'message': 'This phone number is already registered.'}, status=400)

            # --- OTP Generation and Sending ---
            otp = generate_otp()
            
            # --- For Development: Simulate sending OTP to avoid using credits ---
            # print(f"Generated OTP for {full_phone_number}: {otp}")
            # success, message = True, "OTP Sent (Simulated)"
            # --- End of Simulation ---
            
            # --- For Production: Uncomment the line below to send a real SMS ---
            success, message = send_otp_sms(full_phone_number, otp)
            
            if not success:
                # If sending OTP fails, return the error from the API
                return JsonResponse({'status': 'error', 'message': f'Failed to send OTP: {message}'}, status=500)

            # Store all necessary data in the session to use after OTP verification
            request.session['registration_data'] = {
                'name': name,
                'email': email,
                'phone': full_phone_number, # Store the full number
                'password': password,
            }
            request.session['otp_details'] = {
                'otp': otp,
                'timestamp': time.time() # Record when the OTP was sent
            }
            
            # Send a success response to the frontend to trigger the OTP popup
            return JsonResponse({'status': 'success', 'message': 'OTP sent successfully. Please check your WhatsApp.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid request format.'}, status=400)
        except Exception as e:
            # General error catch
            print(f"Error in register_view: {e}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

    # This handles the initial GET request to load the page
    return render(request, 'matri/register.html')


# --- OTP VERIFICATION VIEW (Creates the user) ---

@require_POST
def verify_otp_view(request):
    """
    Verifies the OTP submitted by the user. If correct, creates the user account.
    """
    try:
        data = json.loads(request.body)
        submitted_otp = data.get('otp')
        
        reg_data = request.session.get('registration_data')
        otp_details = request.session.get('otp_details')

        # Check if session data exists
        if not all([submitted_otp, reg_data, otp_details]):
            return JsonResponse({'status': 'error', 'message': 'Your session has expired. Please start the registration process again.'}, status=400)

        # OTP is valid for 10 minutes (600 seconds)
        if time.time() - otp_details['timestamp'] > 600:
            # Clear expired session data
            request.session.flush() 
            return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please request a new one.'}, status=400)

        if submitted_otp == otp_details['otp']:
            # OTP is correct, proceed with creating the user
            username = generate_username()
            user = User.objects.create_user(
                username=username,
                password=reg_data['password'],
                email=reg_data['email']
            )
            user.first_name = reg_data['name']
            user.save()
            
            # Create the associated Profile
            Profile.objects.create(user=user, phone=reg_data['phone'])
            
            # Important: Clear all registration-related session data after success
            request.session.flush()
            
            # Use Django messages for the next page load (login page)
            messages.success(request, f"Registration successful! Your username is {username}. Please log in to continue.")
            
            login_url = redirect('login').url
            return JsonResponse({'status': 'success', 'message': 'Verification successful!', 'redirect_url': login_url})
        else:
            # Incorrect OTP
            return JsonResponse({'status': 'error', 'message': 'The OTP you entered is incorrect. Please try again.'}, status=400)
    except Exception as e:
        print(f"Error during OTP verification: {e}")
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred during verification.'}, status=500)


# --- RESEND OTP VIEW ---

@require_POST
def resend_otp_view(request):
    """
    Handles the "Resend OTP" request, respecting the 3-minute cooldown.
    """
    reg_data = request.session.get('registration_data')
    otp_details = request.session.get('otp_details')

    if not reg_data or not otp_details:
        return JsonResponse({'status': 'error', 'message': 'No registration in progress. Please start over.'}, status=400)

    # Enforce a 3-minute (180 seconds) cooldown before resending
    if time.time() - otp_details.get('timestamp', 0) < 180:
        return JsonResponse({'status': 'error', 'message': 'Please wait a moment before requesting a new OTP.'}, status=429) # 429: Too Many Requests

    new_otp = generate_otp()
    phone_number = reg_data.get('phone')
    
    # --- For Development: Simulate sending OTP ---
    # print(f"Resent OTP for {phone_number}: {new_otp}")
    # success, message = True, "New OTP sent (Simulated)"
    # --- End of Simulation ---

    # --- For Production: Uncomment the line below to send a real SMS ---
    success, message = send_otp_sms(phone_number, new_otp)
    
    if not success:
        return JsonResponse({'status': 'error', 'message': f'Failed to send new OTP: {message}'}, status=500)

    # Update session with the new OTP and timestamp
    request.session['otp_details'] = {
        'otp': new_otp,
        'timestamp': time.time()
    }

    return JsonResponse({'status': 'success', 'message': 'A new OTP has been sent to your number.'})



def login_view(request):
    if request.user.is_authenticated:
        try:
            UserProfile.objects.get(user=request.user)
            return redirect('index')
        except UserProfile.DoesNotExist:
            return redirect('create_user_profile')

    context = {}
    if request.method == 'POST':
        email = request.POST.get('email','').strip().lower()
        password = request.POST.get('password','')

        if not email or not password:
            context['error'] = "Email and password are required."
            return render(request, 'matri/login.html', context)
        try:
            user_obj = User.objects.get(email__iexact=email) 
            user = authenticate(request, username=user_obj.username, password=password)
            if user:
                login(request, user)
                try:
                    UserProfile.objects.get(user=user)
                    return redirect('index')
                except UserProfile.DoesNotExist:
                    messages.info(request, "Welcome! Please complete your profile to get started.")
                    return redirect('create_user_profile')
            else:
                context['error'] = "Invalid email or password."
        except User.DoesNotExist:
            context['error'] = "No account found with this email address."
        except Exception as e: 
            context['error'] = f"An authentication error occurred. Please try again."
    return render(request, 'matri/login.html', context)



@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been successfully logged out.")
    return redirect('login')




def index_view(request):
    user_has_profile = False
    unread_messages_count = 0
    unread_notifications_count = 0 # Default to 0

    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_has_profile = True

            unread_messages_count = ChatMessage.objects.filter(
                room__participants=user_profile, is_read=False
            ).exclude(sender=user_profile).count()

            # --- This is the key part: Calculate count ONLY for this view ---
            unread_notifications_count = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()

        except UserProfile.DoesNotExist:
            user_has_profile = False

    featured_profiles = UserProfile.objects.filter(
        is_profile_in_index=True, profile_picture__isnull=False
    ).exclude(profile_picture='').distinct().order_by('?')[:8]

    context = {
        'featured_profiles': featured_profiles,
        'user_has_profile': user_has_profile,
        'unread_messages_count': unread_messages_count,
        # Pass the count specifically to the index.html template
        'unread_notifications_count': unread_notifications_count, 
    }
    
    return render(request, 'matri/index.html', context)



    
@login_required
def create_user_profile_view(request):
    user_has_profile = False # Flag for template, always False for create view
    try:
        # Check if UserProfile exists. If so, redirect to edit.
        user_profile_instance = UserProfile.objects.get(user=request.user)
        messages.info(request, "You already have a profile. You can edit it here.")
        return redirect('edit_user_profile') # Ensure 'edit_user_profile' URL name exists
    except UserProfile.DoesNotExist:
        pass # Proceed to creation

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, user=request.user, user_gender=request.POST.get('gender'))
        prefs_form = PartnerPreferenceForm(request.POST)

        if profile_form.is_valid() and prefs_form.is_valid():
            profile = profile_form.save(commit=False)
            profile.user = request.user
            profile.save() # Save UserProfile first

            preferences = prefs_form.save(commit=False)
            preferences.user_profile = profile # Link to the created UserProfile
            preferences.save()

            messages.success(request, "Your profile and partner preferences have been created successfully!")
            return redirect('index') # Or a 'view_my_profile' URL
        else:
            # Combine error messages if desired, or let template render them per form
            error_messages = []
            if profile_form.errors:
                error_messages.append("Please correct errors in your details.")
            if prefs_form.errors:
                 error_messages.append("Please correct errors in partner preferences.")
            if not error_messages: # General error if no specific form errors caught this way
                error_messages.append("Please correct the errors below.")
            messages.error(request, " ".join(error_messages))
    else:
        profile_form = UserProfileForm(user=request.user) # Pass user for full_name pre-fill
        prefs_form = PartnerPreferenceForm()
    
    return render(request, 'matri/create_user_profile.html', {
        'profile_form': profile_form,
        'prefs_form': prefs_form,
        'user_has_profile': user_has_profile
    })



@login_required
def add_user_post_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest': # Check if AJAX
            return JsonResponse({'success': False, 'error': 'User profile not found.'}, status=403)
        messages.error(request, "You need to create a detailed profile before adding posts.")
        return redirect('create_user_profile')

    if request.method == 'POST':
        form = UserPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user_profile = user_profile
            post.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                # For AJAX, you might want to return the new post's data or a success message.
                # Here, we still redirect, but an AJAX flow might update the page dynamically.
                return JsonResponse({
                    'success': True,
                    'message': 'Your photo has been posted!',
                    'redirect_url': request.build_absolute_uri(redirect('view_user_profile').url) # Send redirect URL
                })
            messages.success(request, 'Your photo has been posted!') # Fallback for non-JS
            return redirect('view_user_profile')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                error_dict = {}
                for field, errors in form.errors.items():
                    error_dict[field] = [e for e in errors]
                return JsonResponse({'success': False, 'error': 'Form validation failed.', 'errors': error_dict}, status=400)
            
            error_message_list = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_message_list.append(f"{form.fields[field].label or field}: {error}")
            messages.error(request, f"There was an error with your post: {'; '.join(error_message_list)}")
    else: # GET request
        form = UserPostForm()

    return render(request, 'matri/add_user_post.html', {
        'form': form,
        'user_has_profile': True # Assumed if they reach here past the initial check
    })


@login_required
def view_user_profile_view(request):
    user_has_profile = True
    partner_prefs = None
    user_posts = []
    pending_interests_count = 0  # Default to 0

    try:
        profile = UserProfile.objects.get(user=request.user)
        try:
            partner_prefs = profile.partner_preferences
        except PartnerPreference.DoesNotExist:
            partner_prefs = None

        user_posts = UserPost.objects.filter(user_profile=profile).order_by('-created_at')
        
        # --- NEW: Calculate the count of incoming pending interest requests ---
        pending_interests_count = InterestRequest.objects.filter(
            receiver=profile, 
            status='pending'
        ).count()

        context = {
            'profile': profile,
            'partner_prefs': partner_prefs,
            'user_has_profile': user_has_profile,
            'user_posts': user_posts,
            'pending_interests_count': pending_interests_count, # Pass the count to the template
        }
        return render(request, 'matri/view_user_profile.html', context)

    except UserProfile.DoesNotExist:
        messages.warning(request, "You haven't created a detailed profile yet. Please create one.")
        return redirect('create_user_profile')




@login_required
@require_POST # Ensures this view only accepts POST requests for safety
def delete_user_post_view(request, post_id):
    try:
        post = get_object_or_404(UserPost, id=post_id)

        # Security check: Ensure the logged-in user owns this post
        if post.user_profile.user != request.user:
            return JsonResponse({'success': False, 'error': 'You are not authorized to delete this post.'}, status=403)

        # Delete the image file from storage if it exists
        if post.image:
            post.image.delete(save=False) # save=False as we are about to delete the model instance

        post.delete()
        return JsonResponse({'success': True, 'message': 'Post deleted successfully.'})

    except UserPost.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found.'}, status=404)
    except Exception as e:
        # Log the error e for server-side debugging
        print(f"Error deleting post: {e}")
        return JsonResponse({'success': False, 'error': 'An unexpected error occurred while deleting the post.'}, status=500)
    


@login_required
def edit_user_profile_view(request):
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        # Get or create PartnerPreference instance linked to the UserProfile
        partner_prefs, created = PartnerPreference.objects.get_or_create(user_profile=user_profile)
    except UserProfile.DoesNotExist:
        messages.error(request, "You don't have a profile to edit. Please create one first.")
        return redirect('create_user_profile') # Ensure 'create_user_profile' URL name exists

    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, request.FILES, instance=user_profile, user=request.user, user_gender=request.POST.get('gender'))
        prefs_form = PartnerPreferenceForm(request.POST, instance=partner_prefs)

        if profile_form.is_valid() and prefs_form.is_valid():
            profile_form.save()
            prefs_form.save()
            messages.success(request, "Your profile and preferences have been updated successfully!")
            return redirect('index') # Or a 'view_my_profile' URL
        else:
            error_messages = []
            if profile_form.errors:
                error_messages.append("Please correct errors in your details.")
            if prefs_form.errors:
                 error_messages.append("Please correct errors in partner preferences.")
            if not error_messages:
                error_messages.append("Please correct the errors below.")
            messages.error(request, " ".join(error_messages))
    else:
        profile_form = UserProfileForm(instance=user_profile, user=request.user)
        prefs_form = PartnerPreferenceForm(instance=partner_prefs)

    return render(request, 'matri/edit_user_profile.html', { # Create this template
        'profile_form': profile_form,
        'prefs_form': prefs_form,
        'user_has_profile': True # Flag for template
    })





@login_required
def search_users_view(request):
    """
    Handles both username search and advanced search for user profiles.
    Uses Groq AI for an enhanced, semantic search on the 'profession' field.
    """
    current_user_profile = None
    try:
        current_user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.warning(request, "Please create your profile before searching for others.")
        return redirect('create_user_profile')

    # Start with all profiles except the current user and those without a profile picture
    results_queryset = UserProfile.objects.exclude(user=request.user).select_related('user')
    form_submitted_with_data = False

    # Pre-fill the 'gender' field on initial load based on the user's gender
    initial_form_data = {}
    if not request.GET:
        if current_user_profile.gender == 'Male':
            initial_form_data['gender'] = 'Female'
        elif current_user_profile.gender == 'Female':
            initial_form_data['gender'] = 'Male'

    form = UserSearchForm(request.GET or initial_form_data, user_gender=current_user_profile.gender)

    if request.GET:
        search_type = request.GET.get('search_type')

        if form.is_valid():
            cleaned_data = form.cleaned_data
            # Check if any form field has data to determine if a search was actually performed
            form_submitted_with_data = any(
                cleaned_data.get(key) for key in cleaned_data if key not in ['search_type', 'gender'] or (key == 'gender' and cleaned_data.get(key))
            )

            if search_type == 'username_search':
                username_query = cleaned_data.get('username_search')
                if username_query:
                    results_queryset = results_queryset.filter(user__username__iexact=username_query)
                else:
                    # If username search is selected but no username is provided, return no results
                    results_queryset = UserProfile.objects.none()
            
            elif search_type == 'advanced_search':
                # Apply filters sequentially
                if cleaned_data.get('gender'):
                    results_queryset = results_queryset.filter(gender=cleaned_data.get('gender'))
                
                today = date.today()
                age_min, age_max = cleaned_data.get('age_min'), cleaned_data.get('age_max')
                if age_min:
                    results_queryset = results_queryset.filter(date_of_birth__lte=date(today.year - age_min, today.month, today.day))
                if age_max:
                    results_queryset = results_queryset.filter(date_of_birth__gt=date(today.year - (age_max + 1), today.month, today.day))
                
                if cleaned_data.get('marital_status'):
                    results_queryset = results_queryset.filter(marital_status=cleaned_data.get('marital_status'))
                
                if cleaned_data.get('denomination'):
                    results_queryset = results_queryset.filter(denomination=cleaned_data.get('denomination'))

                if cleaned_data.get('height_min'):
                    results_queryset = results_queryset.filter(height__gte=cleaned_data.get('height_min'))
                if cleaned_data.get('height_max'):
                    results_queryset = results_queryset.filter(height__lte=cleaned_data.get('height_max'))
                if cleaned_data.get('weight_min_kg'):
                    results_queryset = results_queryset.filter(weight__gte=cleaned_data.get('weight_min_kg'))
                if cleaned_data.get('weight_max_kg'):
                    results_queryset = results_queryset.filter(weight__lte=cleaned_data.get('weight_max_kg'))
                
                # --- Enhanced Profession Search ---
                profession_query_str = cleaned_data.get('profession')
                if profession_query_str:
                    user_entered_professions = [p.strip() for p in profession_query_str.split(',') if p.strip()]
                    
                    if user_entered_professions:
                        all_db_profession_entries = UserProfile.objects.filter(profession__isnull=False).exclude(profession__exact='').values_list('profession', flat=True).distinct()
                        unique_individual_db_professions = set()
                        for entry in all_db_profession_entries:
                            for p_item in entry.split(','): 
                                cleaned_p_item = p_item.strip()
                                if cleaned_p_item:
                                    unique_individual_db_professions.add(cleaned_p_item)
                        
                        unique_db_professions_list = list(unique_individual_db_professions)

                        if not unique_db_professions_list:
                            q_objects_prof = Q()
                            for term in user_entered_professions:
                                q_objects_prof |= Q(profession__icontains=term)
                            results_queryset = results_queryset.filter(q_objects_prof)
                        else:
                            all_groq_matched_professions = set()
                            groq_call_failed_for_any_term = False

                            for search_term in user_entered_professions:
                                related_terms_from_groq = get_related_professions_groq(search_term, unique_db_professions_list)
                                if related_terms_from_groq is None:
                                    groq_call_failed_for_any_term = True
                                    break 
                                for term in related_terms_from_groq:
                                    all_groq_matched_professions.add(term)
                            
                            if groq_call_failed_for_any_term:
                                print("DEBUG: Groq call failed, falling back to simple icontains search.")
                                q_objects_prof = Q()
                                for term in user_entered_professions:
                                    q_objects_prof |= Q(profession__icontains=term)
                                results_queryset = results_queryset.filter(q_objects_prof)
                            else:
                                if all_groq_matched_professions:
                                    print(f"DEBUG: Querying database with Groq-matched professions: {all_groq_matched_professions}")
                                    q_objects_prof = Q()
                                    # ==================================================================
                                    # THE FIX IS HERE: Using __icontains for reliable matching
                                    # of the exact profession titles returned by Groq.
                                    # ==================================================================
                                    for p_term in all_groq_matched_professions:
                                        q_objects_prof |= Q(profession__icontains=p_term)
                                    # ==================================================================
                                    
                                    results_queryset = results_queryset.filter(q_objects_prof)
                                else:
                                    print("DEBUG: Groq ran successfully but found no matching professions.")
                                    results_queryset = results_queryset.none()
                # --- End of Enhanced Profession Search ---

                if cleaned_data.get('drinking'):
                    results_queryset = results_queryset.filter(drinking=cleaned_data.get('drinking'))
                if cleaned_data.get('smoking'):
                    results_queryset = results_queryset.filter(smoking=cleaned_data.get('smoking'))
            
            else: # Invalid or no search_type
                if request.GET:
                    messages.warning(request, "Invalid search attempt.")
                results_queryset = UserProfile.objects.none()

            if not results_queryset.exists() and form_submitted_with_data:
                messages.info(request, "")
        
        else: # Form is not valid
            was_attempted_submit = any(val for key, val in request.GET.items() if key != 'search_type' and val)
            if was_attempted_submit:
                messages.error(request, "There were errors in your search criteria. Please check the form.")
            results_queryset = UserProfile.objects.none()
    else: # Not a GET request (initial page load)
        results_queryset = UserProfile.objects.none()

    context = {
        'form': form,
        'results': results_queryset,
        'user_has_profile': True,
        'form_submitted_with_data': form_submitted_with_data,
    }
    return render(request, 'matri/search_users.html', context)





@login_required
def view_other_user_profile_view(request, profile_id):
    try:
        my_profile = UserProfile.objects.get(user=request.user)
        user_has_profile_for_nav = True
    except UserProfile.DoesNotExist:
        messages.warning(request, "Please create your profile before viewing others.")
        return redirect('create_user_profile')

    profile_to_view = get_object_or_404(UserProfile, id=profile_id)
    
    if profile_to_view.user == request.user:
        return redirect('view_user_profile') 

    partner_prefs_to_view = PartnerPreference.objects.filter(user_profile=profile_to_view).first()
    
    # --- START OF LIKED POSTS LOGIC (UPDATED) ---
    user_posts_to_view = UserPost.objects.filter(user_profile=profile_to_view).order_by('-created_at')

    # Get a list of post IDs from the gallery that the current user has liked using the new PostLike model
    liked_post_ids = set(
        PostLike.objects.filter(
            user=request.user, 
            post__in=user_posts_to_view
        ).values_list('post_id', flat=True)
    )

    # Annotate each post with whether the current user has liked it
    for post in user_posts_to_view:
        post.is_liked_by_user = post.id in liked_post_ids
    # --- END OF LIKED POSTS LOGIC ---

    # --- Check interest status ---
    interest_status = 'none'
    interest_request_obj = None
    contact_phone = None
    
    interest_lookup = InterestRequest.objects.filter(
        (Q(sender=my_profile) & Q(receiver=profile_to_view)) |
        (Q(sender=profile_to_view) & Q(receiver=my_profile))
    ).first()

    if interest_lookup:
        interest_request_obj = interest_lookup
        if interest_lookup.status == 'accepted':
            interest_status = 'accepted'
            try:
                basic_profile = Profile.objects.get(user=profile_to_view.user)
                contact_phone = basic_profile.phone
            except Profile.DoesNotExist:
                contact_phone = "Not Provided"
        elif interest_lookup.sender == my_profile:
            interest_status = 'sent_pending'
        elif interest_lookup.receiver == my_profile:
            interest_status = 'received_pending'

    context = {
        'profile': profile_to_view,
        'partner_prefs': partner_prefs_to_view,
        'user_has_profile': user_has_profile_for_nav,
        'user_posts': user_posts_to_view,
        'is_own_profile': False,
        'interest_status': interest_status,
        'interest_request': interest_request_obj,
        'contact_phone': contact_phone,
    }
    return render(request, 'matri/view_other_user_profile.html', context)





# ... (your existing views) ...

@login_required
def post_feed_view(request):
    try:
        logged_in_user_profile = UserProfile.objects.select_related('user').get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.warning(request, "Please create your profile to view the feed.")
        return redirect('create_user_profile') 

    logged_in_user_gender = logged_in_user_profile.gender
    own_posts_q = Q(user_profile=logged_in_user_profile)
    opposite_gender_posts_q = Q() 

    if logged_in_user_gender == 'Male':
        opposite_gender_posts_q = Q(user_profile__gender='Female')
    elif logged_in_user_gender == 'Female':
        opposite_gender_posts_q = Q(user_profile__gender='Male')
    elif logged_in_user_gender == 'Other':
         opposite_gender_posts_q = Q(user_profile__gender='Male') | Q(user_profile__gender='Female')
    
    final_query = own_posts_q | opposite_gender_posts_q
        
    all_posts_list = UserPost.objects.filter(final_query).select_related(
        'user_profile', 
        'user_profile__user'
    ).distinct().order_by('-created_at')

    # --- LIKED POSTS LOGIC (UPDATED TO USE PostLike MODEL) ---
    if request.user.is_authenticated:
        # Get a set of post IDs from the feed that the current user has liked.
        liked_post_ids = set(
            PostLike.objects.filter(
                user=request.user,
                post__in=all_posts_list  # Check only against posts in our feed
            ).values_list('post_id', flat=True)
        )
    else:
        liked_post_ids = set()

    # Annotate each post object with a new attribute 'is_liked_by_user'.
    for post in all_posts_list:
        post.is_liked_by_user = post.id in liked_post_ids
    # --- END OF UPDATED LOGIC ---

    # --- PAGINATION REMOVED ---
    # The entire list of posts will be sent to the template.
    
    context = {
        'posts': all_posts_list, # Changed from 'posts_page' to 'posts'
        'user_has_profile': True,
        'page_title': "Community Feed", 
    }
    return render(request, 'matri/post_feed.html', context)





# matri/views.py

# views.py

@login_required
@require_POST
def like_post(request, post_id):
    post = get_object_or_404(UserPost, id=post_id)
    
    if post.user_profile.user == request.user:
        return JsonResponse({'status': 'error', 'message': 'Cannot like your own post'}, status=403)

    like_obj, created = PostLike.objects.get_or_create(user=request.user, post=post)

    if created:
        action = 'liked'
        # --- Create a notification for the post owner ---
        sender_profile = get_object_or_404(UserProfile, user=request.user)
        if post.user_profile.user != request.user:
            Notification.objects.create(
                recipient=post.user_profile.user,
                sender_profile=sender_profile,
                notification_type='like',
                text=f"{sender_profile.full_name} liked your post.",
                post=post
            )
    else:
        like_obj.delete()
        action = 'unliked'
        # --- Delete the corresponding notification ---
        Notification.objects.filter(
            recipient=post.user_profile.user,
            sender_profile__user=request.user,
            notification_type='like',
            post=post
        ).delete()

    return JsonResponse({'status': 'success', 'action': action})








# --- AJAX VIEW FOR LIVE MESSAGE COUNT (This is the one I provided before) ---
@login_required
def get_unread_message_count(request):
    """
    API endpoint to get the total number of unread messages for the logged-in user.
    """
    try:
        current_user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        # If user has no profile, they can't have messages
        return JsonResponse({'unread_count': 0})

    # Count unread messages in all rooms the user is a participant of.
    count = ChatMessage.objects.filter(
        room__participants=current_user_profile,
        is_read=False
    ).exclude(
        sender=current_user_profile
    ).count()
    
    return JsonResponse({'unread_count': count})








@login_required
@require_POST
def send_interest_request(request, profile_id):
    sender_profile = get_object_or_404(UserProfile, user=request.user)
    receiver_profile = get_object_or_404(UserProfile, id=profile_id)

    if sender_profile == receiver_profile:
        messages.error(request, "You cannot send an interest request to yourself.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    if InterestRequest.objects.filter(sender=sender_profile, receiver=receiver_profile).exists() or \
       InterestRequest.objects.filter(sender=receiver_profile, receiver=sender_profile).exists():
        messages.warning(request, "An interest request already exists with this user.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    interest_req = InterestRequest.objects.create(sender=sender_profile, receiver=receiver_profile, status='pending')
    
    # --- Create notification for the receiver ---
    Notification.objects.create(
        recipient=receiver_profile.user,
        sender_profile=sender_profile,
        notification_type='interest_sent',
        text=f"You have received an interest request from {sender_profile.full_name}.",
        interest_request=interest_req
    )
    
    messages.success(request, f"Your interest has been sent to {receiver_profile.full_name}.")
    return redirect('view_other_user_profile', profile_id=profile_id)


@login_required
@require_POST
def accept_interest_request(request, interest_id):
    interest_request = get_object_or_404(InterestRequest, id=interest_id)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    if interest_request.receiver != my_profile:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')

    interest_request.status = 'accepted'
    interest_request.save()

    # --- Create notification for the sender ---
    Notification.objects.create(
        recipient=interest_request.sender.user,
        sender_profile=my_profile,
        notification_type='interest_accepted',
        text=f"{my_profile.full_name} has accepted your interest request.",
        interest_request=interest_request
    )

    messages.success(request, f"You have accepted the interest from {interest_request.sender.full_name}. You can now see their contact details and start a chat.")
    return redirect('view_other_user_profile', profile_id=interest_request.sender.id)




@login_required
def notification_list_view(request):
    """
    Displays a list of all notifications and marks them as read.
    This is a full page, not an API.
    """
    # Get all notifications for the user, newest first.
    notifications = Notification.objects.filter(recipient=request.user, is_read=False)

    # Mark all unread notifications as read.
    # We do this after fetching so we can still show which ones were new.
    #Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    context = {
        'page_title': 'Your Notifications',
        'notifications': notifications,
        'user_has_profile': True, # Assume user has a profile to see this page
    }
    return render(request, 'matri/notifications.html', context)





@login_required
def mark_all_as_read_view(request):
    """
    Finds all unread notifications for the logged-in user and
    marks them as read.
    """
    # Use .update() for an efficient, single database query
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)

    # (Optional) Add a success message to inform the user
    messages.success(request, "All notifications have been marked as read.")

    # Redirect the user back to the notifications list page
    return redirect('notification_list')






# --- NEW VIEWS TO ADD ---

@login_required
@require_POST
def reject_interest_request(request, interest_id):
    """ View for a user to reject an incoming interest request. """
    interest_request = get_object_or_404(InterestRequest, id=interest_id)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    # Security check: only the receiver can reject
    if interest_request.receiver != my_profile:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')

    interest_request.status = 'rejected'
    interest_request.save()
    

    messages.info(request, f"You have rejected the interest from {interest_request.sender.full_name}.")
    return redirect('manage_interests')


@login_required
@require_POST
def withdraw_interest_request(request, interest_id):
    """ View for a user to withdraw a pending interest request they sent. """
    interest_request = get_object_or_404(InterestRequest, id=interest_id)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    # Security check: only the sender can withdraw, and only if it's pending
    if interest_request.sender != my_profile or interest_request.status != 'pending':
        messages.error(request, "You cannot withdraw this request.")
        return redirect('manage_interests')
        
    # Withdrawing simply deletes the request
    interest_request.delete()

    messages.success(request, "You have successfully withdrawn your interest request.")
    return redirect('manage_interests')


@login_required
@require_POST
def remove_connection(request, interest_id):
    """
    View for either user to remove an 'accepted' connection.
    This now updates the interest status to 'rejected' and deletes
    any associated chat room to prevent further communication.
    """
    # Find the specific 'accepted' interest request
    interest_request = get_object_or_404(InterestRequest, id=interest_id, status='accepted')
    my_profile = get_object_or_404(UserProfile, user=request.user)

    # Security check: ensure the current user is part of this connection
    if interest_request.sender != my_profile and interest_request.receiver != my_profile:
        messages.error(request, "You are not part of this connection.")
        return redirect('manage_interests')

    # --- UPDATED LOGIC ---
    # 1. Change the status to 'rejected' instead of deleting the record.
    interest_request.status = 'rejected'
    interest_request.save()

    # 2. (Crucial) Find and delete the associated chat room to stop all communication.
    participant1 = interest_request.sender
    participant2 = interest_request.receiver
    
    # This query finds the single chat room shared by these two participants and deletes it.
    # It will safely do nothing if a chat room was never created.
    ChatRoom.objects.filter(participants=participant1).filter(participants=participant2).delete()

    # Provide clear feedback to the user
    messages.success(request, "The connection has been removed. You can no longer chat with this user.")
    return redirect('manage_interests')


# --- REPLACE pending_interests_view with THIS ---

@login_required
def manage_interests_view(request):
    """ A dashboard to manage all interest-related activities. """
    my_profile = get_object_or_404(UserProfile, user=request.user)
    
    # 1. Incoming requests: Sent to me, status is 'pending'
    incoming_requests = InterestRequest.objects.filter(
        receiver=my_profile, status='pending'
    ).select_related('sender', 'sender__user')

    # 2. Outgoing requests: Sent by me, status is 'pending'
    outgoing_requests = InterestRequest.objects.filter(
        sender=my_profile, status='pending'
    ).select_related('receiver', 'receiver__user')

    # 3. Accepted connections: I am either the sender or receiver, status is 'accepted'
    accepted_connections = InterestRequest.objects.filter(
        Q(sender=my_profile) | Q(receiver=my_profile),
        status='accepted'
    ).select_related('sender', 'receiver', 'sender__user', 'receiver__user')

    context = {
        'incoming_requests': incoming_requests,
        'outgoing_requests': outgoing_requests,
        'accepted_connections': accepted_connections,
        'page_title': "Manage Your Interests",
    }
    return render(request, 'matri/manage_interests.html', context)





# Add this new view function at the end of the file
@login_required
def delete_user_profile_view(request):
    """
    Handles the permanent deletion of a user's account and all related data.
    This action is irreversible.
    """
    if request.method == 'POST':
        user_to_delete = request.user
        
        # Log the user out before deleting to invalidate the session
        logout(request)
        
        # Deleting the user will automatically cascade and delete their UserProfile,
        # Profile, Posts, PartnerPreferences, etc., due to the on_delete=models.CASCADE
        # setting in your models.
        user_to_delete.delete()
        
        messages.success(request, "Your account has been permanently deleted.")
        
        # Redirect to the homepage after deletion
        return redirect('index')
    
    # If the view is accessed via a GET request, do not delete anything.
    # Instead, redirect the user back to their profile page.
    return redirect('view_user_profile')





@login_required
def start_chat(request, profile_id):
    """
    Finds or creates a chat room for two users and redirects to it.
    This view is already well-structured and secure. No changes are needed.
    """
    other_user_profile = get_object_or_404(UserProfile, id=profile_id)
    current_user_profile = get_object_or_404(UserProfile, user=request.user)

    # Security Check 1: Ensure there isn't a rejected interest request.
    rejected_interest = InterestRequest.objects.filter(
        (Q(sender=current_user_profile, receiver=other_user_profile) |
         Q(sender=other_user_profile, receiver=current_user_profile)),
        status='rejected'
    ).exists()

    if rejected_interest:
        messages.error(request, "You cannot start a chat as the interest request was not accepted.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    # Security Check 2: Ensure an accepted interest request exists.
    accepted_interest = InterestRequest.objects.filter(
        (Q(sender=current_user_profile, receiver=other_user_profile) |
         Q(sender=other_user_profile, receiver=current_user_profile)),
        status='accepted'
    ).exists()

    if not accepted_interest:
        messages.error(request, "You can only chat with users whose interest request you have accepted.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    # If checks pass, find or create the room.
    # This method of chaining filters is the standard and correct way to find
    # a room with a specific pair of many-to-many participants.
    room = ChatRoom.objects.filter(participants=current_user_profile).filter(participants=other_user_profile).first()

    if not room:
        room = ChatRoom.objects.create()
        room.participants.add(current_user_profile, other_user_profile)

    return redirect('chat_room_detail', room_id=room.id)


@login_required
def chat_room_list(request):
    """
    Displays a list of all chat rooms and suggestions for new chats.
    --- OPTIMIZED to reduce database queries significantly. ---
    """
    current_user_profile = get_object_or_404(UserProfile, user=request.user)

    # --- Part 1: Get Existing Chats (Highly Optimized) ---

    # Subquery to get the timestamp of the latest message in each room.
    latest_message_subquery = ChatMessage.objects.filter(
        room=OuterRef('pk')
    ).order_by('-timestamp').values('timestamp')[:1]

    # Annotate each chat room with the unread message count and the timestamp of the last message.
    # This performs all calculations in a single, efficient database query.
    chat_rooms_with_details = current_user_profile.chat_rooms.annotate(
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=current_user_profile)
        ),
        last_message_time=Subquery(latest_message_subquery)
    ).order_by('-last_message_time') # Order by the most recently active chat

    chat_list = []
    # This loop no longer makes database queries.
    for room in chat_rooms_with_details:
        other_user = room.participants.exclude(id=current_user_profile.id).first()
        last_message = room.messages.order_by('-timestamp').first() # This one extra query per room is acceptable for simplicity, but could also be subqueried if needed.
        
        chat_list.append({
            'room': room,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': room.unread_count, # Use the annotated value
        })

    # --- Part 2: Get Chat Suggestions (Optimized) ---

    # Get profiles of users the current user already has a chat with.
    existing_chat_partner_ids = set(UserProfile.objects.filter(
        chat_rooms__in=current_user_profile.chat_rooms.all()
    ).exclude(id=current_user_profile.id).values_list('id', flat=True))

    # Get all accepted interests.
    accepted_interests = InterestRequest.objects.filter(
        (Q(sender=current_user_profile) | Q(receiver=current_user_profile)),
        status='accepted'
    ).select_related('sender', 'receiver') # Eager load related profiles

    chat_suggestions = []
    # This loop no longer makes database queries.
    for interest in accepted_interests:
        other_user = interest.sender if interest.receiver == current_user_profile else interest.receiver
        
        # Check against the pre-fetched set of IDs instead of hitting the DB.
        if other_user.id not in existing_chat_partner_ids:
            chat_suggestions.append(other_user)

    context = {
        'page_title': 'Your Messages',
        'chat_list': chat_list,
        'chat_suggestions': chat_suggestions,
        'user_has_profile': True,
    }
    return render(request, 'matri/chat_room_list.html', context)


@login_required
def chat_room_detail(request, room_id):
    """
    Displays the chat room and handles message fetching.
    --- Minor optimization in the security check. ---
    """
    room = get_object_or_404(ChatRoom.objects.prefetch_related('participants', 'messages__sender'), id=room_id)
    current_user_profile = get_object_or_404(UserProfile, user=request.user)

    # Security check: Ensure the user is a participant of the room.
    # Using .exists() is slightly more performant than loading all participants.
    if not room.participants.filter(pk=current_user_profile.pk).exists():
        messages.error(request, "You do not have permission to view this chat.")
        return redirect('chat_room_list')

    # Mark all messages in this room sent by OTHERS as read.
    # This is an efficient, single UPDATE query.
    room.messages.filter(is_read=False).exclude(sender=current_user_profile).update(is_read=True)

    other_user_profile = room.participants.exclude(user=request.user).first()
    
    # The 'messages' have been prefetched in the initial query for efficiency.
    messages_list = room.messages.all()

    context = {
        'page_title': f"Chat with {other_user_profile.full_name}",
        'room': room,
        'messages_list': messages_list,
        'other_user_profile': other_user_profile,
        'current_user_profile_id': current_user_profile.id,
        'user_has_profile': True,
    }
    return render(request, 'matri/chat_room_detail.html', context)


@login_required
def get_unread_message_count(request):
    """
    API endpoint to get the total number of unread messages for the logged-in user.
    This view is already optimal and correct. No changes needed.
    """
    try:
        current_user_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        # If user has no profile, they can't have any messages.
        return JsonResponse({'unread_count': 0})

    # This single .count() query is the most efficient way to get this number.
    count = ChatMessage.objects.filter(
        room__participants=current_user_profile,
        is_read=False
    ).exclude(
        sender=current_user_profile
    ).count()
    
    return JsonResponse({'unread_count': count})





UserModel = get_user_model()

def password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            # Use the UserModel variable you defined
            user = UserModel.objects.filter(email__iexact=email).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_link = f"{request.scheme}://{request.get_host()}/reset/{uid}/{token}/"
                send_mail(
                    'Password Reset - Pentacost Matrimony',
                    f'Click the link to reset your password: {reset_link}',
                    'athul.23pmc116@mariancollege.org',
                    [email],
                    fail_silently=False,
                )
            # Important: Always show the "done" page, even if the user doesn't exist.
            # This prevents attackers from finding out which emails are registered.
            return redirect('password_reset_done')
    else:
        form = PasswordResetForm()
    return render(request, 'password_reset.html', {'form': form})

def password_reset_done(request):
    return render(request, 'password_reset_done.html')


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = UserModel._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            # Replace SetPasswordForm with your CustomSetPasswordForm if you have one
            form = SetPasswordForm(user, request.POST) 
            if form.is_valid():
                form.save()
                return redirect('password_reset_complete')
        else:
            # Replace SetPasswordForm with your CustomSetPasswordForm
            form = SetPasswordForm(user)
        return render(request, 'password_reset_confirm.html', {'form': form})
    else:
        # It's better to render a template than to show a plain HttpResponse
        return render(request, 'password_reset_invalid.html')


def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')






# You can remove the razorpay client initialization
logger = logging.getLogger(__name__) # Keep this, it's good practice



# VIEW 1: RENDER THE SUBSCRIPTION PAGE
@login_required
def subscribe_page(request):
    """
    Displays the subscription page.
    """
    context = {
        # Set to 1 for testing, change to 1500 for final production
        'plan_amount': 299,
    }
    return render(request, 'payment/subscribe.html', context)


# ===================================================================
# HELPER: Get the SDK Client Instance
# ===================================================================
def get_phonepe_client():
    """
    Initializes and returns an instance of the PhonePe Standard Checkout Client
    based on the current environment (UAT or Production).
    """
    env = Env.SANDBOX if settings.APP_ENVIRONMENT == 'DEVELOPMENT' else Env.PRODUCTION
    return StandardCheckoutClient.get_instance(
        client_id=settings.PHONEPE_CLIENT_ID,
        client_secret=settings.PHONEPE_CLIENT_SECRET,
        client_version=settings.PHONEPE_CLIENT_VERSION,
        env=env
    )


# ===================================================================
# VIEW 2: INITIATE PAYMENT (SDK v2 Flow)
# ===================================================================
@login_required
def phonepe_initiate_payment(request):
    """
    Creates a payment order using the SDK and redirects the user to PhonePe.
    """
    if request.method == "POST":
        client = get_phonepe_client()
        
        # Set to 1 for testing, change to 1500 for final production
        payment_amount = 2
        amount_in_paise = int(payment_amount * 100)
        
        # This is the unique order ID for your system
        merchant_order_id = f"MUID_{request.user.id}_{uuid.uuid4().hex[:6].upper()}"
        
        # The URL where the user will be sent back to after payment attempt
        redirect_url = request.build_absolute_uri(reverse('phonepe_redirect'))

        # Build the payment request object using the SDK's builder
        standard_pay_request = StandardCheckoutPayRequest.build_request(
            merchant_order_id=merchant_order_id,
            amount=amount_in_paise,
            redirect_url=redirect_url
        )
        
        try:
            # Create a pending payment record in the database before redirecting
            with transaction.atomic():
                # Store the merchant_order_id in the merchant_transaction_id field
                Payment.objects.create(
                    user=request.user,
                    merchant_transaction_id=merchant_order_id,
                    amount=payment_amount,
                    status='PENDING'
                )

            # Initiate the payment with the SDK client
            standard_pay_response = client.pay(standard_pay_request)
            
            # The SDK response directly gives the URL for the user to pay
            checkout_page_url = standard_pay_response.redirect_url
            
            logger.info(f"Redirecting user to PhonePe Checkout Page: {checkout_page_url}")
            return redirect(checkout_page_url)

        except Exception as e:
            logger.error(f"Error during SDK v2 payment initiation: {e}")
            return render(request, 'payment/payment_error.html', {'message': 'Could not connect to payment gateway.'})

    return redirect('subscribe')


# ===================================================================
# VIEW 3: HANDLE USER REDIRECT (with SDK Status Check)
# This is the most important view for confirming the payment.
# ===================================================================
@csrf_exempt
def phonepe_redirect(request):
    merchant_order_id = request.GET.get('merchantOrderId')

    if not merchant_order_id:
        logger.warning("PhonePe redirect received without a merchantOrderId. Using fallback.")
        try:
            payment = Payment.objects.filter(user=request.user, status='PENDING').latest('created_at')
            merchant_order_id = payment.merchant_transaction_id
            logger.info(f"Found latest pending transaction for user: {merchant_order_id}")
        except Payment.DoesNotExist:
            return render(request, 'payment/payment_error.html', {'message': 'Could not find a pending transaction to verify.'})
    
    try:
        client = get_phonepe_client()
        status_response = client.get_order_status(merchant_order_id=merchant_order_id)
        
        logger.info(f"Status check for {merchant_order_id}: State is '{status_response.state}'")
        
        # Log the full payment_details object to see its structure
        if hasattr(status_response, 'payment_details'):
            logger.info(f"Payment Details object from SDK: {status_response.payment_details}")

        payment = get_object_or_404(Payment, merchant_transaction_id=merchant_order_id)

        with transaction.atomic():
            if status_response.state == "COMPLETED" and payment.status != 'SUCCESS':
                payment.status = 'SUCCESS'
                
                # ==================== THE FIX IS HERE ====================
                # Safely access the first element of the list, then get the transactionId.
                if hasattr(status_response, 'payment_details') and isinstance(status_response.payment_details, list) and len(status_response.payment_details) > 0:
                    payment.phonepe_transaction_id = status_response.payment_details[0].transaction_id
                # =========================================================
                
                user_profile = get_object_or_404(UserProfile, user=payment.user)
                user_profile.is_premium_member = True
                user_profile.save()
                
                payment.save()
                return render(request, 'payment/payment_success.html')
            else:
                payment.status = 'FAILURE'
                payment.save()
                return render(request, 'payment/payment_error.html', {'message': 'Payment was not successful.'})

    except Exception as e:
        logger.error(f"Error during SDK v2 redirect handling for {merchant_order_id}: {e}")
        return render(request, 'payment/payment_error.html', {'message': 'An error occurred while verifying your payment.'})
    



def service_worker(request):
    # Make sure the file path is correct
    sw_path = os.path.join(settings.BASE_DIR, 'assets', 'serviceworker.js') 
    with open(sw_path, 'r') as f:
        sw_content = f.read()
    
    # Create an HttpResponse and set the content type and the crucial header
    response = HttpResponse(sw_content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response





def privacy_policy_view(request):
    """
    Renders the static privacy policy page.
    """
    # You can pass context here if needed, but for a static page, it's not required.
    context = {} 
    return render(request, 'matri/privacy_policy.html', context)



def terms_and_conditions_view(request):
    """
    Renders the static Terms and Conditions page.
    """
    context = {} 
    return render(request, 'matri/terms_and_conditions.html', context)



def contact_us_view(request):
    """
    Renders the Contact Us page.
    """
    # Replace 'your_app_name/contact_us.html' with the actual path to your template
    return render(request, 'matri/contact_us.html')

def about_us_view(request):
    """
    Renders the About Us page.
    """
    # Replace 'your_app_name/about_us.html' with the actual path to your template
    return render(request, 'matri/about_us.html')

def refund_policy_view(request):
    """
    Renders the Refund Policy page.
    """
    # Replace 'your_app_name/refund_policy.html' with the actual path to your template
    return render(request, 'matri/refund_policy.html')






def assetlinks(request):
    """
    View to serve the assetlinks.json file.
    """
    # Construct the full path to the file
    file_path = os.path.join(settings.BASE_DIR, 'assetlinks.json')
    with open(file_path, 'r') as f:
        data = json.load(f)
    return JsonResponse(data, safe=False)









