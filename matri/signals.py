# matri/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from webpush import send_group_notification
from .models import Notification, UserProfile, ChatRoom

@receiver(post_save, sender=Notification)
def send_push_on_new_notification(sender, instance, created, **kwargs):
    """
    This signal triggers a push notification whenever a new Notification object is created.
    """
    if created:
        try:
            recipient = instance.recipient
            
            # --- Construct Payload ---
            sender_profile_pic_url = None
            sender_display_name = instance.sender.username
            sender_profile_id = None

            if hasattr(instance.sender, 'userprofile') and instance.sender.userprofile:
                user_profile = instance.sender.userprofile
                if user_profile.profile_picture:
                    # ** THE FIX IS HERE **
                    # We can only get a relative URL here, which is fine for the service worker.
                    sender_profile_pic_url = user_profile.profile_picture.url
                if user_profile.full_name:
                    sender_display_name = user_profile.full_name
                sender_profile_id = user_profile.id

            click_action_url = "/" # Default URL

            # Reconstruct the URL logic
            if "sent you a message" in instance.message and sender_profile_id:
                current_user_profile = UserProfile.objects.get(user=recipient)
                sender_profile = UserProfile.objects.get(id=sender_profile_id)
                room = ChatRoom.objects.filter(participants=current_user_profile).filter(participants=sender_profile).first()
                if room:
                    click_action_url = f"/messages/room/{room.id}/"
            elif "interest request" in instance.message and sender_profile_id:
                click_action_url = f"/profile/view/{sender_profile_id}/"
            elif instance.post:
                click_action_url = f"/profile/view/{sender_profile_id}/" 
            elif sender_profile_id:
                click_action_url = f"/profile/view/{sender_profile_id}/"

            # Define the payload for the push notification
            payload = {
                "head": f"{sender_display_name}",
                "body": instance.message,
                "icon": sender_profile_pic_url or "/static/icons/icon-192x192.png",
                "url": click_action_url
            }

            # --- Send Notification to the User's Group ---
            group_name = f"user_{recipient.id}"
            send_group_notification(group_name=group_name, payload=payload, ttl=1000)
            
            print(f"Push notification sent or queued for group: {group_name}")

        except Exception as e:
            print(f"Error sending push notification: {e}")
            import traceback
            traceback.print_exc()