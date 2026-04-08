"""
Document analysis service layer.

Flow:
  1. Detect and validate file type
  2. Parse file into text (parsers.py)
  3. Build Gemini prompt (prompt_builder.py)
  4. Call GeminiClient
  5. Persist results to DocumentAnalysis model
"""

import logging
from django.utils import timezone
from .models import DocumentAnalysis
from .parsers import parse_document
from ai_services.gemini_client import GeminiClient, GeminiClientError
from ai_services.prompt_builder import build_document_analysis_prompt, SYSTEM_BASE

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"csv", "pdf", "xlsx", "xls"}
EXTENSION_TO_TYPE  = {
    "csv":  DocumentAnalysis.DocumentType.CSV,
    "pdf":  DocumentAnalysis.DocumentType.PDF,
    "xlsx": DocumentAnalysis.DocumentType.EXCEL,
    "xls":  DocumentAnalysis.DocumentType.EXCEL,
}


def get_file_extension(file_name: str) -> str:
    """Extract and return the lowercase file extension."""
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def validate_file(file_name: str) -> str:
    """
    Validate file extension and return the detected type string.

    Raises:
        ValueError: If the file type is not supported.
    """
    ext = get_file_extension(file_name)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' is not supported. "
            f"Please upload a CSV, PDF, or Excel file."
        )
    return ext


def analyse_document(
    uploaded_file,
    uploaded_by,
    project=None,
) -> DocumentAnalysis:
    """
    Full pipeline: validate → parse → AI analyse → persist.

    Args:
        uploaded_file: Django UploadedFile object from request.FILES
        uploaded_by:   User instance performing the upload
        project:       Optional AnalysisProject to link the result to

    Returns:
        DocumentAnalysis instance with populated results.
    """
    file_name = uploaded_file.name
    ext       = validate_file(file_name)
    doc_type  = EXTENSION_TO_TYPE[ext]

    # ── Create record in PENDING state ─────────────────────────────────────
    analysis = DocumentAnalysis.objects.create(
        project       = project,
        uploaded_by   = uploaded_by,
        file          = uploaded_file,
        file_name     = file_name,
        document_type = doc_type,
        status        = DocumentAnalysis.Status.PENDING,
    )

    try:
        # ── Step 1: Parse file ──────────────────────────────────────────────
        analysis.status = DocumentAnalysis.Status.PROCESSING
        analysis.save(update_fields=["status"])

        uploaded_file.seek(0)   # reset pointer after Django's initial read
        parsed = parse_document(uploaded_file, ext)

        analysis.row_count  = parsed.get("row_count")
        analysis.page_count = parsed.get("page_count")
        analysis.save(update_fields=["row_count", "page_count"])

        # ── Step 2: Build prompt ────────────────────────────────────────────
        prompt = build_document_analysis_prompt(
            document_text = parsed["text"],
            file_name     = file_name,
            document_type = ext,
            project_name  = project.name if project else "",
        )

        # ── Step 3: Call Gemini ─────────────────────────────────────────────
        result = GeminiClient.generate_structured(
            prompt, system_instruction=SYSTEM_BASE
        )

        # ── Step 4: Persist AI results ──────────────────────────────────────
        analysis.summary         = result.get("summary", "")
        analysis.key_themes      = result.get("key_themes", [])
        analysis.statistics      = result.get("statistics", {})
        analysis.insights        = result.get("insights", [])
        analysis.recommendations = result.get("recommendations", "")
        analysis.raw_ai_response = str(result)
        analysis.status          = DocumentAnalysis.Status.DONE
        analysis.completed_at    = timezone.now()
        analysis.save()

        logger.info(
            "Document analysis complete [id=%s, file=%s, themes=%d]",
            analysis.pk, file_name, len(analysis.key_themes)
        )

    except GeminiClientError as exc:
        logger.error("Gemini failed for document analysis #%s: %s", analysis.pk, exc)
        analysis.status        = DocumentAnalysis.Status.FAILED
        analysis.error_message = f"AI processing failed: {exc}"
        analysis.save(update_fields=["status", "error_message"])
        raise

    except Exception as exc:
        logger.exception("Document analysis failed #%s: %s", analysis.pk, exc)
        analysis.status        = DocumentAnalysis.Status.FAILED
        analysis.error_message = str(exc)
        analysis.save(update_fields=["status", "error_message"])
        raise

    return analysis


def get_analyses_for_user(user):
    return DocumentAnalysis.objects.filter(uploaded_by=user).select_related("project")


def get_analyses_for_project(project_id: int):
    return DocumentAnalysis.objects.filter(project_id=project_id)