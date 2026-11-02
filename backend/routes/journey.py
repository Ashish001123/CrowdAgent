from fastapi import APIRouter, HTTPException
from playwright.async_api import Error as PlaywrightError

from schema.schema import JourneyRunRequest, LoginJourneyRequest, JourneyReport
from services.journey_service import execute_journey, create_login_scenario
from services.url_validator import validate_url, URLValidationError


router = APIRouter(
    prefix="/journey",
    tags=["Journey Engine"]
)


@router.post("/run", response_model=JourneyReport)
async def run_journey(request: JourneyRunRequest):
    """
    Execute a defined user testing scenario step-by-step.
    """

    if not request.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Authorization confirmation is required to run synthetic tests."
        )

    try:
        report = await execute_journey(request.scenario)
        return report

    except URLValidationError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )
    except PlaywrightError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Browser automation error during journey execution: {str(error)}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Journey execution failed: {str(error)}"
        )


@router.post("/login", response_model=JourneyReport)
async def run_login_journey(request: LoginJourneyRequest):
    """
    Execute an automated authentication testing journey against a login page.
    Automatically formats credentials, masks sensitive inputs, and verifies login indicators.
    """

    if not request.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Authorization confirmation is required to run synthetic tests."
        )
    try:
        validate_url(str(request.login_url))
    except URLValidationError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    try:
        scenario = create_login_scenario(request)
        report = await execute_journey(scenario)
        return report

    except PlaywrightError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Browser automation error during login journey: {str(error)}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Login journey failed: {str(error)}"
        )



@router.post("/login", response_model=JourneyReport)
async def run_login_journey(request: LoginJourneyRequest):
    """
    Execute an automated authentication testing journey against a login page.
    Automatically formats credentials, masks sensitive inputs, and verifies login indicators.
    """

    if not request.authorization_confirmed:
        raise HTTPException(
            status_code=403,
            detail="Authorization confirmation is required to run synthetic tests."
        )

    # ── SSRF URL Validation ──
    try:
        validate_url(str(request.login_url))
    except URLValidationError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    try:
        scenario = create_login_scenario(request)
        report = await execute_journey(scenario)
        return report

    except PlaywrightError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Browser automation error during login journey: {str(error)}"
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Login journey failed: {str(error)}"
        )


