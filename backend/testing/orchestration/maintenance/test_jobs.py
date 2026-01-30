"""Tests for maintenance Dagster jobs.

These tests verify the maintenance job definitions are correctly configured.
The underlying delete_old_notifications operation is tested in its own test file.
"""

from src.orchestration.maintenance.jobs import (
    cleanup_old_notifications_op,
    maintenance_cleanup_job,
    maintenance_cleanup_schedule,
)


class TestMaintenanceJobs:
    """Test maintenance job configuration."""

    def test_cleanup_job_name(self) -> None:
        """Test that the cleanup job has the correct name."""
        assert maintenance_cleanup_job.name == "maintenance_cleanup_job"

    def test_cleanup_job_has_description(self) -> None:
        """Test that the cleanup job has a description."""
        assert maintenance_cleanup_job.description is not None
        assert "maintenance" in maintenance_cleanup_job.description.lower()

    def test_cleanup_op_requires_postgres(self) -> None:
        """Test that the cleanup op requires postgres_database resource."""
        assert "postgres_database" in cleanup_old_notifications_op.required_resource_keys

    def test_cleanup_op_name(self) -> None:
        """Test that the cleanup op has the correct name."""
        assert cleanup_old_notifications_op.name == "cleanup_old_notifications"

    def test_schedule_cron_is_daily(self) -> None:
        """Test that the schedule runs daily at 4am."""
        assert maintenance_cleanup_schedule.cron_schedule == "0 4 * * *"

    def test_schedule_uses_london_timezone(self) -> None:
        """Test that the schedule uses Europe/London timezone."""
        assert maintenance_cleanup_schedule.execution_timezone == "Europe/London"

    def test_schedule_targets_cleanup_job(self) -> None:
        """Test that the schedule targets the cleanup job."""
        assert maintenance_cleanup_schedule.job_name == "maintenance_cleanup_job"
