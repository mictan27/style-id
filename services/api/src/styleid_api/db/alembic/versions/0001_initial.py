"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-19 03:44:15.353501
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column(
            "typical_ease",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("seeded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("apple_sub", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("dob_verified_18", sa.Boolean(), nullable=False),
        sa.Column(
            "preferences",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("apple_sub"),
    )
    op.create_table(
        "body_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("mesh_blob_key", sa.String(length=512), nullable=True),
        sa.Column(
            "measurements",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "landmarks",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("body_records", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_body_records_user_id"), ["user_id"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("brand_id", sa.String(length=36), nullable=True),
        sa.Column("url_canonical", sa.Text(), nullable=False),
        sa.Column("url_original", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("fabric_composition", sa.Text(), nullable=True),
        sa.Column("stretch_class", sa.String(length=32), nullable=True),
        sa.Column("cut", sa.String(length=32), nullable=True),
        sa.Column("garment_kind", sa.String(length=32), nullable=False),
        sa.Column("chart_id", sa.String(length=36), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url_canonical"),
    )
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_products_brand_id"), ["brand_id"], unique=False)

    op.create_table(
        "garments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("size_label", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("cut", sa.String(length=32), nullable=False),
        sa.Column("stretch_class", sa.String(length=32), nullable=False),
        sa.Column("fit_tag", sa.String(length=16), nullable=True),
        sa.Column("length_from_center_back", sa.Boolean(), nullable=False),
        sa.Column("sleeve_from_center_back", sa.Boolean(), nullable=False),
        sa.Column(
            "measurements",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("is_reference", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "size_label", name="uq_garments_product_size"),
    )
    with op.batch_alter_table("garments", schema=None) as batch_op:
        batch_op.create_index(
            "ix_garments_owner_reference", ["owner_user_id", "is_reference"], unique=False
        )

    op.create_table(
        "size_charts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=True),
        sa.Column("brand_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "classification",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "extraction_json",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "normalised",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("model_id", sa.String(length=128), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("size_charts", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_size_charts_product_id"), ["product_id"], unique=False)

    # products <-> size_charts is a cycle; this side is added once both tables exist.
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_products_chart_id_size_charts",
            "size_charts",
            ["chart_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "fit_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("body_record_id", sa.String(length=36), nullable=True),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("reference_garment_id", sa.String(length=36), nullable=True),
        sa.Column(
            "result",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["body_record_id"], ["body_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reference_garment_id"], ["garments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("fit_reports", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fit_reports_product_id"), ["product_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_fit_reports_user_id"), ["user_id"], unique=False)

    op.create_table(
        "landmark_corrections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("garment_id", sa.String(length=36), nullable=False),
        sa.Column("image_blob_key", sa.String(length=512), nullable=False),
        sa.Column(
            "proposed",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "corrected",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("scale_cm_per_px", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["garment_id"], ["garments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("landmark_corrections", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_landmark_corrections_garment_id"), ["garment_id"], unique=False
        )

    op.create_table(
        "purchase_outcomes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("fit_report_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("size_bought", sa.String(length=32), nullable=False),
        sa.Column("kept", sa.Boolean(), nullable=False),
        sa.Column("problem_zone", sa.String(length=16), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fit_report_id"], ["fit_reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("purchase_outcomes", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_purchase_outcomes_fit_report_id"), ["fit_report_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_purchase_outcomes_user_id"), ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_constraint("fk_products_chart_id_size_charts", type_="foreignkey")

    with op.batch_alter_table("purchase_outcomes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_purchase_outcomes_user_id"))
        batch_op.drop_index(batch_op.f("ix_purchase_outcomes_fit_report_id"))

    op.drop_table("purchase_outcomes")
    with op.batch_alter_table("landmark_corrections", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_landmark_corrections_garment_id"))

    op.drop_table("landmark_corrections")
    with op.batch_alter_table("fit_reports", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fit_reports_user_id"))
        batch_op.drop_index(batch_op.f("ix_fit_reports_product_id"))

    op.drop_table("fit_reports")
    with op.batch_alter_table("size_charts", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_size_charts_product_id"))

    op.drop_table("size_charts")
    with op.batch_alter_table("garments", schema=None) as batch_op:
        batch_op.drop_index("ix_garments_owner_reference")

    op.drop_table("garments")
    with op.batch_alter_table("products", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_products_brand_id"))

    op.drop_table("products")
    with op.batch_alter_table("body_records", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_body_records_user_id"))

    op.drop_table("body_records")
    op.drop_table("users")
    op.drop_table("brands")
