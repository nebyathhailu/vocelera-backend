from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from projects.models import AnalysisProject
from .serializers import ReportSerializer
from .models import Report
from . import services


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return Report.objects.filter(project_id=project_id)
        return Report.objects.none()

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        project = get_object_or_404(AnalysisProject, pk=request.data.get("project_id"))
        report = services.generate_report(project)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)