"""let the immutability triggers of generated documents pass a DELETE inside the process purge

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # GP-D3: only the process deletion sets app.process_purge (SET LOCAL, so it ends with the
    # transaction). UPDATE stays blocked, and so does DELETE anywhere else.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION generated_documents_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF current_setting('app.process_purge', true) = 'on' THEN
                    RETURN OLD;
                END IF;
                RAISE EXCEPTION 'generated_documents cannot be deleted';
            END IF;
            IF OLD.state <> 'GERANDO' THEN
                RAISE EXCEPTION 'generated_documents is immutable once it left GERANDO';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION generated_files_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF current_setting('app.process_purge', true) = 'on' THEN
                    RETURN OLD;
                END IF;
                RAISE EXCEPTION 'generated_files cannot be deleted';
            END IF;
            RAISE EXCEPTION 'generated_files is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION generated_documents_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'generated_documents cannot be deleted';
            END IF;
            IF OLD.state <> 'GERANDO' THEN
                RAISE EXCEPTION 'generated_documents is immutable once it left GERANDO';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION generated_files_immutable() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'generated_files cannot be deleted';
            END IF;
            RAISE EXCEPTION 'generated_files is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
