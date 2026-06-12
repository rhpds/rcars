"""Add infrastructure metadata to catalog items (AgnosticD v2 only).

Revision ID: 002
Revises: 001
Create Date: 2026-06-12
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE catalog_items
            ADD COLUMN IF NOT EXISTS is_agd_v2 BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS agd_config TEXT,
            ADD COLUMN IF NOT EXISTS cloud_provider TEXT,
            ADD COLUMN IF NOT EXISTS ocp_version TEXT,
            ADD COLUMN IF NOT EXISTS os_image TEXT,
            ADD COLUMN IF NOT EXISTS worker_instance_count TEXT,
            ADD COLUMN IF NOT EXISTS control_plane_instance_count TEXT,
            ADD COLUMN IF NOT EXISTS instances_json JSONB;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog_item_workloads (
            id SERIAL PRIMARY KEY,
            ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            workload_fqcn TEXT NOT NULL,
            workload_role TEXT NOT NULL,
            workload_collection TEXT,
            UNIQUE(ci_name, workload_fqcn)
        );
        CREATE INDEX IF NOT EXISTS idx_ciw_ci_name ON catalog_item_workloads(ci_name);
        CREATE INDEX IF NOT EXISTS idx_ciw_workload_role ON catalog_item_workloads(workload_role);
        CREATE INDEX IF NOT EXISTS idx_ciw_workload_collection ON catalog_item_workloads(workload_collection);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS workload_mapping (
            id SERIAL PRIMARY KEY,
            workload_role TEXT NOT NULL UNIQUE,
            product_name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            source_collection TEXT,
            verified BOOLEAN DEFAULT FALSE,
            added_by TEXT,
            added_at TIMESTAMPTZ DEFAULT NOW(),
            verified_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_wm_product_name ON workload_mapping(product_name);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS workload_aliases (
            id SERIAL PRIMARY KEY,
            product_name TEXT NOT NULL,
            alias TEXT NOT NULL UNIQUE,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_wa_product_name ON workload_aliases(product_name);
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog_item_acl_groups (
            id SERIAL PRIMARY KEY,
            ci_name TEXT NOT NULL REFERENCES catalog_items(ci_name) ON DELETE CASCADE,
            group_name TEXT NOT NULL,
            UNIQUE(ci_name, group_name)
        );
        CREATE INDEX IF NOT EXISTS idx_ciag_ci_name ON catalog_item_acl_groups(ci_name);
        CREATE INDEX IF NOT EXISTS idx_ciag_group_name ON catalog_item_acl_groups(group_name);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catalog_item_acl_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS workload_aliases CASCADE")
    op.execute("DROP TABLE IF EXISTS workload_mapping CASCADE")
    op.execute("DROP TABLE IF EXISTS catalog_item_workloads CASCADE")
    op.execute("""
        ALTER TABLE catalog_items
            DROP COLUMN IF EXISTS is_agd_v2,
            DROP COLUMN IF EXISTS agd_config,
            DROP COLUMN IF EXISTS cloud_provider,
            DROP COLUMN IF EXISTS ocp_version,
            DROP COLUMN IF EXISTS os_image,
            DROP COLUMN IF EXISTS worker_instance_count,
            DROP COLUMN IF EXISTS control_plane_instance_count,
            DROP COLUMN IF EXISTS instances_json;
    """)
