"""
Video Editor.
"""

from pathlib import Path

from moviepy import VideoFileClip, concatenate_videoclips


class VideoEditor:
    """
    Video Editor.
    """

    @staticmethod
    def merge_videos(video_paths: list[Path], output_path: Path) -> Path:
        """
        Merge videos into a single video, with no transition between videos.
        """
        video_clips = [VideoFileClip(path) for path in video_paths]
        final_video = concatenate_videoclips(video_clips)
        final_video.write_videofile(
            filename=output_path,
            remove_temp=True,
        )
        final_video.close()
        return output_path
