from rest_framework import serializers
from .models import AnalysisProject, ProjectParticipant
from users.serializers import UserSerializer


class AnalysisProjectSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = AnalysisProject
        fields = ["id", "name", "description", "data_source_type", "created_by", "created_at"]
        read_only_fields = ["id", "created_by", "created_at"]


class ProjectParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ProjectParticipant
        fields = ["id", "project", "user", "user_id", "role", "added_at"]
        read_only_fields = ["id", "added_at", "project"]