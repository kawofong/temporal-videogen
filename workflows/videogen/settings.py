"""
Settings for the VideoGen Workflow.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class VideoGenSettings(BaseSettings):
    """
    Settings for the VideoGen Workflow.
    """

    model_config = SettingsConfigDict(
        env_file=".envrc",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    GOOGLE_API_KEY: str = Field(description="The API key for Google language models.")
    GCS_BUCKET_NAME: str = Field(
        description="The name of the Google Cloud Storage bucket to store generated videos.",
    )


video_gen_settings = VideoGenSettings()
