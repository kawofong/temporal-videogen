"""
Settings for the VideoGen Workflow.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class VideoGenSettings(BaseSettings):
    """
    Settings for the VideoGen Workflow.
    """

    GOOGLE_API_KEY: str = Field(description="The API key for Google language models.")
    GCS_BUCKET_NAME: str = Field(
        description="The name of the Google Cloud Storage bucket to store generated videos.",
        default="kawo-temporal-videos-bucket",
    )


video_gen_settings = VideoGenSettings()
