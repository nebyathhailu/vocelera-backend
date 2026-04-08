from typing import List
from .models import Insight
from projects.models import AnalysisProject
from messages_app.services import get_message_contents_for_project
from ai_services.gemini_client import GeminiClient, GeminiClientError
from ai_services.prompt_builder import build_insight_analysis_prompt, SYSTEM_BASE
import logging

logger = logging.getLogger(__name__)


def generate_insights_for_project(project: AnalysisProject) -> List[Insight]:
    """
    Core AI-powered service: generate and persist insights for a project.

    Flow:
        1. Fetch message contents from DB
        2. Build prompt
        3. Call Gemini
        4. Parse and persist insights
    """
    messages = get_message_contents_for_project(project.pk)

    if not messages:
        raise ValueError("No messages found for this project.")

    prompt = build_insight_analysis_prompt(messages, project.name)

    try:
        result = GeminiClient.generate_structured(prompt, system_instruction=SYSTEM_BASE)
    except GeminiClientError as e:
        logger.error("AI insight generation failed for project %s: %s", project.pk, e)
        raise

    insights_data = result.get("insights", [])
    created_insights = []

    for item in insights_data:
        insight = Insight.objects.create(
            project=project,
            theme=item.get("theme", "Unknown"),
            sentiment=item.get("sentiment", "neutral"),
            priority_score=float(item.get("priority_score", 0.0)),
            frequency=int(item.get("frequency", 0)),
            policy_suggestion=item.get("policy_suggestion", ""),
            service_improvement=item.get("service_improvement", ""),
            interpretation=item.get("interpretation", ""),
        )
        created_insights.append(insight)

    logger.info(
        "Generated %d insights for project %s", len(created_insights), project.pk
    )
    return created_insights


def get_project_insights(project_id: int):
    return Insight.objects.filter(project_id=project_id)