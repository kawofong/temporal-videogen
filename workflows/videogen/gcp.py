"""
GCP utilities.
"""

from pathlib import Path

from google.cloud import storage


class GoogleCloudStorage:
    """
    Google Cloud Storage utilities.
    """

    _client = storage.Client()

    @classmethod
    def upload_file(
        cls, bucket_name: str, file_path: Path, destination_path: str
    ) -> None:
        """
        Upload a file to Google Cloud Storage.
        """
        cls._client.bucket(bucket_name).blob(destination_path).upload_from_filename(
            file_path
        )


def test_upload_file():
    """
    Test the upload_file function.
    """
    GoogleCloudStorage.upload_file(
        bucket_name="kawo-temporal-videos-bucket",
        file_path=Path(
            "/Users/kawofong/Workspace/temporal-videos/build/merged_video.mp4"
        ),
        destination_path="merged_video.mp4",
    )


if __name__ == "__main__":
    test_upload_file()
