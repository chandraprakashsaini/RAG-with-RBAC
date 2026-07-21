"""add database indexes on foreign keys and hot query paths

Revision ID: 20260720_0001
Revises: 20260620_0001
Create Date: 2026-07-20 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260720_0001"
down_revision: Union[str, Sequence[str], None] = "20260620_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_users_role_id", "users", ["role_id"])
    op.create_index("ix_chats_user_id", "chats", ["user_id"])
    op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"])
    op.create_index(
        "ix_chat_messages_chat_id_created_at", "chat_messages", ["chat_id", "created_at"]
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_document_id", "documents", ["document_id"])

    # document_permissions table may not exist on DBs that haven't applied
    # a migration creating it; create its indexes only if the table exists.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "document_permissions" in inspector.get_table_names():
        op.create_index(
            "ix_document_permissions_document_id", "document_permissions", ["document_id"]
        )
        op.create_index(
            "ix_document_permissions_role_id", "document_permissions", ["role_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "document_permissions" in inspector.get_table_names():
        op.drop_index("ix_document_permissions_role_id", table_name="document_permissions")
        op.drop_index(
            "ix_document_permissions_document_id", table_name="document_permissions"
        )
    op.drop_index("ix_documents_document_id", table_name="documents")
    op.drop_index("ix_documents_user_id", table_name="documents")
    op.drop_index("ix_chat_messages_chat_id_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_index("ix_chats_user_id", table_name="chats")
    op.drop_index("ix_users_role_id", table_name="users")
