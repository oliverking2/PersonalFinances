"""Module for working with AWS SSM Parameters."""

from typing import TYPE_CHECKING

from src.utils.logging import setup_dagster_logger

if TYPE_CHECKING:
    from mypy_boto3_ssm import SSMClient


logger = setup_dagster_logger("aws_ssm_parameters")


def get_parameter_data_from_ssm(ssm_client: "SSMClient", parameter_name: str) -> str:
    """Retrieve the parameter data from AWS Parameter Store. Returns None if not found.

    :param ssm_client: boto3 ssm client
    :param parameter_name: name of the parameter to retrieve
    :return: parameter value if found, None otherwise
    """
    # Attempt to fetch the value from Parameter Store
    logger.info(f"Attempting to retrieve parameter data from: {parameter_name}")
    try:
        parameter_response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
        parameter_data = parameter_response["Parameter"]["Value"]
        logger.info("Retrieved parameter data")
        return parameter_data

    except ssm_client.exceptions.ParameterNotFound:
        logger.error(f"Parameter {parameter_name} not found")
        raise

    except Exception as e:
        logger.error(f"Error retrieving parameter data: {e!s}", exc_info=True)
        raise
