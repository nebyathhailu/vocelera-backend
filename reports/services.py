from projects.models import AnalysisProject
from insights.models import Insight
from messages_app.models import Message
from ai_services.gemini_client import GeminiClient
from ai_services.prompt_builder import build_report_summary_prompt, SYSTEM_BASE
from .models import Report


def generate_report(project: AnalysisProject) -> Report:
    """Generate an AI-powered executive report for a project."""

    total_messages = Message.objects.filter(project=project).count()
    insights = Insight.objects.filter(project=project).values(
        "theme", "sentiment", "priority_score", "policy_suggestion"
    )

    prompt = build_report_summary_prompt(
        project_name=project.name,
        insights_summary=list(insights),
        total_messages=total_messages,
    )

    summary = GeminiClient.generate(prompt, system_instruction=SYSTEM_BASE)

    return Report.objects.create(project=project, summary=summary)