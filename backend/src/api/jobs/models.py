"""Pydantic models for jobs endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from src.postgres.common.enums import JobStatus, JobType


class JobResponse(BaseModel):
    """Response model for a job."""

    id: str = Field(..., description="Job UUID")
    job_type: JobType = Field(..., description="Type of job")
    status: JobStatus = Field(..., description="Job status")
    entity_type: str | None = Field(None, description="Type of related entity")
    entity_id: str | None = Field(None, description="ID of related entity")
    dagster_run_id: str | None = Field(None, description="Dagster run ID")
    error_message: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="When the job was created")
    started_at: datetime | None = Field(None, description="When the job started")
    completed_at: datetime | None = Field(None, description="When the job completed")

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Response model for listing jobs."""

    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs matching filter")
