"""
Django Channels WebSocket consumers.

Two consumers power the real-time dashboard:
  1. MessageConsumer  — streams new WhatsApp messages as they arrive
  2. InsightConsumer  — streams updated AI insights after batch processing

Frontend connects to:
  ws://<host>/ws/projects/<project_id>/messages/
  ws://<host>/ws/projects/<project_id>/insights/

Auth: JWT token passed as query param ?token=<access_token>
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from projects.models import ProjectParticipant

User = get_user_model()
logger = logging.getLogger(__name__)


class BaseProjectConsumer(AsyncWebsocketConsumer):
    """
    Base consumer that handles:
      - JWT authentication via query string
      - Project participation check
      - Group join/leave lifecycle
    """

    group_suffix = "base"  # overridden by subclasses

    async def connect(self):
        self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
        self.group_name = f"project_{self.project_id}_{self.group_suffix}"

        # Authenticate
        user = await self._authenticate()
        if user is None:
            logger.warning("WebSocket rejected: unauthenticated connection")
            await self.close(code=4001)
            return

        # Authorization: must be a project participant
        is_participant = await self._is_participant(user, self.project_id)
        if not is_participant:
            logger.warning(
                "WebSocket rejected: user %s is not a participant of project %s",
                user.pk,
                self.project_id,
            )
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(
            "WebSocket connected: user %s joined group %s", user.pk, self.group_name
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Dashboard consumers are read-only
        pass

    async def _authenticate(self):
        """Extract and validate JWT from query string."""
        try:
            query_string = self.scope.get("query_string", b"").decode()
            params = dict(qp.split("=") for qp in query_string.split("&") if "=" in qp)
            token_str = params.get("token")
            if not token_str:
                return None
            token = AccessToken(token_str)
            user_id = token["user_id"]
            return await database_sync_to_async(User.objects.get)(pk=user_id)
        except (TokenError, User.DoesNotExist, Exception) as e:
            logger.debug("WebSocket auth failed: %s", e)
            return None

    @database_sync_to_async
    def _is_participant(self, user, project_id) -> bool:
        return ProjectParticipant.objects.filter(
            project_id=project_id, user=user
        ).exists()


class MessageConsumer(BaseProjectConsumer):
    """
    Streams newly ingested WhatsApp messages to the dashboard in real time.

    Payload sent to frontend:
    {
      "type": "new_message",
      "message": { ...MessageSerializer fields... }
    }
    """

    group_suffix = "messages"

    async def new_message(self, event):
        """Called by Celery broadcast_new_message_task via channel layer."""
        await self.send(text_data=json.dumps({
            "type": "new_message",
            "message": event["message"],
        }))


class InsightConsumer(BaseProjectConsumer):
    """
    Streams updated AI-generated insights to the dashboard.

    Payload sent to frontend:
    {
      "type": "new_insights",
      "insights": [ ...InsightSerializer fields... ]
    }
    """

    group_suffix = "insights"

    async def new_insights(self, event):
        """Called by Celery trigger_insight_generation_task via channel layer."""
        await self.send(text_data=json.dumps({
            "type": "new_insights",
            "insights": event["insights"],
        }))