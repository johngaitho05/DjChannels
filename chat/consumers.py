import asyncio
import json
from django.contrib.auth import get_user_model
from channels.consumer import AsyncConsumer
from channels.db import database_sync_to_async
from .models import Thread, ChatMessage


class ChatConsumer(AsyncConsumer):
    async def websocket_connect(self, event):
        other_user = self.scope['url_route']['kwargs']['username']
        author = self.scope['user']
        thread_obj = await self.get_thread_obj(author, other_user)
        self.thread_obj = thread_obj
        chat_room = f"thread_{thread_obj.id}"
        self.chat_room = chat_room
        await self.channel_layer.group_add(
            chat_room,
            self.channel_name
        )
        await self.send({
            'type': 'websocket.accept'
        })

    async def websocket_receive(self, event):
        data = event.get('text', None)
        if data is not None:
            # getting data from the fronted
            loaded_data = json.loads(data)
            message = loaded_data.get('message')
            sender = self.scope['user']
            # saving the message to the database
            await self.save_message(sender, message)
            response = {
                'sender': sender.username,
                'message': message
            }
            # broadcasts the message to be sent
            await self.channel_layer.group_send(
                self.chat_room,
                {
                    "type": "chat_message",
                    "text": json.dumps(response)
                }
            )

    async def chat_message(self, event):
        # sends the actual message
        await self.send({
            "type": "websocket.send",
            "text": event['text']
        })

    async def websocket_disconnect(self, event):
        print("disconnected", event)

    @database_sync_to_async
    def get_thread_obj(self, user, other_username):
        return Thread.objects.get_or_new(user, other_username)[0]

    @database_sync_to_async
    def save_message(self, sender, msg):
        thread_obj = self.thread_obj
        return ChatMessage.objects.create(user=sender, message=msg, thread=thread_obj)
