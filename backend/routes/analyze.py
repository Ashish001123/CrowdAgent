from fastapi import APIRouter, HTTPException
from playwright.async_api import Error as PlaywrightError

from services.browser_service import analyze_website
from schema.schema import WebsiteScanRequest


router = APIRouter(
    prefix="/analyzer",
    tags=["Website Analyzer"]
)


@router.post("/scan")
async def scan_website(request: WebsiteScanRequest):

    if not request.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Authorization confirmation is required."
        )

    try:

        result = await analyze_website(
            str(request.url),
            request.expected_http_statuses
        )

        return {
            "status": "success",
            "data": result
        }

    except PlaywrightError as error:

        raise HTTPException(
            status_code=502,
            detail=f"Browser analysis failed: {str(error)}"
        )