from typing import List


SYSTEM_BASE = (
    "You are an expert public policy analyst AI assistant embedded in a "
    "government civic engagement platform. Your role is to analyze citizen "
    "feedback, extract actionable insights, and draft professional responses. "
    "Always be factual, neutral, structured, and clear."
)


def build_insight_analysis_prompt(messages: List[str], project_name: str) -> str:
    """
    Build a prompt for generating insights from citizen messages.

    Args:
        messages: List of raw citizen message content strings.
        project_name: Name of the analysis project.

    Returns:
        str: A structured prompt ready to send to Gemini.
    """
    message_block = "\n".join(
        [f"- {msg}" for msg in messages[:500]]  # cap at 500 for token safety
    )
    return f"""
You are analyzing citizen feedback for the government consultation: "{project_name}".

Below are citizen messages collected from this consultation:

{message_block}

Your task:
1. Identify the top recurring themes (max 10).
2. Determine overall sentiment for each theme (positive / negative / neutral / mixed).
3. Assign a priority score from 0.0 to 1.0 (1.0 = most urgent).
4. Estimate frequency (how many messages relate to each theme).
5. Suggest a relevant policy improvement for each theme.
6. Suggest a service improvement for each theme.
7. Provide a short interpretation of the overall feedback landscape.

Respond ONLY in the following JSON format:
{{
  "insights": [
    {{
      "theme": "string",
      "sentiment": "positive | negative | neutral | mixed",
      "priority_score": float,
      "frequency": integer,
      "policy_suggestion": "string",
      "service_improvement": "string",
      "interpretation": "string"
    }}
  ],
  "overall_summary": "string"
}}
"""


def build_draft_response_prompt(
    citizen_message: str,
    project_name: str,
    citizen_name: str = "",
    insights_context: list = None,
) -> str:
    """
    Build a prompt for drafting a meaningful, personalised response
    to a citizen's WhatsApp feedback message.

    The response must:
    - Directly acknowledge the specific concern raised
    - Show the government has understood the feedback
    - Give a concrete next step or commitment (not vague promises)
    - Be warm, human, and professional
    - Be WhatsApp-appropriate (short paragraphs, no bullet points, no formal headers)
    - Be 3-5 sentences maximum
    """
    greeting = f"Dear {citizen_name}" if citizen_name else "Dear valued citizen"

    insights_block = ""
    if insights_context:
        top = insights_context[:3]
        lines = "\n".join(
            f"- {i.get('theme', '')} (priority: {i.get('priority_score', 0):.0%}, sentiment: {i.get('sentiment', '')})"
            for i in top
        )
        insights_block = f"""
For additional context, here are the top themes emerging from the overall
consultation so far:
{lines}

Use this context to make the response feel informed and connected to a
broader effort — but keep the focus on the citizen's specific message.
"""

    return f"""
You are a professional government communications officer responding to a
citizen who submitted feedback via WhatsApp as part of the
"{project_name}" public consultation.

Citizen's message:
\"\"\"{citizen_message}\"\"\"
{insights_block}
Write a WhatsApp reply that:
1. Opens with "{greeting}," then immediately acknowledges the SPECIFIC issue
   they raised — name it directly, do not use generic language like
   "your concern" or "your feedback".
2. Confirms that their input has been recorded and will inform
   decision-making — be specific about what kind of decision
   (e.g. infrastructure planning, service delivery review, policy update).
3. Gives ONE concrete next step the government is taking or will take
   related to their specific concern. If you cannot be specific, state
   a realistic timeline for a response or update.
4. Closes with a genuine, warm sign-off that invites further engagement
   if they have more to share.

Tone: professional but human. Like a real person wrote it, not a bot.
Length: 3-5 sentences. No bullet points. No headers. No markdown.
Return ONLY the message text. Nothing else.
"""


def build_report_summary_prompt(
    project_name: str,
    insights_summary: List[dict],
    total_messages: int,
) -> str:
    """
    Build a prompt to generate a full report summary.

    Args:
        project_name: Name of the project.
        insights_summary: List of insight dicts.
        total_messages: Total number of citizen messages analyzed.

    Returns:
        str: Prompt for report generation.
    """
    insights_text = "\n".join([
        f"- Theme: {i.get('theme')} | Sentiment: {i.get('sentiment')} | "
        f"Priority: {i.get('priority_score')} | Policy: {i.get('policy_suggestion')}"
        for i in insights_summary
    ])

    return f"""
Generate a formal executive summary report for the government consultation project: "{project_name}".

Total messages analyzed: {total_messages}

Top insights identified:
{insights_text}

Your report should include:
1. Executive Summary (2-3 paragraphs)
2. Key Findings
3. Recommendations (prioritized)
4. Conclusion

Use formal government report language. Be clear, structured, and actionable.
"""

def build_document_analysis_prompt(
    document_text: str,
    file_name: str,
    document_type: str,
    project_name: str = "",
) -> str:
    """
    Build a prompt for AI analysis of an uploaded document.

    Args:
        document_text:  Extracted text content from the parser.
        file_name:      Original file name (for context).
        document_type:  csv, pdf, or xlsx.
        project_name:   Optional project context.

    Returns:
        str: Structured prompt ready to send to Gemini.
    """
    project_context = f'This document is part of the "{project_name}" consultation.' if project_name else ""

    return f"""
You are an expert government policy analyst. {project_context}
An officer has uploaded a {document_type.upper()} document named "{file_name}" for analysis.

{document_text}

Your task is to thoroughly analyse this document and respond ONLY in the following JSON format:

{{
  "summary": "A 2-3 paragraph executive summary of the document's content and significance",
  "key_themes": [
    {{
      "theme": "string",
      "description": "string",
      "frequency_or_prevalence": "string",
      "sentiment": "positive | negative | neutral | mixed"
    }}
  ],
  "statistics": {{
    "total_records": "string or number if applicable",
    "date_range": "string if applicable",
    "notable_figures": ["string"]
  }},
  "insights": [
    {{
      "insight": "string",
      "supporting_evidence": "string",
      "priority": "high | medium | low"
    }}
  ],
  "recommendations": "A prioritised list of actionable recommendations for government officers based on the document",
  "data_quality_notes": "Any issues with the data (missing values, inconsistencies, potential biases)"
}}

Respond with ONLY the JSON object. No preamble, no markdown fences.
"""