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


def test_merge_videos():
    """
    Test the merge_videos function.
    """
    video_paths = [
        Path(
            "/var/folders/0j/4l7tq3057m70lpvnmkc2bd5m0000gn/T/tmpu4u1zt9h/20250620_132505_0.mp4"
        ),
        Path(
            "/var/folders/0j/4l7tq3057m70lpvnmkc2bd5m0000gn/T/tmpu4u1zt9h/20250620_132548_0.mp4"
        ),
        Path(
            "/var/folders/0j/4l7tq3057m70lpvnmkc2bd5m0000gn/T/tmpu4u1zt9h/20250620_132505_0.mp4"
        ),
    ]
    output_path = Path(
        "/Users/kawofong/Workspace/temporal-videos/build/merged_video.mp4"
    )
    result = VideoEditor.merge_videos(video_paths, output_path)
    print(result)


if __name__ == "__main__":
    test_merge_videos()
