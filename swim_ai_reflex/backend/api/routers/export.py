"""
Export Router

Provides endpoints for exporting optimization results in various formats.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from swim_ai_reflex.backend.api.models import (
    ErrorResponse,
    ExportFormat,
    ExportRequest,
    ExportResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/export",
    response_model=ExportResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def export_results(request: ExportRequest):
    """
    Export optimization results to the specified format.

    Args:
        request: Export request with format and results data

    Returns:
        Export response with content or download URL
    """
    try:
        from swim_ai_reflex.backend.services.export_service import export_service

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if request.format == ExportFormat.CSV:
            # Extract list from dict - check all keys, prioritize 'details' for scores
            results_list = []
            if isinstance(request.optimization_results, dict):
                results_list = (
                    request.optimization_results.get("details")
                    or request.optimization_results.get("best_lineup")
                    or request.optimization_results.get("results")
                    or []
                )
            else:
                results_list = request.optimization_results

            content = export_service.to_csv(
                optimization_results=results_list,
                seton_score=request.seton_score,
                opponent_score=request.opponent_score,
                metadata=request.metadata or {},
            )
            filename = f"aquaforge_lineup_{timestamp}.csv"

            return Response(
                content=content,
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        elif request.format == ExportFormat.HTML:
            # Extract list from dict
            results_list = []
            if isinstance(request.optimization_results, dict):
                results_list = (
                    request.optimization_results.get("details")
                    or request.optimization_results.get("best_lineup")
                    or request.optimization_results.get("results")
                    or []
                )
            else:
                results_list = request.optimization_results

            content = export_service.to_html_table(
                optimization_results=results_list,
                seton_score=request.seton_score,
                opponent_score=request.opponent_score,
            )
            filename = f"aquaforge_lineup_{timestamp}.html"

            return Response(
                content=content,
                media_type="text/html",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        elif request.format == ExportFormat.PDF:
            # Extract list from dict
            results_list = []
            if isinstance(request.optimization_results, dict):
                results_list = (
                    request.optimization_results.get("details")
                    or request.optimization_results.get("best_lineup")
                    or request.optimization_results.get("results")
                    or []
                )
            else:
                results_list = request.optimization_results

            # Generate HTML first, then attempt PDF conversion
            html_content = export_service.to_html_table(
                optimization_results=results_list,
                seton_score=request.seton_score,
                opponent_score=request.opponent_score,
            )

            # Try PDF conversion, fall back to HTML download
            pdf_bytes = export_service.to_pdf(html_content)
            if pdf_bytes:
                filename = f"aquaforge_lineup_{timestamp}.pdf"
                return Response(
                    content=pdf_bytes,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )
            else:
                # Fallback to HTML when PDF library not available
                filename = f"aquaforge_lineup_{timestamp}.html"
                return Response(
                    content=html_content,
                    media_type="text/html",
                    headers={"Content-Disposition": f"attachment; filename={filename}"},
                )

        elif request.format == ExportFormat.XLSX:
            # Extract list from dict
            results_list = []
            if isinstance(request.optimization_results, dict):
                results_list = (
                    request.optimization_results.get("details")
                    or request.optimization_results.get("best_lineup")
                    or request.optimization_results.get("results")
                    or []
                )
            else:
                results_list = request.optimization_results

            content = export_service.to_xlsx(
                optimization_results=results_list,
                seton_score=request.seton_score,
                opponent_score=request.opponent_score,
            )
            filename = f"aquaforge_lineup_{timestamp}.xlsx"

            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        elif request.format == ExportFormat.JSON:
            import json

            content = json.dumps(
                {
                    "optimization_results": request.optimization_results,
                    "seton_score": request.seton_score,
                    "opponent_score": request.opponent_score,
                    "metadata": request.metadata,
                    "exported_at": datetime.now(UTC).isoformat(),
                },
                indent=2,
            )
            filename = f"aquaforge_lineup_{timestamp}.json"

            return ExportResponse(
                success=True,
                format=request.format,
                filename=filename,
                content=content,
                download_url=None,
            )

        else:
            raise HTTPException(
                status_code=400, detail=f"Unsupported export format: {request.format}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/download/{filename}")
async def download_export(filename: str):
    """
    Download a previously generated export file.

    Note: This requires server-side file storage to be implemented.
    """
    # Placeholder - would require file storage implementation
    raise HTTPException(
        status_code=501,
        detail="Server-side file storage not implemented. Use direct export.",
    )


@router.get("/export/formats")
async def list_export_formats():
    """
    List available export formats and their descriptions.
    """
    return {
        "formats": [
            {
                "id": "csv",
                "name": "CSV",
                "description": "Comma-separated values, compatible with Excel",
                "mime_type": "text/csv",
            },
            {
                "id": "html",
                "name": "HTML",
                "description": "Formatted HTML table, can be printed to PDF",
                "mime_type": "text/html",
            },
            {
                "id": "pdf",
                "name": "PDF",
                "description": "PDF document (currently returns HTML for printing)",
                "mime_type": "application/pdf",
            },
            {
                "id": "json",
                "name": "JSON",
                "description": "Raw JSON data for programmatic access",
                "mime_type": "application/json",
            },
        ]
    }
