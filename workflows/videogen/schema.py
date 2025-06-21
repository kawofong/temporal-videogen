"""
Relevant data models for video generation.
"""

from pydantic import BaseModel, Field


class Scene(BaseModel):
    """
    A scene in a video.
    """

    sequence_number: int = Field(description="The sequence number of the scene.")
    description: str = Field(
        description="A detailed description of what happens in this scene.",
    )
    duration_estimate: int = Field(
        description="The estimated duration of the scene in seconds.",
    )
    camera_angle: str = Field(
        description="The camera angle for this scene.",
        default="overhead shot",
    )
    lighting: str = Field(
        description="The lighting for this scene.",
        default="natural daylight",
    )
    vgm_prompt: str | None = Field(
        description="The optimized VGM prompt for this scene.",
        default=None,
    )
