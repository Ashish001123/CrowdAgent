from fastapi import APIRouter, HTTPException
from playwright.async_api import Error as PlaywrightError

from services.browser_service import analyze_website
from services.issue_reporter import generate_report
from schema.schema import WebsiteScanRequest, ScanReport


router = APIRouter(
    prefix="/analyzer",
    tags=["Website Analyzer"]
)


@router.post("/scan", response_model=ScanReport)
async def scan_website(request: WebsiteScanRequest):

    if not request.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Authorization confirmation is required."
        )

    try:

        raw_result = await analyze_website(
            str(request.url),
            request.expected_http_statuses
        )

        report = generate_report(raw_result)

        return report

    except PlaywrightError as error:

        raise HTTPException(
            status_code=502,
            detail=f"Browser analysis failed: {str(error)}"
        )