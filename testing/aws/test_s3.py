"""Tests for AWS S3 module."""

import json
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock

import botocore.exceptions
import pandas as pd
import pytest

from src.aws.s3 import (
    get_csv_from_s3,
    get_file_from_s3,
    get_json_from_s3,
    infer_csv_fields_from_s3,
    upload_bytes_to_s3,
    upload_dataframe_to_s3_csv,
    upload_dataframe_to_s3_parquet,
    upload_file_to_s3,
)


class TestUploadDataframeToCsv:
    """Tests for upload_dataframe_to_s3_csv function."""

    def test_upload_dataframe_to_s3_csv_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful CSV upload."""
        df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

        result = upload_dataframe_to_s3_csv(mock_s3_client, df, "test-bucket", "prefix", "test.csv")

        assert result == "prefix/test.csv"
        mock_s3_client.upload_file.assert_called_once()

    def test_upload_dataframe_to_s3_csv_invalid_extension(self, mock_s3_client: MagicMock) -> None:
        """Test that non-CSV extension raises ValueError."""
        df = pd.DataFrame({"col1": [1, 2]})

        with pytest.raises(ValueError, match=r"File name must end with \.csv"):
            upload_dataframe_to_s3_csv(mock_s3_client, df, "test-bucket", "prefix", "test.txt")


class TestUploadFileToS3:
    """Tests for upload_file_to_s3 function."""

    def test_upload_file_to_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful file upload."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("test content")

            result = upload_file_to_s3(
                mock_s3_client, "test-bucket", "prefix", "test.txt", file_path
            )

            assert result == "prefix/test.txt"
            mock_s3_client.upload_file.assert_called_once()


class TestUploadBytesToS3:
    """Tests for upload_bytes_to_s3 function."""

    def test_upload_bytes_to_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful bytes upload."""
        file_obj = BytesIO(b"test content")

        result = upload_bytes_to_s3(mock_s3_client, "test-bucket", "prefix", "test.txt", file_obj)

        assert result == "prefix/test.txt"
        mock_s3_client.upload_fileobj.assert_called_once()


class TestGetFileFromS3:
    """Tests for get_file_from_s3 function."""

    def test_get_file_from_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful file retrieval."""
        mock_body = MagicMock()
        mock_body.read.return_value = b"test content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = get_file_from_s3(mock_s3_client, "test-bucket", "test-key")

        assert result == "test content"
        mock_s3_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="test-key")

    def test_get_file_from_s3_not_found(self, mock_s3_client: MagicMock) -> None:
        """Test file not found handling."""
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_s3_client.get_object.side_effect = botocore.exceptions.ClientError(
            error_response, "GetObject"
        )

        with pytest.raises(FileNotFoundError, match="File not found in S3"):
            get_file_from_s3(mock_s3_client, "test-bucket", "missing-key")

    def test_get_file_from_s3_other_error(self, mock_s3_client: MagicMock) -> None:
        """Test other AWS errors are re-raised."""
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_s3_client.get_object.side_effect = botocore.exceptions.ClientError(
            error_response, "GetObject"
        )

        with pytest.raises(botocore.exceptions.ClientError):
            get_file_from_s3(mock_s3_client, "test-bucket", "forbidden-key")


class TestGetCsvFromS3:
    """Tests for get_csv_from_s3 function."""

    def test_get_csv_from_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful CSV retrieval."""
        csv_content = "col1,col2\n1,a\n2,b"
        mock_body = MagicMock()
        mock_body.read.return_value = csv_content.encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = get_csv_from_s3(mock_s3_client, "test-bucket", "test.csv")

        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["col1", "col2"]
        assert len(result) == 2

    def test_get_csv_from_s3_invalid_extension(self, mock_s3_client: MagicMock) -> None:
        """Test that non-CSV extension raises ValueError."""
        with pytest.raises(ValueError, match=r"Key must end with \.csv"):
            get_csv_from_s3(mock_s3_client, "test-bucket", "test.txt")


class TestGetJsonFromS3:
    """Tests for get_json_from_s3 function."""

    def test_get_json_from_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful JSON retrieval."""
        json_content = json.dumps({"key": "value", "nested": {"a": 1}})
        mock_body = MagicMock()
        mock_body.read.return_value = json_content.encode("utf-8")
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = get_json_from_s3(mock_s3_client, "test-bucket", "test.json")

        assert result == {"key": "value", "nested": {"a": 1}}

    def test_get_json_from_s3_invalid_extension(self, mock_s3_client: MagicMock) -> None:
        """Test that non-JSON extension raises ValueError."""
        with pytest.raises(ValueError, match=r"Key must end with \.json"):
            get_json_from_s3(mock_s3_client, "test-bucket", "test.txt")


class TestInferCsvFieldsFromS3:
    """Tests for infer_csv_fields_from_s3 function."""

    def test_infer_csv_fields_from_s3_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful field inference."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/file1.csv", "Size": 100},
                {"Key": "prefix/file2.csv", "Size": 200},
            ]
        }
        mock_body = MagicMock()
        mock_body.readline.return_value = b"field1,field2,field3\n"
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = infer_csv_fields_from_s3(mock_s3_client, "test-bucket", "prefix")

        assert result == ["field1", "field2", "field3"]

    def test_infer_csv_fields_from_s3_no_files(self, mock_s3_client: MagicMock) -> None:
        """Test no files found handling."""
        mock_s3_client.list_objects_v2.return_value = {"Contents": []}

        with pytest.raises(FileNotFoundError, match="No files found"):
            infer_csv_fields_from_s3(mock_s3_client, "test-bucket", "empty-prefix")

    def test_infer_csv_fields_from_s3_skips_zero_size(self, mock_s3_client: MagicMock) -> None:
        """Test that zero-size files are skipped."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "prefix/", "Size": 0},
                {"Key": "prefix/real.csv", "Size": 100},
            ]
        }
        mock_body = MagicMock()
        mock_body.readline.return_value = b"field1,field2\n"
        mock_s3_client.get_object.return_value = {"Body": mock_body}

        result = infer_csv_fields_from_s3(mock_s3_client, "test-bucket", "prefix")

        assert result == ["field1", "field2"]
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="prefix/real.csv"
        )


class TestUploadDataframeToParquet:
    """Tests for upload_dataframe_to_s3_parquet function."""

    def test_upload_dataframe_to_parquet_success(self, mock_s3_client: MagicMock) -> None:
        """Test successful Parquet upload."""
        df = pd.DataFrame({"colName": [1, 2], "anotherCol": ["a", "b"]})

        result = upload_dataframe_to_s3_parquet(
            mock_s3_client, df, "test-bucket", "prefix", "test.parquet"
        )

        assert result == "prefix/test.parquet"
        mock_s3_client.upload_file.assert_called_once()

    def test_upload_dataframe_to_parquet_invalid_extension(self, mock_s3_client: MagicMock) -> None:
        """Test that non-Parquet extension raises ValueError."""
        df = pd.DataFrame({"col1": [1, 2]})

        with pytest.raises(ValueError, match=r"File name must end with \.parquet"):
            upload_dataframe_to_s3_parquet(mock_s3_client, df, "test-bucket", "prefix", "test.csv")
