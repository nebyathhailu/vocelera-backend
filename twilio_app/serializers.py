from rest_framework import serializers
from messages_app.models import Message, Citizen
from insights.models import Insight


class CitizenMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Citizen
        fields = ["id", "phone_number", "name", "region"]


class WhatsAppMessageSerializer(serializers.ModelSerializer):
    """
    Serializer used for real-time WebSocket broadcast payloads.
    Optimized to include only what the dashboard needs.
    """
    citizen = CitizenMiniSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "project",
            "citizen",
            "content",
            "source",
            "timestamp",
            "external_id",
            "created_at",
        ]


class InsightBroadcastSerializer(serializers.ModelSerializer):
    """Serializer for real-time insight broadcast payloads."""

    class Meta:
        model = Insight
        fields = [
            "id",
            "project",
            "theme",
            "sentiment",
            "priority_score",
            "frequency",
            "policy_suggestion",
            "service_improvement",
            "interpretation",
            "created_at",
        ]