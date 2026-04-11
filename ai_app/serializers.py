from rest_framework import serializers
from .models import AIDraft, OutgoingMessage
from messages_app.models import Message


class MessageMiniSerializer(serializers.ModelSerializer):
    citizen_name  = serializers.CharField(source="citizen.name",         read_only=True)
    citizen_phone = serializers.CharField(source="citizen.phone_number", read_only=True)

    class Meta:
        model  = Message
        fields = ["id", "content", "source", "timestamp", "citizen_name", "citizen_phone"]


class AIDraftSerializer(serializers.ModelSerializer):
    message_detail = MessageMiniSerializer(source="message", read_only=True)

    class Meta:
        model  = AIDraft
        fields = [
            "id", "project", "message", "message_detail",
            "generated_text", "edited_text", "status", "created_at",
        ]
        read_only_fields = ["id", "generated_text", "created_at"]


class OutgoingMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OutgoingMessage
        fields = "__all__"
        read_only_fields = ["id", "sent_at"]