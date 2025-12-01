"""Module for working with AWS S3."""

import tempfile
from io import StringIO
from pathlib import Path
import json
from typing import TYPE_CHECKING, Dict, Any, List, Optional, Literal, Tuple

import botocore.exceptions
import pandas as pd
from dotenv import load_dotenv
import inflection

import pyarrow.types
from pyarrow import DataType
import pyarrow.dataset
from pyarrow.fs import S3FileSystem, FileSelector


from src.utils.logging import get_logger

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = get_logger("s3")

# read any .env files and load them into the environment
load_dotenv()


def upload_dataframe_to_s3_csv(
    s3_client: "S3Client", df: pd.DataFrame, bucket_name: str, prefix: str, file_name: str
) -> str:
    """Upload a DataFrame to S3 as a CSV file.

    :param s3_client: The S3 client to use for uploading.
    :param df: The DataFrame to upload.
    :param bucket_name: The name of the S3 bucket to upload to.
    :param prefix: The path to the object in the bucket.
    :param file_name: The name of the CSV file to upload. This file must have a .csv extension in the file name .
    :return: The key of the uploaded file in S3.
    """
    logger.info(f"Uploading raw data to S3, path: {file_name}")
    if not file_name.endswith(".csv"):
        logger.error("File name must end with .csv")
        raise ValueError("File name must end with .csv")

    logger.info(f"Preparing to upload file: {file_name}")
    upload_df = df.copy()

    tmp_path = Path(tempfile.gettempdir()) / file_name
    try:
        logger.info(f"Writing DataFrame to temporary file: {tmp_path}")
        upload_df.to_csv(
            tmp_path,
            index=False,
        )
        logger.info(f"Successfully wrote DataFrame to temporary file: {tmp_path}")

        s3_key = upload_file_to_s3(s3_client, bucket_name, prefix, file_name, tmp_path)
    finally:
        # once the file is uploaded, delete the temporary file
        tmp_path.unlink(missing_ok=True)

    return s3_key


def upload_file_to_s3(
    s3_client: "S3Client",
    bucket_name: str,
    prefix: str,
    file_name: str,
    file_path: Path,
) -> str:
    """Upload a file to an Amazon S3 bucket with a specified prefix.

    This function takes a valid S3 client, bucket name, key prefix, file name,
    and file path to upload the specified file to the S3 bucket. It returns the
    full path of the uploaded S3 object as a string.

    :param s3_client: A pre-configured S3 client object to interact with the S3 service.
    :param bucket_name: The name of the S3 bucket where the file will be uploaded.
    :param prefix: The prefix or directory inside the S3 bucket under which the file will be stored.
    :param file_name: The name the file should have in the S3 bucket.
    :param file_path: The path to the file to be uploaded to S3.
    :return: The full path of the uploaded object on S3 as a string.
    """
    s3_key = f"{prefix}/{file_name}"
    logger.info(f"Uploading file to S3: bucket={bucket_name}, key={s3_key}")
    s3_client.upload_file(str(file_path), bucket_name, s3_key)
    logger.info(f"Data uploaded to S3. bucket={bucket_name}, key={s3_key}")
    return s3_key


def get_file_from_s3(s3_client: "S3Client", bucket_name: str, key: str) -> str:
    """Get a file from S3.

    :param s3_client: The boto3 S3 client to use for accessing S3.
    :param bucket_name: The name of the S3 bucket to get the file from.
    :param key: The prefix and file name of the object in S3. Effectively the path to the file.
    :return: The contents of the file as a UTF-8 encoded string.
    """
    logger.info(f"Fetching file from S3: bucket={bucket_name}, key={key}")
    try:
        # Fetch the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=key)

    except botocore.exceptions.ClientError as err:
        # catch the generic aws error and raise a more standard file not found error to match current logic
        if err.response["Error"]["Code"] == "NoSuchKey":
            logger.error(f"File not found in S3: bucket={bucket_name}, key={key}")
            raise FileNotFoundError(f"File not found in S3: bucket={bucket_name}, key={key}")
        # otherwise raise the original error
        raise err

    # read the file contents
    content = response["Body"].read().decode("utf-8")
    logger.info(
        f"Successfully fetched file from S3: bucket={bucket_name}, key={key}, size={len(content)} bytes"
    )
    return content


def get_csv_from_s3(
    s3_client: "S3Client", bucket_name: str, key: str, header: Optional[Literal["infer"]] = "infer"
) -> pd.DataFrame:
    """Get a CSV file from S3 and return it as a Pandas DataFrame.

    :param s3_client: The boto3 S3 client to use for accessing S3.
    :param bucket_name: The name of the S3 bucket to get the file from.
    :param key: The prefix and file name of the object in S3. This must be a CSV file.
    :param header: The header row of the CSV file. Defaults to 'infer' which attempts to infer the header.
    :return: The DataFrame loaded from the CSV file.
    """
    logger.info(f"Fetching CSV from S3: bucket={bucket_name}, key={key}")
    if not key.endswith(".csv"):
        logger.error(f"Invalid file type: key must end with .csv, got {key}")
        raise ValueError("Key must end with .csv")

    raw_data = get_file_from_s3(s3_client, bucket_name, key)
    # read the raw data into a pandas DataFrame
    # don't infer any nan values from the raw data
    df = pd.read_csv(StringIO(raw_data), header=header, na_filter=False)
    logger.info(f"Successfully loaded CSV from S3: shape={df.shape}, columns={list(df.columns)}")
    return df


def get_json_from_s3(s3_client: "S3Client", bucket_name: str, key: str) -> Dict[Any, Any]:
    """Get a JSON file from S3.

    :param s3_client: The boto3 S3 client to use for accessing S3.
    :param bucket_name: The name of the S3 bucket to get the file from.
    :param key: The prefix and file name of the object in S3. This must be a JSON file.
    :return: The JSON object loaded from the file as a Python Dictionary
    """
    logger.info(f"Fetching JSON from S3: bucket={bucket_name}, key={key}")
    if not key.endswith(".json"):
        logger.error(f"Invalid file type: key must end with .json, got {key}")
        raise ValueError("Key must end with .json")

    raw_data = get_file_from_s3(s3_client, bucket_name, key)

    # convert the raw data to a JSON object
    data = json.loads(raw_data)
    logger.info(
        f"Successfully loaded JSON from S3: keys={list(data.keys()) if isinstance(data, dict) else 'non-dict'}"
    )
    return data


def infer_csv_fields_from_s3(s3_client: "S3Client", bucket: str, prefix: str) -> List[str]:
    """Infer fields from a csv file based on a prefix in S3.

    This pulls the first file in the prefix and uses the first line as the header. It excludes any zero size files
    from the listed files in the prefix (AWS sometimes creates zero size hidden files to create folder structures).

    :param s3_client: The boto3 S3 client to use for accessing S3.
    :param bucket: The name of the S3 bucket to search.
    :param prefix: The prefix to search for CSV files.
    :return: A list of field names inferred from the CSV file.
    """
    logger.info(f"Inferring CSV fields from S3: bucket={bucket}, prefix={prefix}")
    # List objects under the prefix
    list_response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)

    # Get the first CSV file key
    file_keys = [
        obj["Key"]
        for obj in list_response.get("Contents", [])
        if not obj["Key"].endswith("/") and obj["Size"] > 0
    ]
    if not file_keys:
        logger.error(f"No files found under prefix: bucket={bucket}, prefix={prefix}")
        raise FileNotFoundError("No files found under that prefix.")

    key = file_keys[0]
    logger.info(f"Using first file to infer fields: key={key}")

    get_response = s3_client.get_object(Bucket=bucket, Key=key)
    first_line = get_response["Body"].readline().decode("utf-8").strip()

    fields = first_line.split(",")
    logger.info(f"Inferred {len(fields)} fields from CSV: {fields}")
    return fields


def upload_dataframe_to_s3_parquet(
    s3_client: "S3Client", df: pd.DataFrame, bucket_name: str, prefix: str, file_name: str
) -> str:
    """Upload a DataFrame to S3.

    :param s3_client: The S3 client to use for uploading.
    :param df: The DataFrame to upload.
    :param bucket_name: The name of the S3 bucket to upload to.
    :param prefix: The path to the object in the bucket.
    :param file_name: The name of the file to upload.
    :return: The key of the uploaded file in S3.
    """
    if not file_name.endswith(".parquet"):
        logger.error("File name must end with .parquet")
        raise ValueError("File name must end with .parquet")

    logger.info(f"Preparing to upload file: {file_name}")
    upload_df = df.copy()

    # Normalise column names and write to temp Parquet
    upload_df.columns = [inflection.underscore(col).upper() for col in upload_df.columns]
    tmp_path = Path(tempfile.gettempdir()) / file_name

    logger.info(f"Writing DataFrame to temporary file: {tmp_path}")
    upload_df.to_parquet(
        tmp_path,
        index=False,
        engine="pyarrow",
    )
    logger.info(f"Successfully wrote DataFrame to temporary file: {tmp_path}")

    s3_key = f"{prefix}/{file_name}"
    logger.info(f"Uploading file to S3: bucket={bucket_name}, key={s3_key}")
    s3_client.upload_file(str(tmp_path), bucket_name, s3_key)
    logger.info(f"Successfully uploaded file to S3: {s3_key}")

    return s3_key


def infer_parquet_schema_from_s3(
    s3_client: "S3Client", bucket: str, prefix: str
) -> List[Tuple[str, str]]:
    """Read the latest Parquet file under `prefix/` in S3, infer column names and types, and map to Snowflake types."""
    logger.info(f"Inferring Parquet schema from S3: bucket={bucket}, prefix={prefix}")

    region = s3_client.meta.region_name
    logger.debug(f"Creating S3FileSystem with region: {region}")
    s3 = S3FileSystem(region=region)

    # retrieve schema based on the latest file in prefix
    file_infos = s3.get_file_info(FileSelector(f"{bucket}/{prefix}"))
    latest_file = max(file_infos, key=lambda fi: fi.mtime).path
    logger.info(f"Retrieved latest file: {latest_file} to infer schema from.")

    logger.debug(f"Creating PyArrow dataset from path: {latest_file}")
    dataset = pyarrow.dataset.dataset(latest_file, filesystem=s3, format="parquet")

    arrow_schema = dataset.schema
    logger.debug(f"Retrieved schema with {len(arrow_schema)} fields")

    # map Arrow types to Snowflake types
    def _arrow_to_snowflake(pa_type: DataType) -> str:
        if pyarrow.types.is_integer(pa_type):
            return "NUMBER"
        if pyarrow.types.is_floating(pa_type):
            return "FLOAT"
        if pyarrow.types.is_boolean(pa_type):
            return "BOOLEAN"
        if pyarrow.types.is_timestamp(pa_type):
            return "TIMESTAMP_LTZ"

        # everything else as a catch-all (strings, binaries, etc.)
        return "STRING"

    # build final schema list
    schema: List[Tuple[str, str]] = []
    for field in arrow_schema:
        # normalise name: camelCase or whatever to UPPER_SNAKE
        col_name = inflection.underscore(field.name).upper()
        sf_type = _arrow_to_snowflake(field.type)
        logger.debug(f"Mapped field '{field.name}' to '{col_name}' with type {sf_type}")
        schema.append((col_name, sf_type))

    logger.info(f"Successfully inferred schema with {len(schema)} columns")
    return schema
