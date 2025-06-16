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

        chat_message = await self.save_message(message, sender_profile)
        
        # --- Create notification for other participants ---
        await self.create_chat_notification(sender_profile, chat_message.room)

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

    # --- ADDED: Method to create notifications for new messages ---
    @database_sync_to_async
    def create_chat_notification(self, sender_profile, room):
        other_participants = room.participants.exclude(user=self.user)
        
        for participant_profile in other_participants:
            if participant_profile.user != self.user:
                Notification.objects.create(
                    recipient=participant_profile.user,
                    sender_profile=sender_profile,
                    notification_type='new_message',
                    text=f"You have a new message from {sender_profile.full_name}.",
                    chat_room=room
                )