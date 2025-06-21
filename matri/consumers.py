# matri/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage, UserProfile, User, Notification


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        is_participant = await self.is_user_participant()
        if not is_participant:
            await self.close()
            return
            
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_profile = await self.get_user_profile(self.user)

        # First, save the message to the database
        chat_message = await self.save_message(message, sender_profile)
        
        # Then, conditionally create a notification based on the new logic
        await self.create_chat_notification_if_needed(sender_profile, chat_message.room)

        # Finally, broadcast the message to the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_profile.id,
                'sender_name': sender_profile.full_name,
                'sender_avatar_url': sender_profile.profile_picture.url if sender_profile.profile_picture else None,
                'timestamp': chat_message.timestamp.strftime('%I:%M %p, %b %d')
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender_name = event['sender_name']
        sender_avatar_url = event['sender_avatar_url']
        timestamp = event['timestamp']

        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'sender_avatar_url': sender_avatar_url,
            'timestamp': timestamp
        }))
        
    @database_sync_to_async
    def get_user_profile(self, user):
        return UserProfile.objects.get(user=user)

    @database_sync_to_async
    def is_user_participant(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            user_profile = UserProfile.objects.get(user=self.user)
            return user_profile in room.participants.all()
        except (ChatRoom.DoesNotExist, UserProfile.DoesNotExist):
            return False

    @database_sync_to_async
    def save_message(self, message_content, sender_profile):
        room = ChatRoom.objects.get(id=self.room_id)
        return ChatMessage.objects.create(
            room=room, 
            sender=sender_profile, 
            content=message_content
        )

    # --- MODIFIED: Renamed and updated to only create a notification when needed ---
    @database_sync_to_async
    def create_chat_notification_if_needed(self, sender_profile, room):
        """
        Creates a 'new_message' notification but only if the recipient doesn't
        already have unread messages in this room.
        """
        # Get the recipient(s) of the message
        other_participants = room.participants.exclude(user=self.user)
        
        for recipient_profile in other_participants:
            # Count unread messages for this recipient in this room.
            # This includes the message we just saved.
            unread_count = ChatMessage.objects.filter(
                room=room,
                is_read=False
            ).exclude(sender=recipient_profile).count()

            # If the count is exactly 1, it means this is the first unread message.
            # This is the moment to create a notification.
            if unread_count == 1:
                Notification.objects.create(
                    recipient=recipient_profile.user,
                    sender_profile=sender_profile,
                    notification_type='new_message',
                    text=f"You have a new message from {sender_profile.full_name}.",
                    chat_room=room
                )
                print(f"Created notification for {recipient_profile.user.username} in room {room.id}")
            else:
                # If unread_count > 1, a notification already exists. Do nothing.
                print(f"Skipped notification for {recipient_profile.user.username}. Unread count: {unread_count}")