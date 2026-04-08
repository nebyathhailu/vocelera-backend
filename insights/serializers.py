from rest_framework import serializers
from .models import Insight


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = "__all__"
        read_only_fields = ["id", "created_at"]