import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ApplicantQueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if user.is_anonymous:
            await self.close()
            return

        applicant_id = await self.get_applicant_id(user)

        if not applicant_id:
            await self.close()
            return

        self.applicant_id = applicant_id
        self.group_name = f"queue_applicant_{self.applicant_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    @database_sync_to_async
    def get_applicant_id(self, user):
        try:
            return user.applicant_profile.id
        except Exception:
            return None

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def queue_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))