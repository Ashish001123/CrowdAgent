from urllib.parse import urlparse

def classify_http_response(
    error: dict,
    expected_http_statuses: dict | None = None
):
    expected_http_statuses = expected_http_statuses or {}

    url = error["url"]
    actual_status = error["status"]

    path = urlparse(url).path

    expected_statuses = expected_http_statuses.get(path, [])

    if actual_status in expected_statuses:
        return {
            "type": "http_response",
            "url": url,
            "actual_status": actual_status,
            "expected_statuses": expected_statuses,
            "classification": "passed",
            "severity": "none",
            "reason": "The HTTP response matches the expected behavior.",
            "requires_investigation": False
        }

    if actual_status >= 500:
        severity = "high"
        reason = "The server returned an unexpected 5xx response."

    elif actual_status >= 400:
        severity = "medium"
        reason = "The endpoint returned an unexpected 4xx response."

    else:
        severity = "low"
        reason = "The response did not match the configured expected status."

    return {
        "type": "http_response",
        "url": url,
        "actual_status": actual_status,
        "expected_statuses": expected_statuses,
        "classification": "potential_issue",
        "severity": severity,
        "reason": reason,
        "requires_investigation": True
    }