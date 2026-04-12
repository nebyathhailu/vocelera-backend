from rest_framework import serializers
from .models import Discussion, DiscussionParticipant, Comment
from users.serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model  = Comment
        fields = ["id", "discussion", "user", "content", "created_at"]
        read_only_fields = ["id", "user", "created_at"]


class DiscussionParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model  = DiscussionParticipant
        fields = ["id", "user", "role"]
        read_only_fields = ["id", "user"]


class DiscussionSerializer(serializers.ModelSerializer):
    created_by    = UserSerializer(read_only=True)
    comments      = CommentSerializer(many=True, read_only=True)
    participants  = DiscussionParticipantSerializer(many=True, read_only=True)
    comment_count = serializers.SerializerMethodField()

    # These let the frontend show project context without a separate API call
    # Safe for invited users who are not project members
    project_name = serializers.SerializerMethodField()
    project_id   = serializers.SerializerMethodField()

    class Meta:
        model  = Discussion
        fields = [
            "id", "project", "project_id", "project_name",
            "related_type", "related_id",
            "created_by", "created_at",
            "comments", "participants", "comment_count",
        ]
        read_only_fields = ["id", "created_by", "created_at"]

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_project_name(self, obj):
        # Safe access — project may not be prefetched in all contexts
        try:
            return obj.project.name if obj.project else None
        except Exception:
            return None

    def get_project_id(self, obj):
        try:
            return obj.project.id if obj.project else None
        except Exception:
            return None


class CreateDiscussionSerializer(serializers.Serializer):
    project        = serializers.IntegerField()
    related_type   = serializers.ChoiceField(choices=["message", "insight", "report"])
    related_id     = serializers.IntegerField()
    invited_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list,
        max_length=50,
    )


class InviteParticipantsSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        min_length=1,
        max_length=50,
    )