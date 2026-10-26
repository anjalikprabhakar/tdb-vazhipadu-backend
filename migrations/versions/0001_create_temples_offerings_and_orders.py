from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "temples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "offerings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("temple_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["temple_id"],
            ["temples.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("temple_id", "name"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("temple_id", sa.Integer(), nullable=False),
        sa.Column("devotee_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=False),
        sa.Column(
            "nakshatra",
            sa.Enum(
                "ASHWINI",
                "BHARANI",
                "KRITTIKA",
                "ROHINI",
                "MRIGASHIRA",
                "ARDRA",
                "PUNARVASU",
                "PUSHYA",
                "ASHLESHA",
                "MAGHA",
                "PURVA_PHALGUNI",
                "UTTARA_PHALGUNI",
                "HASTA",
                "CHITRA",
                "SWATI",
                "VISHAKHA",
                "ANURADHA",
                "JYESHTHA",
                "MULA",
                "PURVA_ASHADHA",
                "UTTARA_ASHADHA",
                "SHRAVANA",
                "DHANISHTA",
                "SHATABHISHA",
                "PURVA_BHADRAPADA",
                "UTTARA_BHADRAPADA",
                "REVATI",
                name="nakshatra",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("CONFIRMED", name="orderstatus", native_enum=False, length=20),
            nullable=False,
        ),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["temple_id"],
            ["temples.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("offering_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["offerings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "offering_id"),
    )


def downgrade() -> None:
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("offerings")
    op.drop_table("temples")
