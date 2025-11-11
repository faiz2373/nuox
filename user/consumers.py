import json
from channels.generic.websocket import AsyncWebsocketConsumer
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from portal.models import *
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.utils import timezone
import pytz

UAE_TIMEZONE = "Asia/Dubai"

@database_sync_to_async
def UserRoomStatus(conditions):
    try:
        ChatboxRoom.objects.get( **conditions )
        return True
    except Exception as e:
        return False
    
@database_sync_to_async
def getReceiverId(room_id,user_id):
    try:
        chat_room = ChatboxRoom.objects.get(id=room_id).name
        chat_room_split = chat_room.split('-') 
        receiver_id = chat_room_split[-1]
        if user_id==int(receiver_id):
            receiver_id = chat_room_split[0]
        return receiver_id
    except Exception as e:
        return False
    
@database_sync_to_async
def SaveUserMessage(conditions):
    try:
        sender_obj = User.objects.get(id=conditions['sender_id'])
        receiver_obj = User.objects.get(id=conditions['receiver_id'])
        room_obj = ChatboxRoom.objects.get(id=conditions['room_id'])
        Chatlist.objects.create(message=conditions['message'],sender=sender_obj,receiver=receiver_obj,room=room_obj)
        return True
    except Exception as e:
        return False
    
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join the room group
        user = self.scope['authuser']
        room_stat = False
        if user.is_authenticated:
            room_id = self.scope["url_route"]["kwargs"]["room_name"]
            self.room_groupname = "trainpad_{0}".format( room_id )
            conditions = {
                    "id": room_id,
                    # "user_id": user.pk,
                }
            query_string = parse_qs( self.scope['query_string'].decode() )
            role = query_string.get("role", ['user'])
            if role[0] == 'user':
                room_stat = await UserRoomStatus( conditions )
                if room_stat:
                    # Join the room group
                    
                    await self.channel_layer.group_add(group=self.room_groupname,channel = self.channel_name)
                    await self.accept()
        if room_stat == False:
            self.room_groupname = None
            await self.close()

    async def disconnect(self, close_code):
        # Leave the room group
        if self.room_groupname is not None:
            conditions = {
                'room_id': self.scope["url_route"]["kwargs"]["room_name"],
                'user_id': self.scope["authuser"],
            }
            try:
                await self.channel_layer.group_discard(
                    self.room_groupname,
                    self.channel_layer
                )
            except Exception as e:
                pass
        else:
            pass

    async def receive(self, text_data):
        # Handle received messages from the client
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        user = self.scope["authuser"]
        room_id = self.scope["url_route"]["kwargs"]["room_name"]

        receiverId = await getReceiverId(room_id,user.pk)
        message_rec = {"room_id": room_id, "message": message, "sender_id": user.pk, "receiver_id":receiverId}
        # saving msg to db
        await SaveUserMessage( message_rec )
        # Send the message to the room group
        await self.channel_layer.group_send(
            self.room_groupname,{
                "type" : "send_message" ,
                "message" : message ,
                "sender_id": user.pk,
                "receiver_id": receiverId,
            })
        
        
    async def send_message(self , event):
        # Send the received message to the client
        query_string = parse_qs( self.scope['query_string'].decode() )
        local_timezone = pytz.timezone( query_string.get("timezone", [ UAE_TIMEZONE ])[0] )
        received_at = str( naturaltime( timezone.now().astimezone( tz= local_timezone ) ) )
        message = event["message"]
        sender_id = event["sender_id"]
        receiver_id = event["receiver_id"]
        await self.send(text_data = json.dumps({"message":message, "received_at": received_at, "sender_id": sender_id, "receiver_id":receiver_id }))
