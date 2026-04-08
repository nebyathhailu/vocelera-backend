from rest_framework import serializers
from .models import DocumentAnalysis


class DocumentUploadSerializer(serializers.Serializer):
    """Handles the incoming multipart file upload."""
    file       = serializers.FileField()
    project_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_file(self, value):
        allowed = {"csv", "pdf", "xlsx", "xls"}
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        if ext not in allowed:
            raise serializers.ValidationError(
                f"Unsupported file type '.{ext}'. Upload CSV, PDF, or Excel."
            )
        max_size = 50 * 1024 * 1024   # 50 MB
        if value.size > max_size:
            raise serializers.ValidationError("File size must not exceed 50 MB.")
        return value


class DocumentAnalysisSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.name", read_only=True
    )
    project_name = serializers.CharField(
        source="project.name", read_only=True, default=None
    )

    class Meta:
        model  = DocumentAnalysis
        fields = [
            "id",
            "project", "project_name",
            "uploaded_by", "uploaded_by_name",
            "file_name", "document_type",
            "status",
            "summary", "key_themes", "statistics",
            "insights", "recommendations",
            "row_count", "page_count",
            "error_message",
            "created_at", "completed_at",
        ]
        read_only_fields = fields   # all fields are read-only on output