from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.create_index(
            "ix_orders_temple_booking_date_id", ["temple_id", "booking_date", "id"], unique=False
        )
        batch_op.create_index("ix_orders_temple_id_id", ["temple_id", "id"], unique=False)
        batch_op.create_index(
            "ix_orders_temple_phone_id", ["temple_id", "phone", "id"], unique=False
        )
        batch_op.create_index(
            "ix_orders_temple_status_id", ["temple_id", "status", "id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("orders", schema=None) as batch_op:
        batch_op.drop_index("ix_orders_temple_status_id")
        batch_op.drop_index("ix_orders_temple_phone_id")
        batch_op.drop_index("ix_orders_temple_id_id")
        batch_op.drop_index("ix_orders_temple_booking_date_id")
