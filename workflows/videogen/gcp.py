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
        Upload a blob to Google Cloud Storage.
        """
        cls._client.bucket(bucket_name).blob(destination_path).upload_from_filename(
            file_path
        )

    @classmethod
    def download_blob(
        cls, bucket_name: str, source_blob_name: str, destination_file_path: Path
    ) -> None:
        """
        Download a blob from Google Cloud Storage.
        """
        cls._client.bucket(bucket_name).blob(source_blob_name).download_to_filename(
            destination_file_path
        )
