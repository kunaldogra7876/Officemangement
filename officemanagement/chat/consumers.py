import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message
from accounts.models import CustomUser

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        try:
            self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        except KeyError:
            await self.close()
            return

        users = sorted([int(self.user.id), int(self.other_user_id)])
        self.room_name = f"chat_{users[0]}_{users[1]}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)

        self.user_notification_group = f"notify_{self.user.id}"
        await self.channel_layer.group_add(self.user_notification_group, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)
        if hasattr(self, 'user_notification_group'):
            await self.channel_layer.group_discard(self.user_notification_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '').strip()
        if not message: return
        
        receiver = await self.get_user(self.other_user_id)
        if receiver:
            await self.save_message(self.user, receiver, message)
            await self.channel_layer.group_send(
                self.room_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'username': self.user.username
                }
            )
            await self.channel_layer.group_send(
                f"notify_{self.other_user_id}",
                {
                    'type': 'user_notification',
                    'sender_name': self.user.username,
                    'sender_id': self.user.id,
                    'message': message[:30] + "..."
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'username': event['username']
        }))

    async def user_notification(self, event):
        if event.get('sender_id') == self.user.id:
            return

        await self.send(text_data=json.dumps({
            'type': 'notification',
            'sender_name': event['sender_name'],
            'message': str(event['message']),
            'sender_id': event.get('sender_id')
        }))

    @database_sync_to_async
    def get_user(self, user_id):
        return CustomUser.objects.filter(id=user_id).first()

    @database_sync_to_async
    def save_message(self, sender, receiver, message):
        return Message.objects.create(sender=sender, receiver=receiver, content=message)