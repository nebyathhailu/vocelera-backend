from rest_framework import serializers
from .models import Citizen, Message


class CitizenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Citizen
        fields = ["id", "phone_number", "name", "region"]


class MessageSerializer(serializers.ModelSerializer):
    citizen = CitizenSerializer(read_only=True)
    citizen_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Message
        fields = [
            "id", "project", "citizen", "citizen_id",
            "content", "source", "timestamp", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class BulkMessageSerializer(serializers.Serializer):
    """Used for importing large batches of messages."""
    messages = MessageSerializer(many=True)