from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from projects.models import AnalysisProject, ProjectParticipant
from collaboration.models import DiscussionParticipant
from .serializers import InsightSerializer
from . import services


class InsightViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InsightSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if not project_id:
            return services.get_project_insights(None)

        user = self.request.user

        # Full project members see all insights
        if ProjectParticipant.objects.filter(project_id=project_id, user=user).exists():
            return services.get_project_insights(project_id)

        # Discussion-only invitees see only insights they were invited to discuss
        invited_insight_ids = DiscussionParticipant.objects.filter(
            user=user,
            discussion__project_id=project_id,
            discussion__related_type="insight",
        ).values_list("discussion__related_id", flat=True)

        if invited_insight_ids:
            from .models import Insight
            return Insight.objects.filter(
                project_id=project_id,
                id__in=invited_insight_ids,
            )

        return services.get_project_insights(None)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        project_id = request.data.get("project_id")
        project = get_object_or_404(AnalysisProject, pk=project_id)
        try:
            insights = services.generate_insights_for_project(project)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "AI generation failed.", "detail": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(InsightSerializer(insights, many=True).data, status=status.HTTP_201_CREATED)