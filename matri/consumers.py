# matri/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatRoom, ChatMessage, UserProfile, Notification, User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if the user is a participant of the room
        is_participant = await self.is_user_participant()
        if not is_participant:
            await self.close()
            return
            
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_profile = await self.get_user_profile(self.user)

        # Save message to database
        chat_message = await self.save_message(message, sender_profile)
        
        # Create and send notification to the other user
        await self.create_notification_for_receiver(sender_profile, message)

        # Send message to room group
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

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender_name = event['sender_name']
        sender_avatar_url = event['sender_avatar_url']
        timestamp = event['timestamp']

        # Send message to WebSocket
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

    @database_sync_to_async
    def create_notification_for_receiver(self, sender_profile, message_content):
        room = ChatRoom.objects.get(id=self.room_id)
        # Find the other participant
        receiver_profile = room.participants.exclude(id=sender_profile.id).first()
        if receiver_profile:
            Notification.objects.create(
                recipient=receiver_profile.user,
                sender=self.user,
                message=f"sent you a message: '{message_content[:30]}...'",
                # No post associated with a chat message
            )