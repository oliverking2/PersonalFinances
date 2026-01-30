"""Tests for S3 client."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.providers.s3.client import generate_download_url, get_s3_client, upload_export


class TestGetS3Client:
    """Tests for get_s3_client function."""

    @patch("src.providers.s3.client.boto3")
    def test_creates_client_with_default_region(self, mock_boto3: MagicMock) -> None:
        """Creates client with eu-west-2 region by default."""
        with patch.dict("os.environ", {}, clear=True):
            get_s3_client()

        mock_boto3.client.assert_called_once()
        call_kwargs = mock_boto3.client.call_args
        assert call_kwargs[0][0] == "s3"
        assert call_kwargs[1]["region_name"] == "eu-west-2"

    @patch("src.providers.s3.client.boto3")
    def test_creates_client_with_custom_region(self, mock_boto3: MagicMock) -> None:
        """Uses AWS_REGION environment variable if set."""
        with patch.dict("os.environ", {"AWS_REGION": "us-east-1"}):
            get_s3_client()

        call_kwargs = mock_boto3.client.call_args
        assert call_kwargs[1]["region_name"] == "us-east-1"


class TestUploadExport:
    """Tests for upload_export function."""

    @patch("src.providers.s3.client.get_s3_client")
    def test_uploads_csv_file(self, mock_get_client: MagicMock) -> None:
        """Uploads CSV file with correct content type."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        user_id = uuid4()
        job_id = uuid4()
        content = b"id,name\n1,test"

        with patch.dict("os.environ", {"S3_EXPORTS_BUCKET": "test-bucket"}):
            key = upload_export(content, user_id, job_id, "csv")

        assert key == f"exports/{user_id}/{job_id}.csv"
        mock_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key=key,
            Body=content,
            ContentType="text/csv",
        )

    @patch("src.providers.s3.client.get_s3_client")
    def test_uploads_parquet_file(self, mock_get_client: MagicMock) -> None:
        """Uploads Parquet file with correct content type."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        user_id = uuid4()
        job_id = uuid4()
        content = b"parquet-binary-content"

        with patch.dict("os.environ", {"S3_EXPORTS_BUCKET": "test-bucket"}):
            key = upload_export(content, user_id, job_id, "parquet")

        assert key == f"exports/{user_id}/{job_id}.parquet"
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["ContentType"] == "application/octet-stream"

    def test_raises_if_bucket_not_configured(self) -> None:
        """Raises ValueError if S3_EXPORTS_BUCKET is not set."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="S3_EXPORTS_BUCKET"),
        ):
            upload_export(b"test", uuid4(), uuid4(), "csv")


class TestGenerateDownloadUrl:
    """Tests for generate_download_url function."""

    @patch("src.providers.s3.client.get_s3_client")
    def test_generates_presigned_url(self, mock_get_client: MagicMock) -> None:
        """Generates pre-signed URL with default expiry."""
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned-url"
        mock_get_client.return_value = mock_client

        s3_key = "exports/user-id/job-id.csv"

        with patch.dict("os.environ", {"S3_EXPORTS_BUCKET": "test-bucket"}):
            url = generate_download_url(s3_key)

        assert url == "https://presigned-url"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": s3_key},
            ExpiresIn=3600,
        )

    @patch("src.providers.s3.client.get_s3_client")
    def test_generates_presigned_url_with_custom_expiry(self, mock_get_client: MagicMock) -> None:
        """Uses custom expiry time if provided."""
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://presigned-url"
        mock_get_client.return_value = mock_client

        s3_key = "exports/user-id/job-id.csv"

        with patch.dict("os.environ", {"S3_EXPORTS_BUCKET": "test-bucket"}):
            generate_download_url(s3_key, expires_in=7200)

        call_kwargs = mock_client.generate_presigned_url.call_args
        assert call_kwargs[1]["ExpiresIn"] == 7200

    def test_raises_if_bucket_not_configured(self) -> None:
        """Raises ValueError if S3_EXPORTS_BUCKET is not set."""
        with (
            patch.dict("os.environ", {}, clear=True),
            pytest.raises(ValueError, match="S3_EXPORTS_BUCKET"),
        ):
            generate_download_url("exports/test.csv")
