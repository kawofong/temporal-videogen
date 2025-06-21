"""
Video generation activities.
"""

import tempfile
from pathlib import Path

from moviepy import VideoFileClip
from pydantic import BaseModel, Field
from temporalio import activity

from workflows.videogen.gcp import GoogleCloudStorage
from workflows.videogen.llm import GoogleGemini
from workflows.videogen.schema import Scene
from workflows.videogen.settings import video_gen_settings
from workflows.videogen.vgm import GoogleVeo2
from workflows.videogen.video import VideoEditor


class CreateScenesInput(BaseModel):
    """
    Create Scenes Input.
    """

    prompt: str = Field(description="The user prompt for creating scenes.")


class GenerateVideoForSceneInput(BaseModel):
    """
    Generate Video for Scene Input.
    """

    current_scene: Scene = Field(
        description="The current scene to generate a video for."
    )
    previous_video_path: Path | None = Field(
        description="File path to previous video in the sequence.",
        default=None,
    )
    staging_directory: Path = Field(
        description="The path to the staging directory.",
    )
    output_path: Path = Field(
        description="The path to the output video.",
    )


class MergeVideosInput(BaseModel):
    """
    Merge Videos Input.
    """

    video_paths: list[Path] = Field(
        description="The paths of the videos to merge.",
    )
    output_path: Path = Field(
        description="The path of the output video.",
    )


class VideoGenerationActivities:
    """
    Video Generation activities.
    """

    def __init__(self):
        self._google_api_key = video_gen_settings.GOOGLE_API_KEY

    @activity.defn
    async def create_scenes(self, arg: CreateScenesInput) -> list[Scene]:
        """
        Create Scenes from a prompt.
        """
        activity.logger.info("Creating scenes from prompt. arg=%s", arg)

        llm = GoogleGemini(api_key=self._google_api_key)
        llm_prompt = f"""
You are a creative AI agent that transforms user input into cinematic movie scenes. Your task is to take any concept, story, or idea and convert it into a compelling visual narrative with dramatic flair and artistic vision.

# Requirements:
* Create exactly 1-5 scenes that tell a complete story with a clear beginning and satisfying ending
* Each scene must be 5-8 seconds long
* NO overlay text or written words should appear in any scene
* For each scene, provide detailed camera angle and lighting descriptions
* Embrace bold creativity - think like a visionary director pushing artistic boundaries

# Scene Structure:
* Scene 1 (Opening): Establish the story
* Scene 2-3 (Development): [Optional] Build tension
* Scene 4-5 (Resolution): Deliver a powerful, memorable conclusion

# Technical Specifications:
* For each scene, specify:
  * Camera Angle: (e.g., extreme close-up, wide shot, low angle, aerial view, tracking shot)
  * Lighting: (e.g., golden hour, dramatic shadows, neon glow, soft natural light, harsh fluorescent)
  * Visual Description: Paint a vivid picture of what unfolds on screen

Transform the user's input into something unexpectedly cinematic, whether it's mundane or fantastical. Make every second count and every frame visually stunning.

User Input: {arg.prompt}
"""

        response: list[Scene] = await llm.generate_content(
            prompt=llm_prompt,
            response_schema=list[Scene],
        )
        return response

    @activity.defn
    async def generate_video_for_scene(self, arg: GenerateVideoForSceneInput) -> Path:
        """
        Generate a video for a scene.
        """
        activity.logger.info("Generating a video for the scene. arg=%s", arg)
        vgm = GoogleVeo2(api_key=self._google_api_key)
        vgm_prompt = f"""
{arg.current_scene.description}. The camera uses {arg.current_scene.camera_angle}. The lighting is {arg.current_scene.lighting}.
"""
        # Save the last frame of the previous video as a reference image for VGM.
        if arg.previous_video_path is not None:
            # Use moviepy to extract the last frame of the previous video.
            video = VideoFileClip(arg.previous_video_path)
            image_path = (
                arg.staging_directory
                / f"scene_{arg.current_scene.sequence_number}_last_frame.png"
            )
            video.save_frame(image_path, t=float(video.duration - 0.01))
        else:
            image_path = None

        output_path = await vgm.generate_video(
            prompt=vgm_prompt,
            output_path=arg.output_path,
            image_path=image_path,
        )

        return output_path

    @activity.defn
    async def merge_videos(self, arg: MergeVideosInput) -> Path:
        """
        Merge videos into a single video.
        """
        activity.logger.info("Merging videos into a single video. arg=%s", arg)

        return VideoEditor.merge_videos(
            video_paths=arg.video_paths, output_path=arg.output_path
        )


@activity.defn
def create_video_directory() -> Path:
    """
    Create a staging video directory.
    """
    # use tempdir to create a unique directory
    output_path = Path(tempfile.mkdtemp())
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


class UploadFileInput(BaseModel):
    """
    Upload File Input.
    """

    bucket_name: str = Field(
        description="The name of the bucket to upload the file to."
    )
    source_path: Path = Field(description="The path of the file to upload.")
    destination_path: str = Field(
        description="The path of the file stored in the bucket."
    )


class GoogleCloudActivities:
    """
    Google Cloud activities.
    """

    @activity.defn
    def upload_file(self, arg: UploadFileInput) -> None:
        """
        Upload a file to Google Cloud Storage.
        """
        GoogleCloudStorage.upload_file(
            bucket_name=arg.bucket_name,
            file_path=arg.source_path,
            destination_path=arg.destination_path,
        )
