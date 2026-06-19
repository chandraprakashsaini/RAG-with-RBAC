"""create users, roles, chats, and messages

Revision ID: 20260527_0002
Revises: 20260527_0001
Create Date: 2026-05-27 20:05:00
"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260527_0002"
down_revision: Union[str, Sequence[str], None] = "20260527_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    role_ids = {
        "admin": "11111111-1111-1111-1111-111111111111",
        "analyst": "22222222-2222-2222-2222-222222222222",
        "manager": "33333333-3333-3333-3333-333333333333",
        "executive": "44444444-4444-4444-4444-444444444444",
        "viewer": "55555555-5555-5555-5555-555555555555",
    }
    user_ids = {
        "alice": "aaaaaaaa-1111-1111-1111-111111111111",
        "bob": "bbbbbbbb-2222-2222-2222-222222222222",
        "carol": "cccccccc-3333-3333-3333-333333333333",
        "dave": "dddddddd-4444-4444-4444-444444444444",
        "eve": "eeeeeeee-5555-5555-5555-555555555555",
    }

    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role_id", sa.String(length=36), sa.ForeignKey("user_roles.id"), nullable=False
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "chats",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "chat_id",
            sa.String(length=36),
            sa.ForeignKey("chats.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_type", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

    now = datetime.utcnow()

    user_roles_table = sa.table(
        "user_roles",
        sa.column("id", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime()),
    )
    op.bulk_insert(
        user_roles_table,
        [
            {
                "id": role_ids["admin"],
                "name": "admin",
                "description": "Full system access",
                "created_at": now,
            },
            {
                "id": role_ids["analyst"],
                "name": "analyst",
                "description": "Can analyze and query documents",
                "created_at": now,
            },
            {
                "id": role_ids["manager"],
                "name": "manager",
                "description": "Team-level management access",
                "created_at": now,
            },
            {
                "id": role_ids["executive"],
                "name": "executive",
                "description": "Leadership-level access",
                "created_at": now,
            },
            {
                "id": role_ids["viewer"],
                "name": "viewer",
                "description": "Read-only constrained access",
                "created_at": now,
            },
        ],
    )

    users_table = sa.table(
        "users",
        sa.column("id", sa.String()),
        sa.column("email", sa.String()),
        sa.column("full_name", sa.String()),
        sa.column("password_hash", sa.String()),
        sa.column("role_id", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.bulk_insert(
        users_table,
        [
            {
                "id": user_ids["alice"],
                "email": "alice.admin@example.com",
                "full_name": "Alice Admin",
                "password_hash": "dummy_hash_admin_123",
                "role_id": role_ids["admin"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": user_ids["bob"],
                "email": "bob.analyst@example.com",
                "full_name": "Bob Analyst",
                "password_hash": "dummy_hash_analyst_123",
                "role_id": role_ids["analyst"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": user_ids["carol"],
                "email": "carol.manager@example.com",
                "full_name": "Carol Manager",
                "password_hash": "dummy_hash_manager_123",
                "role_id": role_ids["manager"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": user_ids["dave"],
                "email": "dave.executive@example.com",
                "full_name": "Dave Executive",
                "password_hash": "dummy_hash_executive_123",
                "role_id": role_ids["executive"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": user_ids["eve"],
                "email": "eve.viewer@example.com",
                "full_name": "Eve Viewer",
                "password_hash": "dummy_hash_viewer_123",
                "role_id": role_ids["viewer"],
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chats")
    op.drop_table("users")
    op.drop_table("user_roles")

