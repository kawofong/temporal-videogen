"""
Video generation model.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai.types import GenerateVideosConfig, Image

logger = logging.getLogger(__name__)


class BaseVideoGenerationModel(ABC):
    """
    Base class for video generation models.
    """

    @abstractmethod
    async def generate_video(
        self, prompt: str, output_path: Path, image_path: Path | None = None
    ):
        """
        Generate video from the prompt.
        """
        raise NotImplementedError("Subclasses must implement this method")


class GoogleVeo2(BaseVideoGenerationModel):
    """
    Using Google Veo2 as a video generation model.
    """

    def __init__(self, api_key: str, model_name: str = "veo-2.0-generate-001"):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        logger.info("GoogleVeo2 initialized. model_name=%s", model_name)

    async def generate_video(
        self, prompt: str, output_path: Path, image_path: Path | None = None
    ) -> Path:
        """
        Use Google Veo2 to generate video from the prompt.
        """
        start_time = datetime.now()

        logger.info(
            "Starting video generation. output_path=%s. start_time=%s",
            str(output_path),
            start_time,
        )

        default_veo2_config = GenerateVideosConfig(
            person_generation="allow_adult",  # "dont_allow" or "allow_adult"
            aspect_ratio="16:9",  # "16:9" or "9:16"
            number_of_videos=1,
            duration_seconds=5,
            negative_prompt="text,text overlay,text on screen",
        )

        if image_path is not None:
            image_bytes = image_path.read_bytes()
            image = Image(
                image_bytes=image_bytes,
                mime_type="image/png",
            )
            operation = await self._client.aio.models.generate_videos(
                model=self._model_name,
                prompt=prompt,
                image=image,
                config=default_veo2_config,
            )
        else:
            operation = await self._client.aio.models.generate_videos(
                model=self._model_name,
                prompt=prompt,
                config=default_veo2_config,
            )

        # Wait for videos to generate
        wait_count = 0
        while not operation.done:
            await asyncio.sleep(10)
            wait_count += 1
            operation = self._client.operations.get(operation)

            logger.debug(
                "Waiting for video generation to complete. wait_count=%s.",
                wait_count,
            )

        if operation.response.generated_videos is None:
            raise RuntimeError(
                "No video is generated for scene.",
                response=str(operation.response),
            )

        logger.info(
            "Video generation operation completed. elapsed_time=%s. video_count=%s",
            datetime.now() - start_time,
            len(operation.response.generated_videos),
        )

        # Given that default_veo2_config is set to generate 1 video,
        # we assume that there is only 1 generated video and process it.
        video = operation.response.generated_videos[0]
        self._client.files.download(file=video.video)
        video.video.save(output_path)

        logger.info(
            "Video generation completed successfully. output_path=%s",
            output_path,
        )

        return output_path
