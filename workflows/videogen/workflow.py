"""
A video generation workflow.
"""

import asyncio
import uuid
from datetime import timedelta

from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, Field

    from workflows.videogen.activities import (
        CreateScenesInput,
        GenerateVideoForSceneInput,
        MergeVideosInput,
        VideoGenerationActivities,
    )
    from workflows.videogen.schema import Scene
    from workflows.videogen.settings import video_gen_settings


class VideoGenerationWorkflowInput(BaseModel):
    """
    Video Generation Workflow Input.
    """

    user_prompt: str = Field(description="The user prompt to generate a video for.")
    output_video_name: str = Field(
        default="final_video.mp4",
        description=(
            "The name of the video to generate."
            "This will be used as the destination path in GCS."
        ),
    )


class VideoGenerationWorkflowOutput(BaseModel):
    """
    Video Generation Workflow Output.
    """

    gcs_uri: str = Field(
        description="The path of the video in GCS.",
        examples=[
            "gs://my-bucket/my-video.mp4",
            "gs://my-bucket/my-video-dir/my-video.mp4",
        ],
    )


@workflow.defn
class VideoGenerationWorkflow:
    """
    Video Generation Workflow.
    """

    @workflow.run
    async def run(
        self, arg: VideoGenerationWorkflowInput
    ) -> VideoGenerationWorkflowOutput:
        """
        Main Workflow function.
        """
        workflow_start_time = workflow.now()
        gcs_staging_directory = (
            f"videos/{workflow_start_time.strftime('%Y%m%d_%H%M%S')}"
        )
        workflow.logger.info(
            "Running workflow. input=%s. start_time=%s. gcs=%s",
            arg,
            workflow_start_time,
            gcs_staging_directory,
        )

        # Expand user prompt into movie scenes.
        scenes = await workflow.execute_activity_method(
            VideoGenerationActivities.create_scenes,
            CreateScenesInput(prompt=arg.user_prompt),
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info("Scene development completed. scene_count=%s", len(scenes))

        scene_gcs_paths: list[tuple[int, str]] = []
        scene_gcs_paths = await asyncio.gather(
            *[self._process_scene(scene, gcs_staging_directory) for scene in scenes]
        )

        # Combine the video scenes into a single video.
        scene_gcs_paths.sort(key=lambda x: x[0])
        full_video_gcs_name: str = await workflow.execute_activity(
            VideoGenerationActivities.merge_videos,
            MergeVideosInput(
                gcs_video_paths=[x[1] for x in scene_gcs_paths],
                gcs_staging_directory=gcs_staging_directory,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info(
            "Final video generated and uploaded to GCS. bucket=%s, path=%s",
            video_gen_settings.GCS_BUCKET_NAME,
            full_video_gcs_name,
        )

        return VideoGenerationWorkflowOutput(
            gcs_uri=f"gs://{video_gen_settings.GCS_BUCKET_NAME}/{full_video_gcs_name}",
        )

    async def _process_scene(
        self,
        scene: Scene,
        gcs_staging_directory: str,
    ) -> tuple[int, str]:
        """
        Generate an optimized prompt for a scene and generate a video for it.
        """
        vgm_prompt: str = await workflow.start_activity_method(
            VideoGenerationActivities.generate_vgm_prompt,
            scene,
            start_to_close_timeout=timedelta(seconds=30),
        )
        scene.vgm_prompt = vgm_prompt
        gcs_path = await workflow.start_activity_method(
            VideoGenerationActivities.generate_video_for_scene,
            GenerateVideoForSceneInput(
                current_scene=scene,
                gcs_staging_directory=gcs_staging_directory,
            ),
            start_to_close_timeout=timedelta(minutes=2),
        )
        workflow.logger.info("Scene video generated. gcs_path=%s", gcs_path)
        return (scene.sequence_number, gcs_path)


async def main():
    """
    Main function.
    """
    from workflows.videogen.constants import TASK_QUEUE

    # Start client
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    result = await client.execute_workflow(
        VideoGenerationWorkflow.run,
        VideoGenerationWorkflowInput(
            user_prompt="A street magician performs for crowds in a busy plaza, notices his tricks are becoming real and causing chaos."
        ),
        id=f"video-gen-workflow-{uuid.uuid4()}",
        task_queue=TASK_QUEUE,
    )
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
