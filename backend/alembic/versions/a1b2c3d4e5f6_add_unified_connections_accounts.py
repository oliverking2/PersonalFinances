"""add unified connections and accounts tables

Revision ID: a1b2c3d4e5f6
Revises: 568c7aa09b4d
Create Date: 2026-01-24 14:00:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op  # type: ignore[attr-defined]
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "568c7aa09b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# GoCardless status mapping
GC_STATUS_MAP = {
    "CR": "pending",
    "GA": "pending",
    "SA": "pending",
    "LN": "active",
    "EX": "expired",
    "RJ": "error",
    "UA": "error",
    "SU": "error",
}

GC_ACCOUNT_STATUS_MAP = {
    "READY": "active",
    "EXPIRED": "inactive",
    "SUSPENDED": "inactive",
}

# Known institutions for backfill (will be populated by existing data)
KNOWN_INSTITUTIONS = {
    "BARCLAYS_BUKBGB2L": ("Barclays", "https://cdn.nordigen.com/ais/BARCLAYS_BUKBGB2L.png"),
    "CHASE_CHASGB2L": ("Chase UK", "https://cdn.nordigen.com/ais/CHASE_CHASGB2L.png"),
    "FIRST_DIRECT_MIDLGB2106Z": (
        "First Direct",
        "https://cdn.nordigen.com/ais/FIRST_DIRECT_MIDLGB2106Z.png",
    ),
    "HSBC_BUSINESS_HBUKGB4112A": (
        "HSBC Business",
        "https://cdn.nordigen.com/ais/HSBC_BUSINESS_HBUKGB4112A.png",
    ),
    "HSBC_HBUKGB4B": ("HSBC UK", "https://cdn.nordigen.com/ais/HSBC_HBUKGB4B.png"),
    "LLOYDS_LOYDGB2L": ("Lloyds Bank", "https://cdn.nordigen.com/ais/LLOYDS_LOYDGB2L.png"),
    "MONZO_MONZGB2L": ("Monzo", "https://cdn.nordigen.com/ais/MONZO_MONZGB2L.png"),
    "NATIONWIDE_NAIAGB21": ("Nationwide", "https://cdn.nordigen.com/ais/NATIONWIDE_NAIAGB21.png"),
    "NATWEST_NWBKGB2L": ("NatWest", "https://cdn.nordigen.com/ais/NATWEST_NWBKGB2L.png"),
    "REVOLUT_REVOGB21": ("Revolut", "https://cdn.nordigen.com/ais/REVOLUT_REVOGB21.png"),
    "SANTANDER_ABBYGB2L": ("Santander UK", "https://cdn.nordigen.com/ais/SANTANDER_ABBYGB2L.png"),
    "STARLING_SRLGGB2L": ("Starling Bank", "https://cdn.nordigen.com/ais/STARLING_SRLGGB2L.png"),
}


def upgrade() -> None:
    """Upgrade schema."""
    # Create institutions table
    op.create_table(
        "institutions",
        sa.Column("id", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=512), nullable=True),
        sa.Column("countries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create connections table
    op.create_table(
        "connections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("institution_id", sa.String(length=100), nullable=False),
        sa.Column("friendly_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_connections_user_id", "connections", ["user_id"], unique=False)
    op.create_index(
        "idx_connections_provider_provider_id",
        "connections",
        ["provider", "provider_id"],
        unique=True,
    )

    # Create accounts table
    op.create_table(
        "accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("provider_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("iban", sa.String(length=200), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_accounts_connection_id", "accounts", ["connection_id"], unique=False)
    op.create_index(
        "idx_accounts_connection_provider_id",
        "accounts",
        ["connection_id", "provider_id"],
        unique=True,
    )

    # Run data migration
    _backfill_data()


def _backfill_data() -> None:
    """Backfill data from GoCardless tables to standardised tables."""
    connection = op.get_bind()

    # Get the first user (for single-user backfill)
    result = connection.execute(sa.text("SELECT id FROM users ORDER BY created_at LIMIT 1"))
    row = result.fetchone()
    if row is None:
        # No users yet, nothing to backfill
        return
    first_user_id = row[0]

    # Get all unique institution IDs from requisitions
    result = connection.execute(
        sa.text("SELECT DISTINCT institution_id FROM gc_requisition_links")
    )
    institution_ids = [row[0] for row in result.fetchall()]

    # Seed institutions
    now = sa.func.now()
    for inst_id in institution_ids:
        if inst_id in KNOWN_INSTITUTIONS:
            name, logo_url = KNOWN_INSTITUTIONS[inst_id]
        else:
            # Unknown institution - use ID as name
            name = inst_id
            logo_url = None

        connection.execute(
            sa.text(
                """
                INSERT INTO institutions (id, provider, name, logo_url, countries, created_at, updated_at)
                VALUES (:id, 'gocardless', :name, :logo_url, '["GB"]'::jsonb, NOW(), NOW())
                """
            ),
            {"id": inst_id, "name": name, "logo_url": logo_url},
        )

    # Backfill connections from gc_requisition_links
    result = connection.execute(
        sa.text(
            """
            SELECT id, institution_id, status, friendly_name, created, agreement
            FROM gc_requisition_links
            """
        )
    )
    requisitions = result.fetchall()

    # Map requisition ID to new connection UUID
    req_to_conn_id: dict[str, str] = {}

    for req in requisitions:
        req_id, institution_id, gc_status, friendly_name, created, agreement_id = req
        status = GC_STATUS_MAP.get(gc_status, "error")
        conn_id = str(uuid4())
        req_to_conn_id[req_id] = conn_id

        # Calculate expires_at from agreement (if available)
        # For now, set to None - can be enhanced later
        connection.execute(
            sa.text(
                """
                INSERT INTO connections
                (id, user_id, provider, provider_id, institution_id, friendly_name, status, created_at, synced_at)
                VALUES (:id, :user_id, 'gocardless', :provider_id, :institution_id, :friendly_name, :status, :created_at, NOW())
                """
            ),
            {
                "id": conn_id,
                "user_id": str(first_user_id),
                "provider_id": req_id,
                "institution_id": institution_id,
                "friendly_name": friendly_name,
                "status": status,
                "created_at": created,
            },
        )

    # Backfill accounts from gc_bank_accounts
    result = connection.execute(
        sa.text(
            """
            SELECT id, requisition_id, display_name, name, iban, currency, status
            FROM gc_bank_accounts
            WHERE requisition_id IS NOT NULL
            """
        )
    )
    accounts = result.fetchall()

    for acc in accounts:
        acc_id, req_id, display_name, name, iban, currency, gc_status = acc
        if req_id not in req_to_conn_id:
            continue

        conn_id = req_to_conn_id[req_id]
        status = GC_ACCOUNT_STATUS_MAP.get(gc_status, "inactive") if gc_status else "inactive"

        connection.execute(
            sa.text(
                """
                INSERT INTO accounts
                (id, connection_id, provider_id, display_name, name, iban, currency, status, synced_at)
                VALUES (:id, :connection_id, :provider_id, :display_name, :name, :iban, :currency, :status, NOW())
                """
            ),
            {
                "id": str(uuid4()),
                "connection_id": conn_id,
                "provider_id": acc_id,
                "display_name": display_name,
                "name": name,
                "iban": iban,
                "currency": currency,
                "status": status,
            },
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_accounts_connection_provider_id", table_name="accounts")
    op.drop_index("idx_accounts_connection_id", table_name="accounts")
    op.drop_table("accounts")
    op.drop_index("idx_connections_provider_provider_id", table_name="connections")
    op.drop_index("idx_connections_user_id", table_name="connections")
    op.drop_table("connections")
    op.drop_table("institutions")
