from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from projects.models import AnalysisProject, ProjectParticipant
from collaboration.models import DiscussionParticipant
from .serializers import ReportSerializer
from .models import Report
from . import services


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if not project_id:
            return Report.objects.none()

        user = self.request.user

        # Full project members see all reports
        if ProjectParticipant.objects.filter(project_id=project_id, user=user).exists():
            return Report.objects.filter(project_id=project_id)

        # Discussion-only invitees see only the specific reports they were invited to discuss
        invited_report_ids = DiscussionParticipant.objects.filter(
            user=user,
            discussion__project_id=project_id,
            discussion__related_type="report",
        ).values_list("discussion__related_id", flat=True)

        if invited_report_ids:
            return Report.objects.filter(
                project_id=project_id,
                id__in=invited_report_ids,
            )

        return Report.objects.none()

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        project = get_object_or_404(AnalysisProject, pk=request.data.get("project_id"))
        report = services.generate_report(project)
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)