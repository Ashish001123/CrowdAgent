from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from enum import Enum


class WebsiteScanRequest(BaseModel):
    url: HttpUrl

    authorization_confirmed: bool

    expected_http_statuses: dict[str, list[int]] = Field(
        default_factory=dict,
        description="Expected HTTP status codes mapped by endpoint path"
    )



class Evidence(BaseModel):
    """Raw evidence collected from the browser for a single issue."""

    source_url: str = Field(
        description="The URL where the issue was observed"
    )

    detail: str = Field(
        description="Technical detail such as status code, error message, or log text"
    )


class Issue(BaseModel):
    """A single classified issue found during a scan."""

    issue_id: str = Field(
        description="Unique issue identifier, e.g. CRA-0001"
    )

    title: str = Field(
        description="Short human-readable title"
    )

    category: str = Field(
        description="Issue category: http_error | console_error | page_error | failed_request"
    )

    severity: str = Field(
        description="Severity level: high | medium | low"
    )

    classification: str = Field(
        description="Either 'passed' or 'potential_issue'"
    )

    page_url: str = Field(
        description="The page URL where the issue was detected"
    )

    description: str = Field(
        description="Detailed explanation of what went wrong"
    )

    evidence: Evidence

    recommendation: str = Field(
        description="Suggested action the developer should take"
    )

    requires_investigation: bool = Field(
        default=True,
        description="Whether this issue needs manual review"
    )

    detected_at: datetime = Field(
        description="UTC timestamp when the issue was detected"
    )


class ScanSummary(BaseModel):
    """Aggregate counts for a scan report."""

    total_issues: int = 0

    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0

    by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Issue count grouped by category"
    )


class ScanReport(BaseModel):
    """Complete structured report for a website scan."""

    scan_url: str
    final_url: str
    page_title: str
    http_status: int | None

    buttons: list[str]
    links: list[str]
    forms_count: int

    issues: list[Issue]
    summary: ScanSummary

    screenshot_path: str | None = Field(
        default=None,
        description="File path to the full-page screenshot captured during the scan"
    )

    scanned_at: datetime = Field(
        description="UTC timestamp when the scan completed"
    )


# ── User Journey Models ──────────────────────────────────────


class ActionType(str, Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_TEXT = "assert_text"
    WAIT = "wait"


class JourneyStep(BaseModel):
    """A single deterministic action or assertion in a journey."""

    action: ActionType = Field(
        description="Type of action: navigate, click, fill, assert_visible, assert_text, wait"
    )

    selector: str | None = Field(
        default=None,
        description="CSS selector, XPath, or text selector (e.g. 'button:has-text(\"Login\")')"
    )

    value: str | None = Field(
        default=None,
        description="Value needed for the action (URL for navigate, text for fill, expected text for assert_text, seconds for wait)"
    )

    description: str = Field(
        default="",
        description="Human-readable description of what this step does"
    )


class JourneyScenario(BaseModel):
    """A complete user testing scenario composed of ordered steps."""

    scenario_id: str = Field(
        description="Identifier for the scenario, e.g. SCN-LOGIN-01"
    )

    name: str = Field(
        description="Descriptive scenario name, e.g. 'Standard User Login Flow'"
    )

    persona: str = Field(
        default="New User",
        description="Synthetic user persona executing this scenario"
    )

    objective: str = Field(
        description="What this journey aims to verify"
    )

    steps: list[JourneyStep] = Field(
        description="Ordered sequence of steps to perform"
    )


class StepResult(BaseModel):
    """Execution outcome for a single step in a journey."""

    step_index: int
    action: str
    description: str
    status: str = Field(
        description="'passed' or 'failed'"
    )
    duration_ms: float
    error_message: str | None = None
    screenshot_path: str | None = None


class JourneyReport(BaseModel):
    """Comprehensive test report for an executed journey scenario."""

    scenario_id: str
    name: str
    persona: str
    objective: str
    status: str = Field(
        description="'passed' if all steps passed, 'failed' if any step failed"
    )
    total_steps: int
    passed_steps: int
    failed_step_index: int | None = None
    duration_ms: float
    step_results: list[StepResult]
    reproduction_steps: list[str] = Field(
        default_factory=list,
        description="Clear step-by-step instructions to reproduce the test outcome"
    )
    executed_at: datetime


class JourneyRunRequest(BaseModel):
    """Request to execute a journey scenario."""

    scenario: JourneyScenario
    authorization_confirmed: bool

