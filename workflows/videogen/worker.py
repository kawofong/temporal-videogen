"""
Temporal Worker for the VideoGen Workflow.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from workflows.videogen.activities import VideoGenerationActivities
from workflows.videogen.constants import TASK_QUEUE
from workflows.videogen.videogen import VideoGenerationWorkflow

logging.basicConfig(level=logging.INFO)


async def main():
    """
    Main function.
    """
    # Start client
    client = await Client.connect(
        "localhost:7233",
        data_converter=pydantic_data_converter,
    )

    # Run a worker for the workflow
    video_generation_activities = VideoGenerationActivities()
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[VideoGenerationWorkflow],
        activities=[
            video_generation_activities.create_scenes,
            video_generation_activities.generate_vgm_prompt,
            video_generation_activities.generate_video_for_scene,
            video_generation_activities.merge_videos,
        ],
        activity_executor=ThreadPoolExecutor(max_workers=5),
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
