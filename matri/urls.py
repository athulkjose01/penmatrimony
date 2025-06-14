# urls.py
from django.urls import path
from . import views
from django.db.models import Q # Import Q object



urlpatterns = [
    path('', views.index_view, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('profile/create/', views.create_user_profile_view, name='create_user_profile'),
    path('profile/my/', views.view_user_profile_view, name='view_user_profile'), # For own profile
    path('profile/edit/', views.edit_user_profile_view, name='edit_user_profile'),
    path('search/', views.search_users_view, name='search_users'),
    # URL for viewing other users' profiles using UserProfile.id
    path('profile/view/<int:profile_id>/', views.view_other_user_profile_view, name='view_other_user_profile'),
    path('profile/add-post/', views.add_user_post_view, name='add_user_post'),
    path('post/delete/<int:post_id>/', views.delete_user_post_view, name='delete_user_post'),
    path('feed/', views.post_feed_view, name='post_feed'),
    path('like_post/<int:post_id>/', views.like_post, name='like_post'),
    path('get_notifications/', views.get_notifications, name='get_notifications'),
    path('mark_notification_read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark_all_notifications_read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('interests/', views.manage_interests_view, name='manage_interests'),
    path('profile/<int:profile_id>/send_interest/', views.send_interest_request, name='send_interest'),
    path('interests/accept/<int:interest_id>/', views.accept_interest_request, name='accept_interest'),
    path('interests/reject/<int:interest_id>/', views.reject_interest_request, name='reject_interest'),
    path('interests/withdraw/<int:interest_id>/', views.withdraw_interest_request, name='withdraw_interest'),
    path('interests/remove/<int:interest_id>/', views.remove_connection, name='remove_connection'),
    path('profile/delete/', views.delete_user_profile_view, name='delete_user_profile'),
    path('messages/', views.chat_room_list, name='chat_room_list'),
    path('messages/start/<int:profile_id>/', views.start_chat, name='start_chat'),
    path('messages/room/<int:room_id>/', views.chat_room_detail, name='chat_room_detail'),
    path('password_reset/', views.password_reset, name='password_reset'),
    path('password_reset/done/', views.password_reset_done, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete, name='password_reset_complete'),
    path('subscribe/', views.initiate_payment, name='subscribe'),
    path('payment/verify/', views.verify_payment, name='verify_payment'),
    path('webpush/key/', views.get_vapid_public_key, name='get_vapid_key'),
    path('webpush/subscribe/', views.subscribe_to_push, name='subscribe_to_push'),
    path('serviceworker.js', views.service_worker, name='service_worker'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-and-conditions/', views.terms_and_conditions_view, name='terms_and_conditions'),
]