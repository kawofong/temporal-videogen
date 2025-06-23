"""
Video generation activities.
"""

import tempfile
from pathlib import Path

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
    gcs_staging_directory: str = Field(
        description="The path to the staging directory in Google Cloud Storage.",
    )


class MergeVideosInput(BaseModel):
    """
    Merge Videos Input.
    """

    gcs_video_paths: list[str] = Field(
        description="The paths of the videos to merge.",
    )
    gcs_staging_directory: str = Field(
        description="The path to the staging directory in Google Cloud Storage.",
    )


class VideoGenerationActivities:
    """
    Video Generation activities.
    """

    def __init__(self):
        self._google_api_key = video_gen_settings.GOOGLE_API_KEY
        self._llm = GoogleGemini(api_key=self._google_api_key)
        self._vgm = GoogleVeo2(api_key=self._google_api_key)

    @activity.defn
    async def create_scenes(self, arg: CreateScenesInput) -> list[Scene]:
        """
        Create Scenes from a prompt.
        """
        activity.logger.info("Creating scenes from prompt. arg=%s", arg)

        llm_prompt = f"""
You are a creative AI agent that transforms user input into cinematic movie scenes. Your task is to take any concept, story, or idea and convert it into a compelling visual narrative with dramatic flair and artistic vision.

# Requirements:
* Create exactly 3-8 scenes that tell a complete story with a clear beginning and satisfying ending
* Each scene must be 5 seconds long
* NO overlay text or written words should appear in any scene
* For each scene, provide detailed camera angle and lighting descriptions
* Embrace bold creativity - think like a visionary director pushing artistic boundaries

# Scene Structure:
* Opening: Establish the story
* Development: Build tension
* Resolution: Deliver a powerful, memorable conclusion

# Technical Specifications:
* For each scene, specify:
  * Camera Angle: (e.g., extreme close-up, wide shot, low angle, aerial view, tracking shot)
  * Lighting: (e.g., golden hour, dramatic shadows, neon glow, soft natural light, harsh fluorescent)
  * Visual Description: Paint a vivid picture of what unfolds on screen

Transform the user's input into something unexpectedly cinematic, whether it's mundane or fantastical. Make every second count and every frame visually stunning.

User Input: {arg.prompt}
"""

        response: list[Scene] = await self._llm.generate_content(
            prompt=llm_prompt,
            response_schema=list[Scene],
        )
        return response

    @activity.defn
    async def generate_vgm_prompt(self, scene: Scene) -> str:
        """
        Generate an optimized VGM prompt for a scene.
        """
        activity.logger.info("Generating a VGM prompt for the scene. scene=%s", scene)
        llm_prompt = f"""
As a Veo 2 video generation agent, your goal is to create compelling and high-quality video clips based on detailed scene descriptions. You will receive specific scene parameters and should interpret them to craft a vivid and precise video generation prompt for Veo 2.

**Prompt Structure for Veo 2:**

Your output should be a single, cohesive prompt that Veo 2 can directly process.

**Parameters to Extract and Interpret from Scene Information:**

* **VISUAL_DESCRIPTION:** This is the core of the prompt. Translate the `description` field into a highly descriptive and evocative visual narrative. Focus on:
    * **Subjects:** What is present? (e.g., "bare feet," "dancers' lower bodies")
    * **Actions:** What are they doing? (e.g., "kicking up golden dust," "moving rhythmically," "spin and twirl")
    * **Key Details:** Emphasize unique visual elements (e.g., "golden dust," "vibrant, flowing fabrics").
    * **Mood/Atmosphere:** Convey the feeling (e.g., "powerful," "increasing energy and freedom").
    * **Shot Type:** Integrate the `camera_angle` as a descriptive element within the visual description, especially for initial framing (e.g., "An extreme close-up...").

* **CAMERA_MOVEMENT :** Directly translate the `camera_angle` information. Use Veo 2 compatible terms:
    * `tracking shot`
    * `tilt up`
    * `pan left/right`
    * `zoom in/out`
    * `dolly in/out`
    * Combine multiple movements if described.

* **LIGHTING_STYLE :** Directly translate or interpret the `lighting` field. Be specific and use evocative terms:
    * `golden hour backlighting`
    * `prominent lens flares`
    * `long, dynamic shadows`
    * `soft ambient light`
    * `harsh industrial light`

**Optimize Prompt for Veo 2**

Use the parameters above to generate an optimized prompt for Veo 2.

**Input Scene:**

{scene}

**Optimized Veo 2 Prompt:**
"""
        optimized_vgm_prompt: str = await self._llm.generate_content(
            prompt=llm_prompt,
        )
        return optimized_vgm_prompt

    @activity.defn
    async def generate_video_for_scene(self, arg: GenerateVideoForSceneInput) -> str:
        """
        Generate a video for a scene and store it in Google Cloud Storage.
        """
        activity.logger.info("Generating a video for the scene. arg=%s", arg)
        vgm_prompt = arg.current_scene.vgm_prompt
        if vgm_prompt is None:
            vgm_prompt = f"""
{arg.current_scene.description}.
The camera uses {arg.current_scene.camera_angle}.
The lighting is {arg.current_scene.lighting}.
"""

        video_name = f"scene_{arg.current_scene.sequence_number}.mp4"
        gcs_destination_path = f"{arg.gcs_staging_directory}/{video_name}"
        # Generate the video in a local temporary directory, then upload it to Google Cloud Storage.
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / video_name
            output_path = await self._vgm.generate_video(
                prompt=vgm_prompt,
                output_path=output_path,
            )
            GoogleCloudStorage.upload_file(
                bucket_name=video_gen_settings.GCS_BUCKET_NAME,
                file_path=output_path,
                destination_path=gcs_destination_path,
            )

        return gcs_destination_path

    @activity.defn
    async def merge_videos(self, arg: MergeVideosInput) -> str:
        """
        Merge videos into a single video and store it in Google Cloud Storage.
        """
        activity.logger.info("Merging videos into a single video. arg=%s", arg)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            downloaded_video_paths: list[Path] = []
            # Download the videos from Google Cloud Storage.
            for gcs_name in arg.gcs_video_paths:
                video_name = Path(gcs_name).name
                downloaded_video_path = temp_dir / video_name
                GoogleCloudStorage.download_blob(
                    bucket_name=video_gen_settings.GCS_BUCKET_NAME,
                    source_blob_name=gcs_name,
                    destination_file_path=downloaded_video_path,
                )
                downloaded_video_paths.append(downloaded_video_path)

            # Merge the videos into a single video.
            video_name = "full_video.mp4"
            gcs_destination_name = f"{arg.gcs_staging_directory}/{video_name}"
            full_video_output_path = temp_dir / video_name
            VideoEditor.merge_videos(
                video_paths=downloaded_video_paths, output_path=full_video_output_path
            )

            # Upload the merged video to Google Cloud Storage.
            GoogleCloudStorage.upload_file(
                bucket_name=video_gen_settings.GCS_BUCKET_NAME,
                file_path=full_video_output_path,
                destination_path=gcs_destination_name,
            )

        return gcs_destination_name
