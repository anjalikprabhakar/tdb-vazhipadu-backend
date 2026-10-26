from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "offering_daily_usage",
        sa.Column("offering_id", sa.Integer(), nullable=False),
        sa.Column("booking_date", sa.Date(), nullable=False),
        sa.Column("booked", sa.Integer(), nullable=False),
        sa.CheckConstraint("booked >= 0", name="ck_offering_daily_usage_booked"),
        sa.ForeignKeyConstraint(
            ["offering_id"],
            ["offerings.id"],
        ),
        sa.PrimaryKeyConstraint("offering_id", "booking_date"),
    )
    with op.batch_alter_table("offerings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("daily_limit", sa.Integer(), nullable=True))
        batch_op.create_check_constraint("ck_offerings_daily_limit_positive", "daily_limit > 0")

    op.execute(
        """
        INSERT INTO offering_daily_usage (offering_id, booking_date, booked)
        SELECT order_items.offering_id, orders.booking_date, SUM(order_items.quantity)
        FROM order_items JOIN orders ON orders.id = order_items.order_id
        WHERE orders.status != 'CANCELLED'
        GROUP BY order_items.offering_id, orders.booking_date
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("offerings", schema=None) as batch_op:
        batch_op.drop_constraint("ck_offerings_daily_limit_positive", type_="check")
        batch_op.drop_column("daily_limit")

    op.drop_table("offering_daily_usage")
