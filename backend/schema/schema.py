from pydantic import BaseModel, HttpUrl, Field


class WebsiteScanRequest(BaseModel):
    url: HttpUrl

    authorization_confirmed: bool = Field(
        ...,
        description="Developer confirms permission to test this website"
    )