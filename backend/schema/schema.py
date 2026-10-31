from pydantic import BaseModel, HttpUrl, Field


class WebsiteScanRequest(BaseModel):
    url: HttpUrl

    authorization_confirmed: bool

    expected_http_statuses: dict[str, list[int]] = Field(
        default_factory=dict,
        description="Expected HTTP status codes mapped by endpoint path"
    )