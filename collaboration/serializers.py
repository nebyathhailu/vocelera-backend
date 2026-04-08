from rest_framework import serializers
from .models import Discussion, DiscussionParticipant, Comment
from users.serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "discussion", "user", "content", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class DiscussionParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = DiscussionParticipant
        fields = ["id", "discussion", "user", "role"]
        read_only_fields = ["id", "user"]


class DiscussionSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Discussion
        fields = [
            "id", "project", "related_type", "related_id",
            "created_by", "created_at", "comments",
        ]
        read_only_fields = ["id", "created_by", "created_at"]