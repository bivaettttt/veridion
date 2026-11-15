from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE lab_runs (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
            user_id uuid NOT NULL REFERENCES users(id), results jsonb NOT NULL,
            created_at timestamptz DEFAULT clock_timestamp() NOT NULL
        );
        CREATE INDEX lab_history ON lab_runs(project_id,created_at DESC);
        CREATE TRIGGER immutable_lab BEFORE UPDATE OR DELETE ON lab_runs
            FOR EACH ROW EXECUTE FUNCTION reject_changes();
    """)


def downgrade():
    op.execute("DROP TABLE lab_runs")
