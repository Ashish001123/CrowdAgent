from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime


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
