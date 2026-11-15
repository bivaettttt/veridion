from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE answer_keys (
            project_id uuid NOT NULL REFERENCES projects(id), user_id uuid NOT NULL REFERENCES users(id),
            key text NOT NULL, fingerprint text NOT NULL, answer_id uuid REFERENCES answers(id),
            PRIMARY KEY(project_id,user_id,key)
        );
    """)


def downgrade():
    op.execute("DROP TABLE answer_keys")
