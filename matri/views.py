# views.py

import os
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse_lazy, reverse
from .models import ChatRoom, Profile, UserProfile, UserPost
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
import random
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
from .models import Notification
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
from webpush.models import SubscriptionInfo, PushInformation, Group
from firebase_admin import auth



# ... (generate_username, register_view, login_view, logout_view remain the same as your last version) ...
def generate_username():
    base = 'user'
    suffix = ''.join(random.choices(string.digits, k=4))
    username = base + suffix
    while User.objects.filter(username=username).exists():
        suffix = ''.join(random.choices(string.digits, k=4))
        username = base + suffix
    return username


def register_view(request):
    if request.user.is_authenticated:
        try:
            UserProfile.objects.get(user=request.user)
            return redirect('index') 
        except UserProfile.DoesNotExist:
            return redirect('create_user_profile') 

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        form_data = request.POST 

        if not all([name, email, phone, password, confirm_password]):
            messages.error(request, "All fields are required.")
            return render(request, 'matri/register.html', {'form_data': form_data})
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'matri/register.html', {'form_data': form_data})
        
        if '@' not in email or '.' not in email.split('@')[-1]:
            messages.error(request, "Enter a valid email address.")
            return render(request, 'matri/register.html', {'form_data': form_data})
        
        if not phone.isdigit() or not (10 <= len(phone) <= 15):
            messages.error(request, "Phone number must be 10-15 digits.")
            return render(request, 'matri/register.html', {'form_data': form_data})
        
        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email is already registered.")
            return render(request, 'matri/register.html', {'form_data': form_data})

        # Check if the phone number is already used
        if Profile.objects.filter(phone=phone).exists():
            messages.error(request, "Phone number is already registered.")
            return render(request, 'matri/register.html', {'form_data': form_data})

        username = generate_username()
        try:
            user = User.objects.create_user(username=username, password=password, email=email)
            user.first_name = name
            user.save()
            Profile.objects.create(user=user, phone=phone)
            messages.success(request, f"Registered successfully. Your username is {username}. Please login.")
            return redirect('login')
        except Exception as e:
            messages.error(request, f"An error occurred during registration: {e}")
            return render(request, 'matri/register.html', {'form_data': form_data})

    return render(request, 'matri/register.html')



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
    # --- Define default values for all variables first ---
    user_has_profile = False
    unread_notifications_count = 0
    unread_messages_count = 0 # NEW: Default to 0 for unread messages

    # Check the user's status
    if request.user.is_authenticated:
        try:
            # This checks if the logged-in user has a profile
            user_profile = UserProfile.objects.get(user=request.user)
            user_has_profile = True

            # NEW: Calculate unread messages count if profile exists
            # Counts messages in rooms the user is part of, which are unread and not sent by the user.
            unread_messages_count = ChatMessage.objects.filter(
                room__participants=user_profile,
                is_read=False
            ).exclude(
                sender=user_profile
            ).count()

        except UserProfile.DoesNotExist:
            # User is logged in but has no profile
            user_has_profile = False

        # Get notification count for any authenticated user, regardless of profile status.
        unread_notifications_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    # Get featured profiles for the homepage
    featured_profiles = UserProfile.objects.filter(
        is_profile_in_index=True,
        profile_picture__isnull=False
    ).exclude(
        profile_picture=''
    ).distinct().order_by('?')[:8] # Added back a limit to avoid loading too many profiles

    # Now, all context variables are guaranteed to have a value.
    context = {
        'featured_profiles': featured_profiles,
        'user_has_profile': user_has_profile,
        'unread_notifications_count': unread_notifications_count, # Using existing descriptive name
        'unread_messages_count': unread_messages_count, # NEW: Add to context
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
    current_user_profile = None
    try:
        current_user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.warning(request, "Please create your profile before searching for others.")
        return redirect('create_user_profile') # Ensure 'create_user_profile' is a valid URL name

    results_queryset = UserProfile.objects.exclude(user=request.user).select_related('user')
    form_submitted_with_data = False

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
            form_submitted_with_data = any(
                cleaned_data.get(key) for key in cleaned_data if key not in ['search_type', 'gender'] or (key == 'gender' and cleaned_data.get(key))
            )

            if search_type == 'username_search':
                username_query = cleaned_data.get('username_search')
                if username_query:
                    results_queryset = results_queryset.filter(user__username__iexact=username_query)
                else:
                    results_queryset = UserProfile.objects.none()
            
            elif search_type == 'advanced_search':
                if cleaned_data.get('gender'):
                    results_queryset = results_queryset.filter(gender=cleaned_data.get('gender'))
                
                today = date.today()
                age_min, age_max = cleaned_data.get('age_min'), cleaned_data.get('age_max')
                if age_min:
                    results_queryset = results_queryset.filter(date_of_birth__lte=date(today.year - age_min, today.month, today.day))
                if age_max:
                    # To ensure someone who just turned age_max+1 is excluded
                    # date_of_birth must be greater than (today - (age_max + 1) years)
                    # effectively meaning they are age_max or younger.
                    results_queryset = results_queryset.filter(date_of_birth__gt=date(today.year - (age_max + 1), today.month, today.day))
                
                if cleaned_data.get('marital_status'):
                    results_queryset = results_queryset.filter(marital_status=cleaned_data.get('marital_status'))
                if cleaned_data.get('height_min'):
                    results_queryset = results_queryset.filter(height__gte=cleaned_data.get('height_min'))
                if cleaned_data.get('height_max'):
                    results_queryset = results_queryset.filter(height__lte=cleaned_data.get('height_max'))
                if cleaned_data.get('weight_min_kg'):
                    results_queryset = results_queryset.filter(weight__gte=cleaned_data.get('weight_min_kg'))
                if cleaned_data.get('weight_max_kg'):
                    results_queryset = results_queryset.filter(weight__lte=cleaned_data.get('weight_max_kg'))
                
                # --- Enhanced Profession Search with Groq AI ---
                profession_query_str = cleaned_data.get('profession')
                if profession_query_str:
                    user_entered_professions = [p.strip() for p in profession_query_str.split(',') if p.strip()]
                    
                    if user_entered_professions:
                        # 1. Get all unique individual professions from the database
                        all_db_profession_entries = UserProfile.objects.filter( 
                            profession__isnull=False
                        ).exclude(profession__exact='').values_list('profession', flat=True).distinct()
                        
                        print(f"DEBUG: Raw profession entries from DB: {list(all_db_profession_entries)}")
                        
                        unique_individual_db_professions = set()
                        for entry in all_db_profession_entries:
                            # Handle comma-separated professions in DB field
                            for p_item in entry.split(','): 
                                cleaned_p_item = p_item.strip()
                                if cleaned_p_item:
                                    unique_individual_db_professions.add(cleaned_p_item)
                        
                        unique_db_professions_list = list(unique_individual_db_professions)
                        print(f"DEBUG: Unique professions extracted: {unique_db_professions_list}")

                        if not unique_db_professions_list:
                            # No professions in DB to compare against, fallback to simple icontains
                            print("DEBUG: No unique professions in DB. Falling back to icontains for profession search.")
                            q_objects_prof = Q()
                            for term in user_entered_professions:
                                q_objects_prof |= Q(profession__icontains=term)
                            results_queryset = results_queryset.filter(q_objects_prof)
                        else:
                            # 2. Try Groq AI for each user-entered term
                            all_groq_matched_professions = set()
                            groq_call_failed_for_any_term = False

                            for search_term in user_entered_professions:
                                print(f"DEBUG: Processing search term: '{search_term}'")
                                related_terms_from_groq = get_related_professions_groq(search_term, unique_db_professions_list)
                                
                                if related_terms_from_groq is None: # Groq API call failed
                                    groq_call_failed_for_any_term = True
                                    print(f"DEBUG: Groq call failed for term '{search_term}'. Switching to fallback for all profession terms.")
                                    break 
                                # If related_terms_from_groq is an empty list, it means Groq ran but found no matches for this term.
                                # This is a valid outcome, so we add its (empty) content.
                                for term in related_terms_from_groq:
                                    all_groq_matched_professions.add(term)
                            
                            if groq_call_failed_for_any_term:
                                # Fallback to simple icontains for all user-entered terms
                                print("DEBUG: Fallback: Using 'icontains' for all entered profession terms due to Groq failure.")
                                q_objects_prof = Q()
                                for term in user_entered_professions:
                                    q_objects_prof |= Q(profession__icontains=term)
                                results_queryset = results_queryset.filter(q_objects_prof)
                            else:
                                # Groq processed all terms (successfully or found no matches for some/all)
                                if all_groq_matched_professions:
                                    print(f"DEBUG: Groq search: Using matched professions: {list(all_groq_matched_professions)}")
                                    
                                    # Debug: Let's see what professions actually exist in the database
                                    actual_db_professions = UserProfile.objects.filter(
                                        profession__isnull=False
                                    ).exclude(profession__exact='').values_list('profession', flat=True)
                                    
                                    print(f"DEBUG: Actual profession values in DB: {list(actual_db_professions)}")
                                    
                                    # Check which profiles would match each Groq-identified profession
                                    for groq_term in all_groq_matched_professions:
                                        matching_profiles = results_queryset.filter(profession__icontains=groq_term)
                                        print(f"DEBUG: Profession '{groq_term}' matches {matching_profiles.count()} profiles")
                                        for profile in matching_profiles[:3]:  # Show first 3 matches
                                            print(f"  - Profile ID {profile.id}: profession='{profile.profession}'")
                                    
                                    # Enhanced matching for comma-separated profession fields
                                    q_objects_prof = Q()
                                    for p_term in all_groq_matched_professions:
                                        # Handle different formats of profession storage
                                        # This covers: "Teacher", "Doctor, Teacher", "Teacher, Nurse", etc.
                                        q_objects_prof |= (
                                            Q(profession__icontains=p_term) |  # General contains
                                            Q(profession__iregex=r'\b' + re.escape(p_term) + r'\b')  # Word boundary match
                                        )
                                    
                                    # Apply the filter and debug
                                    results_before_filter = results_queryset.count()
                                    results_queryset = results_queryset.filter(q_objects_prof)
                                    results_after_filter = results_queryset.count()
                                    
                                    print(f"DEBUG: Results before profession filter: {results_before_filter}")
                                    print(f"DEBUG: Results after profession filter: {results_after_filter}")
                                    
                                    # Show some matching profiles for debugging
                                    if results_queryset.exists():
                                        print("DEBUG: Sample matching profiles:")
                                        for profile in results_queryset[:3]:
                                            print(f"  - {profile.user.username}: '{profile.profession}'")
                                    else:
                                        print("DEBUG: No profiles found after applying profession filter")
                                        
                                        # Additional debugging - try direct search
                                        print("\nDEBUG: Trying direct profession searches:")
                                        for p_term in all_groq_matched_professions:
                                            direct_matches = UserProfile.objects.filter(
                                                profession__icontains=p_term
                                            ).exclude(user=request.user)
                                            print(f"  Direct search for '{p_term}': {direct_matches.count()} matches")
                                            for match in direct_matches[:2]:
                                                print(f"    - {match.user.username}: '{match.profession}'")

                                else:
                                    # Groq ran for all terms but found no matches for any of them.
                                    # This implies no profiles match the semantic search.
                                    print("DEBUG: Groq processed all terms but found no related professions. Filtering for no results.")
                                    results_queryset = results_queryset.none() 
                # --- End of Enhanced Profession Search ---

                if cleaned_data.get('drinking'):
                    results_queryset = results_queryset.filter(drinking=cleaned_data.get('drinking'))
                if cleaned_data.get('smoking'):
                    results_queryset = results_queryset.filter(smoking=cleaned_data.get('smoking'))
                if cleaned_data.get('family_type'):
                    results_queryset = results_queryset.filter(family_type=cleaned_data.get('family_type'))
            
            else: # Invalid search_type or no search_type
                if request.GET: # If there was an attempt to submit GET data
                    messages.warning(request, "Invalid search attempt.")
                results_queryset = UserProfile.objects.none()

            if not results_queryset.exists() and form_submitted_with_data:
                messages.info(request, "")
        
        else: # Form is not valid
            was_attempted_submit = any(val for key, val in request.GET.items() if key != 'search_type' and val)
            if was_attempted_submit:
                messages.error(request, "There were errors in your search criteria. Please check the form.")
            results_queryset = UserProfile.objects.none() # No results if form is invalid
    else: # Not a GET request (initial page load without search)
        results_queryset = UserProfile.objects.none() # Show no results by default

    context = {
        'form': form,
        'results': results_queryset,
        'user_has_profile': True, # Assuming this is set correctly elsewhere if needed
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
    
    # --- START OF LIKED POSTS LOGIC ---
    user_posts_to_view = UserPost.objects.filter(user_profile=profile_to_view).order_by('-created_at')

    # Get a list of post IDs from the gallery that the current user has liked
    liked_post_ids = set(
        Notification.objects.filter(
            sender=request.user, 
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
    contact_phone = None  # <<< NEW: Initialize phone number variable
    
    interest_lookup = InterestRequest.objects.filter(
        (Q(sender=my_profile) & Q(receiver=profile_to_view)) |
        (Q(sender=profile_to_view) & Q(receiver=my_profile))
    ).first()

    if interest_lookup:
        interest_request_obj = interest_lookup
        if interest_lookup.status == 'accepted':
            interest_status = 'accepted'
            # <<< START OF NEW LOGIC >>>
            # If interest is accepted, try to get the phone number from the related Profile model.
            try:
                # The phone number is in the Profile model, linked via the User model
                basic_profile = Profile.objects.get(user=profile_to_view.user)
                contact_phone = basic_profile.phone
            except Profile.DoesNotExist:
                # Handle the case where a basic Profile object might not exist for the user
                contact_phone = "Not Provided"
            # <<< END OF NEW LOGIC >>>

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
        'contact_phone': contact_phone,  # <<< NEW: Add phone to context
    }
    return render(request, 'matri/view_other_user_profile.html', context)





# ... (your existing views) ...

@login_required
def post_feed_view(request):
    try:
        # Get the profile of the logged-in user
        logged_in_user_profile = UserProfile.objects.select_related('user').get(user=request.user)
    except UserProfile.DoesNotExist:
        # If profile doesn't exist, redirect to profile creation page
        messages.warning(request, "Please create your profile to view the feed.")
        return redirect('create_user_profile') 

    # Determine the gender of the logged-in user to filter the feed
    logged_in_user_gender = logged_in_user_profile.gender
    
    # Q object for the logged-in user's own posts to ensure they appear in their feed
    own_posts_q = Q(user_profile=logged_in_user_profile)
    
    # Q object for posts from the "opposite" gender
    opposite_gender_posts_q = Q() 

    if logged_in_user_gender == 'Male':
        opposite_gender_posts_q = Q(user_profile__gender='Female')
    elif logged_in_user_gender == 'Female':
        opposite_gender_posts_q = Q(user_profile__gender='Male')
    elif logged_in_user_gender == 'Other':
         opposite_gender_posts_q = Q(user_profile__gender='Male') | Q(user_profile__gender='Female')
    
    # Combine the queries: show own posts OR posts from the determined opposite gender
    final_query = own_posts_q | opposite_gender_posts_q
        
    # Get all posts that match the filtering criteria
    # It's better practice to order by newest first for a feed than random ('?')
    all_posts_list = UserPost.objects.filter(final_query).select_related(
        'user_profile', 
        'user_profile__user'
    ).distinct().order_by('-created_at')

    # --- START OF FIX: Check which posts are liked by the current user ---

    # Get a set of post IDs from the feed that the current user has liked.
    # We filter by the specific 'like' message to be precise.
    liked_post_ids = set(
        Notification.objects.filter(
            sender=request.user,
            post_id__in=[post.id for post in all_posts_list], # Check only against posts in our feed
            message="liked your post"
        ).values_list('post_id', flat=True)
    )

    # Annotate each post object with a new attribute 'is_liked_by_user'.
    # The template will use this to decide which heart icon to show.
    for post in all_posts_list:
        post.is_liked_by_user = post.id in liked_post_ids
        
    # --- END OF FIX ---

    # Pagination
    paginator = Paginator(all_posts_list, 9) # Show 9 posts per page
    page_number = request.GET.get('page')
    
    # .get_page() is a safer way to handle pagination as it gracefully handles
    # invalid page numbers and empty pages.
    posts_page = paginator.get_page(page_number)

    context = {
        'posts_page': posts_page,
        'user_has_profile': True, # If this view is rendered, the user must have a profile
        'page_title': "Community Feed", 
    }
    return render(request, 'matri/post_feed.html', context)





# matri/views.py

# views.py

@login_required
@require_POST
def like_post(request, post_id):
    post = get_object_or_404(UserPost, id=post_id)
    
    # Keep this check as a security measure
    if post.user_profile.user == request.user:
        return JsonResponse({'status': 'error', 'message': 'Cannot like your own post'}, status=403)

    like_message = "liked your post"
    
    # Use a queryset to handle potential duplicates
    existing_notifications = Notification.objects.filter(
        sender=request.user,
        post=post,
        message=like_message
    )

    if existing_notifications.exists():
        # This will delete ALL matching notifications, ensuring a clean "unlike"
        existing_notifications.delete()
        action = 'unliked'
    else:
        Notification.objects.create(
            recipient=post.user_profile.user,
            sender=request.user,
            post=post,
            message=like_message
        )
        action = 'liked'

    return JsonResponse({'status': 'success', 'action': action})
    




@login_required
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user, is_read=False) \
                                     .select_related('sender__userprofile', 'post') \
                                     .order_by('-created_at')

    serialized_notifications = []
    for n in notifications:
        sender_profile_pic_url = None
        sender_display_name = n.sender.username
        sender_profile_id = None

        if hasattr(n.sender, 'userprofile') and n.sender.userprofile:
            user_profile = n.sender.userprofile
            if user_profile.profile_picture:
                sender_profile_pic_url = user_profile.profile_picture.url
            if user_profile.full_name:
                sender_display_name = user_profile.full_name
            sender_profile_id = user_profile.id

        click_action_url = "#"
        message_text = n.message

        if "sent you a message" in n.message and sender_profile_id:
            # Find the chat room between the sender and recipient
            current_user_profile = UserProfile.objects.get(user=request.user)
            sender_profile = UserProfile.objects.get(id=sender_profile_id)
            room = ChatRoom.objects.filter(participants=current_user_profile).filter(participants=sender_profile).first()
            if room:
                click_action_url = f"/messages/room/{room.id}/"
        elif "interest request" in n.message and sender_profile_id:
            click_action_url = f"/profile/view/{sender_profile_id}/"
        elif n.post:
            click_action_url = f"/profile/view/{sender_profile_id}/" # Or a link to the post itself
        elif sender_profile_id:
            click_action_url = f"/profile/view/{sender_profile_id}/"

        full_message_html = f"<strong>{sender_display_name}</strong> {message_text}"

        serialized_notifications.append({
            'id': n.id,
            'message_html': full_message_html,
            'sender_profile_pic_url': sender_profile_pic_url,
            'post_preview_url': n.post.image.url if n.post and n.post.image else None,
            'click_action_url': click_action_url,
            'created_at': n.created_at.strftime("%b %d, %Y %I:%M %p")
        })

    count = len(serialized_notifications)
    return JsonResponse({
        'count': count,
        'notifications': serialized_notifications
    })



@login_required
@require_POST # Make sure this view only accepts POST requests
def mark_notification_read(request, notification_id): # Ensure this is @require_POST
    try:
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)

# If you haven't implemented mark_all_notifications_read, add it:
@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success', 'message': 'All notifications marked as read.'})






@login_required
@require_POST
def send_interest_request(request, profile_id):
    # This view is correct, no changes needed
    sender_profile = get_object_or_404(UserProfile, user=request.user)
    receiver_profile = get_object_or_404(UserProfile, id=profile_id)

    if sender_profile == receiver_profile:
        messages.error(request, "You cannot send an interest request to yourself.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    if InterestRequest.objects.filter(sender=sender_profile, receiver=receiver_profile).exists() or \
       InterestRequest.objects.filter(sender=receiver_profile, receiver=sender_profile).exists():
        messages.warning(request, "An interest request already exists with this user.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    InterestRequest.objects.create(sender=sender_profile, receiver=receiver_profile, status='pending')
    Notification.objects.create(
        recipient=receiver_profile.user,
        sender=request.user,
        message=f"{sender_profile.full_name} sent you an interest request.",
        post=None
    )
    
    messages.success(request, f"Your interest has been sent to {receiver_profile.full_name}.")
    return redirect('view_other_user_profile', profile_id=profile_id)


@login_required
@require_POST
def accept_interest_request(request, interest_id):
    # This view is mostly correct, just changing the redirect
    interest_request = get_object_or_404(InterestRequest, id=interest_id)
    my_profile = get_object_or_404(UserProfile, user=request.user)

    if interest_request.receiver != my_profile:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')

    interest_request.status = 'accepted'
    interest_request.save()

    Notification.objects.create(
        recipient=interest_request.sender.user,
        sender=request.user,
        message=f"{my_profile.full_name} accepted your interest request!",
        post=None
    )

    messages.success(request, f"You have accepted the interest from {interest_request.sender.full_name}.\nNow you can see the contact number or chat with the user")
    # Redirect back to the new manage interests page
    return redirect('manage_interests')


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
    
    # You can optionally notify the sender of the rejection
    # Notification.objects.create(...)

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
    This view now prevents chatting if the interest request was rejected.
    """
    other_user_profile = get_object_or_404(UserProfile, id=profile_id)
    current_user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # --- NEW: Check for a rejected interest request first ---
    # Look for a request in either direction that has been rejected.
    rejected_interest = InterestRequest.objects.filter(
        (Q(sender=current_user_profile, receiver=other_user_profile) | 
         Q(sender=other_user_profile, receiver=current_user_profile)),
        status='rejected'
    ).exists()

    if rejected_interest:
        messages.error(request, "You cannot initiate a chat as the interest request was not accepted.")
        # Redirect back to the other user's profile page
        return redirect('view_other_user_profile', profile_id=profile_id)

    # --- EXISTING: Security check to ensure an accepted interest exists ---
    # This check remains crucial.
    accepted_interest = InterestRequest.objects.filter(
        (Q(sender=current_user_profile, receiver=other_user_profile) | 
         Q(sender=other_user_profile, receiver=current_user_profile)),
        status='accepted'
    ).exists()

    if not accepted_interest:
        messages.error(request, "You can only chat with users whose interest request you have accepted.")
        return redirect('view_other_user_profile', profile_id=profile_id)

    # If checks pass, find or create the room
    room = ChatRoom.objects.filter(participants=current_user_profile).filter(participants=other_user_profile).first()

    if not room:
        room = ChatRoom.objects.create()
        room.participants.add(current_user_profile, other_user_profile)

    return redirect('chat_room_detail', room_id=room.id)


@login_required
def chat_room_list(request):
    """
    Displays a list of all chat rooms the user is in, and suggestions to start new chats.
    This view's logic is already correct as it only suggests chats for 'accepted' interests.
    """
    current_user_profile = get_object_or_404(UserProfile, user=request.user)

    # Get existing chat rooms, ordered by the most recent message
    existing_chats = current_user_profile.chat_rooms.annotate(
        last_message_time=Max('messages__timestamp')
    ).order_by('-last_message_time')
    
    chat_list = []
    for room in existing_chats:
        other_user = room.participants.exclude(id=current_user_profile.id).first()
        last_message = room.messages.order_by('-timestamp').first()
        unread_count = room.messages.filter(is_read=False).exclude(sender=current_user_profile).count()
        chat_list.append({
            'room': room,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count
        })

    # Get accepted interests where a chat hasn't started yet.
    # This correctly filters out pending and rejected requests.
    accepted_interests = InterestRequest.objects.filter(
        (Q(sender=current_user_profile) | Q(receiver=current_user_profile)),
        status='accepted'
    )
    
    chat_suggestions = []
    for interest in accepted_interests:
        other_user = interest.sender if interest.receiver == current_user_profile else interest.receiver
        # Check if a chat room already exists for this pair
        if not ChatRoom.objects.filter(participants=current_user_profile).filter(participants=other_user).exists():
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
    """
    room = get_object_or_404(ChatRoom, id=room_id)
    current_user_profile = get_object_or_404(UserProfile, user=request.user)

    # Security check: Ensure the user is a participant of the room
    if current_user_profile not in room.participants.all():
        messages.error(request, "You do not have permission to view this chat.")
        return redirect('chat_room_list')

    # Mark messages as read
    room.messages.filter(is_read=False).exclude(sender=current_user_profile).update(is_read=True)

    other_user_profile = room.participants.exclude(user=request.user).first()
    messages_list = room.messages.all().order_by('timestamp')

    context = {
        'page_title': f"Chat with {other_user_profile.full_name}",
        'room': room,
        'messages_list': messages_list,
        'other_user_profile': other_user_profile,
        'current_user_profile_id': current_user_profile.id,
        'user_has_profile': True,
    }
    return render(request, 'matri/chat_room_detail.html', context)





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






# It's good practice to get a logger instance
logger = logging.getLogger(__name__)

# Initialize Razorpay client once
try:
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
except Exception as e:
    logger.critical(f"Failed to initialize Razorpay client: {e}")
    client = None

@login_required
def initiate_payment(request):
    """
    View to display the subscription page and create a Razorpay Order.
    Includes error handling for the API call.
    """
    if not client:
        # Handle case where Razorpay client failed to initialize
        # You might want to render an error page or a message
        # For now, let's add a message to the context
        context = {'error_message': 'Payment service is currently unavailable. Please try again later.'}
        return render(request, 'payment/subscribe.html', context)
        
    # It's better to store this in settings.py
    payment_amount = 500
    amount_in_paise = payment_amount * 100

    order_data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"receipt_user_{request.user.id}_{int(time.time())}", # More unique receipt
        "notes": {
            "plan": "Lifetime Premium",
            "user_id": request.user.id,
            "email": request.user.email
        }
    }

    try:
        # --- IMPROVEMENT 1: WRAP API CALL IN TRY/EXCEPT ---
        order = client.order.create(data=order_data)
        
        # Get user profile for pre-filling checkout form
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)

        context = {
            'razorpay_order_id': order['id'],
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'amount': order['amount'],
            'currency': order['currency'],
            'user_profile': user_profile,
            'user': request.user,
            'plan_amount': payment_amount,
        }
        return render(request, 'payment/subscribe.html', context)

    except Exception as e:
        # This will catch the ConnectionError and any other Razorpay API errors
        logger.error(f"Razorpay order creation failed for user {request.user.id}: {e}")
        context = {
            'error_message': 'Could not connect to the payment gateway. Please check your internet connection and try again.'
        }
        return render(request, 'payment/subscribe.html', context)


# --- IMPROVEMENT 3: REMOVED @csrf_exempt ---
# Your JS is sending the CSRF token, so this is more secure.
@login_required
def verify_payment(request):
    """
    View to verify the payment signature from Razorpay.
    Uses an atomic transaction to ensure data integrity.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_signature = data.get('razorpay_signature')
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }

            # Verify the payment signature
            client.utility.verify_payment_signature(params_dict)
            
            # --- IMPROVEMENT 2: USE ATOMIC TRANSACTION ---
            with transaction.atomic():
                # 1. Fetch the order details to get the correct amount
                order = client.order.fetch(razorpay_order_id)
                amount_paid = order['amount'] / 100 # Convert from paise to rupees

                # 2. Log the payment details in the Payment model
                Payment.objects.create(
                    user=request.user,
                    razorpay_order_id=razorpay_order_id,
                    razorpay_payment_id=razorpay_payment_id,
                    razorpay_signature=razorpay_signature,
                    amount=amount_paid
                )

                # 3. Update UserProfile to premium
                user_profile = UserProfile.objects.get(user=request.user)
                user_profile.is_premium_member = True
                user_profile.save()
            
            return JsonResponse({'status': 'success', 'message': 'Payment successful!'})

        except Exception as e:
            # --- IMPROVEMENT 4: BETTER ERROR LOGGING ---
            logger.error(f"Payment verification failed for user {request.user.id}: {e}")
            return JsonResponse({'status': 'failure', 'message': 'Payment verification failed. Please contact support.'}, status=400)
    
    return JsonResponse({'status': 'failure', 'message': 'Invalid request method.'}, status=405)






@login_required
def get_vapid_public_key(request):
    """Returns the VAPID public key."""
    public_key = settings.WEBPUSH_SETTINGS.get('VAPID_PUBLIC_KEY')
    return JsonResponse({'public_key': public_key})





@login_required
@csrf_exempt
def subscribe_to_push(request):
    """
    Subscribes a user to push notifications.
    This version uses the library's intended and simplest pattern.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    try:
        # 1. Get the subscription data
        subscription_data = json.loads(request.body)
        
        # 2. Get or create a Group for the user.
        # The library is designed to send notifications to Groups.
        # A "group" can just be one user. We'll name the group after the user's ID.
        group, created = Group.objects.get_or_create(name=f"user_{request.user.id}")

        # 3. Create a PushInformation object and add it to the user's group
        # This is the single step that creates the subscription and links it.
        PushInformation.objects.create(
            subscription_info=subscription_data,
            group=group
        )
        
        # We can also add the user directly if we want to use send_user_notification
        # This part is slightly redundant if using groups, but provides flexibility
        # and might be what send_user_notification looks for. Let's add it for safety.
        # First, find the PushInformation object we just made.
        push_info = PushInformation.objects.get(subscription_info=subscription_data)
        
        SubscriptionInfo.objects.get_or_create(
            user=request.user,
            push_information=push_info
        )

        return JsonResponse({'status': 'success', 'message': 'Subscription saved.'})

    except Exception as e:
        print(f"CRITICAL Error in subscribe_to_push: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': 'An unexpected server error occurred.'}, status=500)
    







def service_worker(request):
    # Make sure the file path is correct
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'serviceworker.js') 
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









