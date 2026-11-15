from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE search_runs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        project_id uuid NOT NULL REFERENCES projects(id), user_id uuid NOT NULL REFERENCES users(id),
        query text NOT NULL, configuration jsonb NOT NULL, context jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE answers (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        search_id uuid NOT NULL UNIQUE REFERENCES search_runs(id),
        provider text NOT NULL, model text NOT NULL, parameters jsonb NOT NULL,
        output jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE citations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), answer_id uuid NOT NULL REFERENCES answers(id),
        chunk_id uuid NOT NULL REFERENCES chunks(id), quote text NOT NULL,
        start_at integer NOT NULL, end_at integer NOT NULL, UNIQUE(answer_id,chunk_id)
    );
    CREATE TABLE reviews (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), answer_id uuid NOT NULL REFERENCES answers(id),
        user_id uuid NOT NULL REFERENCES users(id), revision integer NOT NULL,
        decision text NOT NULL CHECK (decision IN ('IN_REVIEW','VERIFIED','REJECTED','NEEDS_MORE_EVIDENCE')),
        rationale text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(answer_id,revision)
    );
    CREATE TABLE reports (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
        author_id uuid NOT NULL REFERENCES users(id), answer_id uuid NOT NULL REFERENCES answers(id),
        title text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE TABLE snapshots (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), report_id uuid NOT NULL REFERENCES reports(id),
        revision integer NOT NULL, body jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(report_id,revision)
    );
    CREATE TABLE evaluation_runs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
        user_id uuid NOT NULL REFERENCES users(id), configuration jsonb NOT NULL, results jsonb NOT NULL,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE INDEX search_history ON search_runs(project_id,created_at DESC);
    CREATE INDEX report_history ON reports(project_id,created_at DESC);
    CREATE INDEX evaluation_history ON evaluation_runs(project_id,created_at DESC);
    DO $$
    DECLARE relation text;
    BEGIN
      FOREACH relation IN ARRAY ARRAY['search_runs','answers','citations','reviews','reports','snapshots','evaluation_runs']
      LOOP
        EXECUTE format('CREATE TRIGGER immutable_%I BEFORE UPDATE OR DELETE ON %I
                        FOR EACH ROW EXECUTE FUNCTION reject_changes()', relation, relation);
      END LOOP;
    END $$;
    """)


def downgrade():
    op.execute(
        "DROP TABLE evaluation_runs,snapshots,reports,reviews,citations,answers,search_runs"
    )
