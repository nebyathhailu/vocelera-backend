import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from projects.models import AnalysisProject
from .models import DocumentAnalysis
from .serializers import DocumentUploadSerializer, DocumentAnalysisSerializer
from . import services

logger = logging.getLogger(__name__)


class DocumentAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoints:
      POST   /documents/analyze/           — upload & analyse a document
      GET    /documents/                   — list my analyses
      GET    /documents/<id>/              — retrieve single analysis
      GET    /documents/?project_id=<id>  — list analyses for a project
    """

    serializer_class = DocumentAnalysisSerializer
    parser_classes   = [MultiPartParser, FormParser]

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return services.get_analyses_for_project(project_id)
        return services.get_analyses_for_user(self.request.user)

    @action(
        detail=False,
        methods=["post"],
        url_path="analyze",
        parser_classes=[MultiPartParser, FormParser],
    )
    def analyze(self, request):
        """
        Upload a CSV, PDF, or Excel file and receive a full AI analysis.

        Request:  multipart/form-data
          - file:       the document file
          - project_id: (optional) link to an existing project

        Response: DocumentAnalysis object with AI-generated fields populated.
        """
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        project_id    = serializer.validated_data.get("project_id")

        project = None
        if project_id:
            project = get_object_or_404(AnalysisProject, pk=project_id)

        try:
            analysis = services.analyse_document(
                uploaded_file = uploaded_file,
                uploaded_by   = request.user,
                project       = project,
            )
        except ValueError as exc:
            # File type or validation errors
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Document analysis endpoint error: %s", exc)
            return Response(
                {
                    "error": "Document analysis failed.",
                    "detail": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            DocumentAnalysisSerializer(analysis).data,
            status=status.HTTP_201_CREATED,
        )