from rest_framework import serializers
from .models import AIDraft, OutgoingMessage


class AIDraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIDraft
        fields = "__all__"
        read_only_fields = ["id", "generated_text", "created_at"]


class OutgoingMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutgoingMessage
        fields = "__all__"
        read_only_fields = ["id", "sent_at"]