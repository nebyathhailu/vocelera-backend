from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from projects.models import AnalysisProject
from .serializers import InsightSerializer
from . import services
from twilio_app.tasks import trigger_insight_generation_task


class InsightViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InsightSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get("project_id")
        if project_id:
            return services.get_project_insights(project_id)
        return services.get_project_insights(None)

    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        """Trigger AI insight generation for a given project."""
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

        return Response(
            InsightSerializer(insights, many=True).data,
            status=status.HTTP_201_CREATED,
        )

