from datetime import datetime, timezone

from schema.schema import Issue, Evidence, ScanSummary, ScanReport


def _generate_issue_id(counter: int) -> str:
    """Generate a unique issue ID like CRA-0001."""
    return f"CRA-{counter:04d}"


def _build_http_issue(raw: dict, page_url: str, counter: int) -> Issue | None:
    """
    Convert a classified HTTP issue into a structured Issue.

    Skips issues that were classified as 'passed' — those are
    expected responses that do not need reporting.
    """

    if raw.get("classification") == "passed":
        return None

    status = raw["actual_status"]

    return Issue(
        issue_id=_generate_issue_id(counter),
        title=f"HTTP {status} on {raw['url']}",
        category="http_error",
        severity=raw["severity"],
        classification=raw["classification"],
        page_url=page_url,
        description=raw["reason"],
        evidence=Evidence(
            source_url=raw["url"],
            detail=f"Expected statuses: {raw['expected_statuses']}, "
                   f"Actual status: {status}"
        ),
        recommendation=_http_recommendation(status),
        requires_investigation=raw["requires_investigation"],
        detected_at=datetime.now(timezone.utc)
    )


def _http_recommendation(status: int) -> str:
    """Return a developer-facing recommendation based on HTTP status."""

    if status == 401:
        return "Check authentication configuration. The endpoint may require valid credentials."

    if status == 403:
        return "Check authorization rules. The current user may lack required permissions."

    if status == 404:
        return "Verify the endpoint URL exists. It may have been removed or renamed."

    if status >= 500:
        return "Investigate the server logs. A 5xx error indicates a server-side failure."

    return "Review the endpoint behavior. The response status was not expected."


def _build_console_issue(error: dict, page_url: str, counter: int) -> Issue:
    """Convert a browser console error into a structured Issue."""

    return Issue(
        issue_id=_generate_issue_id(counter),
        title=f"Console error: {error['message'][:80]}",
        category="console_error",
        severity="medium",
        classification="potential_issue",
        page_url=page_url,
        description=f"The browser console logged an error: {error['message']}",
        evidence=Evidence(
            source_url=page_url,
            detail=f"Console {error['type']}: {error['message']}"
        ),
        recommendation="Inspect the browser console for this page. "
                       "Console errors may indicate broken scripts or missing resources.",
        requires_investigation=True,
        detected_at=datetime.now(timezone.utc)
    )


def _build_page_error_issue(error_text: str, page_url: str, counter: int) -> Issue:
    """Convert an uncaught JavaScript exception into a structured Issue."""

    return Issue(
        issue_id=_generate_issue_id(counter),
        title=f"Uncaught exception: {error_text[:80]}",
        category="page_error",
        severity="high",
        classification="potential_issue",
        page_url=page_url,
        description=f"An uncaught JavaScript exception occurred: {error_text}",
        evidence=Evidence(
            source_url=page_url,
            detail=f"Uncaught exception: {error_text}"
        ),
        recommendation="This is an unhandled JavaScript error. "
                       "Check the stack trace and fix the failing code path.",
        requires_investigation=True,
        detected_at=datetime.now(timezone.utc)
    )


def _build_failed_request_issue(request: dict, page_url: str, counter: int) -> Issue:
    """Convert a failed network request into a structured Issue."""

    return Issue(
        issue_id=_generate_issue_id(counter),
        title=f"Failed request: {request['url'][:80]}",
        category="failed_request",
        severity="high",
        classification="potential_issue",
        page_url=page_url,
        description=f"A network request failed completely: {request['url']}",
        evidence=Evidence(
            source_url=request["url"],
            detail=f"Failure reason: {request['error']}"
        ),
        recommendation="The request did not reach the server or was blocked. "
                       "Check CORS settings, network connectivity, and the target URL.",
        requires_investigation=True,
        detected_at=datetime.now(timezone.utc)
    )


def _build_summary(issues: list[Issue]) -> ScanSummary:
    """Build aggregate counts from a list of issues."""

    by_category: dict[str, int] = {}
    high = 0
    medium = 0
    low = 0

    for issue in issues:

        by_category[issue.category] = by_category.get(issue.category, 0) + 1

        if issue.severity == "high":
            high += 1
        elif issue.severity == "medium":
            medium += 1
        elif issue.severity == "low":
            low += 1

    return ScanSummary(
        total_issues=len(issues),
        high_severity=high,
        medium_severity=medium,
        low_severity=low,
        by_category=by_category
    )


def generate_report(scan_result: dict) -> ScanReport:
    """
    Transform raw scan results from browser_service.analyze_website()
    into a structured ScanReport.

    This is the main entry point for the reporter service.
    """

    page_url = scan_result["url"]
    issues: list[Issue] = []
    counter = 1

    for raw_issue in scan_result.get("issues", []):
        issue = _build_http_issue(raw_issue, page_url, counter)
        if issue is not None:
            issues.append(issue)
            counter += 1

    for error in scan_result.get("console_errors", []):
        issues.append(
            _build_console_issue(error, page_url, counter)
        )
        counter += 1

    for error_text in scan_result.get("page_errors", []):
        issues.append(
            _build_page_error_issue(error_text, page_url, counter)
        )
        counter += 1    

    for request in scan_result.get("failed_requests", []):
        issues.append(
            _build_failed_request_issue(request, page_url, counter)
        )
        counter += 1

    summary = _build_summary(issues)

    return ScanReport(
        scan_url=page_url,
        final_url=page_url,
        page_title=scan_result.get("title", ""),
        http_status=scan_result.get("http_status"),
        buttons=scan_result.get("buttons", []),
        links=scan_result.get("links", []),
        forms_count=scan_result.get("forms_count", 0),
        issues=issues,
        summary=summary,
        screenshot_path=scan_result.get("screenshot_path"),
        scanned_at=datetime.now(timezone.utc)
    )

