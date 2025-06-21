"""
A video generation workflow.
"""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

from temporalio import workflow
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

with workflow.unsafe.imports_passed_through():
    from pydantic import BaseModel, Field

    from workflows.videogen.activities import (
        CreateScenesInput,
        GenerateVideoForSceneInput,
        GoogleCloudActivities,
        MergeVideosInput,
        UploadFileInput,
        VideoGenerationActivities,
        create_video_directory,
    )
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

    video_path: str = Field(
        description="The path of the video in GCS.",
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
        workflow.logger.info(
            "Running workflow. input=%s. start_time=%s",
            arg,
            workflow_start_time,
        )

        # Expand user prompt into movie scenes.
        scenes = await workflow.execute_activity_method(
            VideoGenerationActivities.create_scenes,
            CreateScenesInput(prompt=arg.user_prompt),
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info("Scene development completed. scene_count=%s", len(scenes))

        # Create a staging directory to store the videos.
        video_dir = await workflow.execute_activity(
            create_video_directory,
            start_to_close_timeout=timedelta(seconds=5),
        )
        workflow.logger.info("Staging directory created. path=%s", video_dir)

        previous_video_path: Path | None = None
        scene_video_map: dict[int, Path] = {}
        # For each scene, generate a video. If there is a previous scene,
        # use the last frame of the previous video as a reference image for VGM.
        for scene in scenes:
            vgm_prompt: str = await workflow.execute_activity_method(
                VideoGenerationActivities.generate_vgm_prompt,
                scene,
                start_to_close_timeout=timedelta(seconds=30),
            )
            scene.vgm_prompt = vgm_prompt
            video_path: Path = await workflow.execute_activity_method(
                VideoGenerationActivities.generate_video_for_scene,
                GenerateVideoForSceneInput(
                    current_scene=scene,
                    previous_video_path=previous_video_path,
                    staging_directory=video_dir,
                    output_path=video_dir / f"scene_{scene.sequence_number}.mp4",
                ),
                start_to_close_timeout=timedelta(minutes=2),
            )
            previous_video_path = video_path
            scene_video_map[scene.sequence_number] = video_path
            workflow.logger.info("Scene video generated. video_path=%s", video_path)

        # Combine the video scenes into a single video.
        final_video_path = await workflow.execute_activity(
            VideoGenerationActivities.merge_videos,
            MergeVideosInput(
                video_paths=list(scene_video_map.values()),
                output_path=video_dir / arg.output_video_name,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info("Final video generated. video_path=%s", final_video_path)

        # Upload the videos to GCS.
        gcs_bucket = video_gen_settings.GCS_BUCKET_NAME
        destination_path = (
            f"{workflow_start_time.strftime('%Y%m%d_%H%M%S')}/{arg.output_video_name}"
        )
        await workflow.execute_activity(
            GoogleCloudActivities.upload_file,
            UploadFileInput(
                bucket_name=gcs_bucket,
                source_path=final_video_path,
                destination_path=destination_path,
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )
        workflow.logger.info(
            "Final video uploaded to GCS. bucket=%s, path=%s",
            gcs_bucket,
            arg.output_video_name,
        )

        return VideoGenerationWorkflowOutput(
            video_path=f"gs://{gcs_bucket}/{destination_path}"
        )


async def main():
    """
    Main function.
    """
    import logging

    logging.basicConfig(level=logging.INFO)

    # Start client
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    TASK_QUEUE = "video-gen-task-queue"
    # Run a worker for the workflow
    video_generation_activities = VideoGenerationActivities()
    google_cloud_activities = GoogleCloudActivities()
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[VideoGenerationWorkflow],
        activities=[
            video_generation_activities.create_scenes,
            video_generation_activities.generate_vgm_prompt,
            video_generation_activities.generate_video_for_scene,
            video_generation_activities.merge_videos,
            google_cloud_activities.upload_file,
            create_video_directory,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=5),
    ):
        result = await client.execute_workflow(
            VideoGenerationWorkflow.run,
            VideoGenerationWorkflowInput(
                user_prompt="A dog chases a person running in a park."
            ),
            id=f"video-gen-workflow-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
