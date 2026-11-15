from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE EXTENSION vector;
    CREATE TABLE users (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        email text UNIQUE NOT NULL,
        name text NOT NULL,
        password text NOT NULL,
        is_admin boolean NOT NULL DEFAULT false
    );
    CREATE TABLE sessions (
        digest text PRIMARY KEY, user_id uuid NOT NULL REFERENCES users(id),
        expires_at timestamptz NOT NULL DEFAULT now() + interval '12 hours'
    );
    CREATE TABLE projects (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL,
        description text NOT NULL DEFAULT '', lab boolean NOT NULL DEFAULT false,
        owner_id uuid NOT NULL REFERENCES users(id), created_at timestamptz NOT NULL DEFAULT now()
    );
    CREATE TABLE members (
        project_id uuid NOT NULL REFERENCES projects(id), user_id uuid NOT NULL REFERENCES users(id),
        role text NOT NULL CHECK (role IN ('RESEARCHER','ANALYST','REVIEWER','ADMIN')),
        PRIMARY KEY (project_id,user_id)
    );
    CREATE TABLE sources (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), project_id uuid NOT NULL REFERENCES projects(id),
        title text NOT NULL, category text NOT NULL,
        archived_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(project_id,title)
    );
    CREATE TABLE source_versions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id uuid NOT NULL REFERENCES sources(id),
        version integer NOT NULL CHECK(version > 0), filename text NOT NULL, media_type text NOT NULL,
        content_hash text NOT NULL CHECK (length(content_hash)=64), original bytea NOT NULL,
        normalized text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        UNIQUE(source_id,version), UNIQUE(source_id,content_hash)
    );
    CREATE TABLE sections (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), version_id uuid NOT NULL REFERENCES source_versions(id),
        heading text NOT NULL, page integer, start_at integer NOT NULL CHECK (start_at >= 0),
        end_at integer NOT NULL CHECK (end_at > start_at)
    );
    CREATE TABLE chunks (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), section_id uuid NOT NULL REFERENCES sections(id),
        version_id uuid NOT NULL REFERENCES source_versions(id),
        start_at integer NOT NULL CHECK (start_at >= 0), end_at integer NOT NULL CHECK (end_at > start_at),
        content text NOT NULL, search tsvector GENERATED ALWAYS AS (
            to_tsvector('simple', content) || to_tsvector('russian', content) || to_tsvector('english', content)
        ) STORED, UNIQUE(version_id,start_at,end_at), CHECK (char_length(content)=end_at-start_at)
    );
    CREATE INDEX chunk_fts ON chunks USING gin(search);
    CREATE INDEX source_projects ON sources(project_id);
    CREATE TABLE embeddings (
        chunk_id uuid NOT NULL REFERENCES chunks(id), model text NOT NULL, value vector(384) NOT NULL,
        PRIMARY KEY(chunk_id,model)
    );
    CREATE TABLE jobs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_id uuid NOT NULL REFERENCES sources(id),
        filename text NOT NULL, payload bytea, digest text NOT NULL,
        state text NOT NULL DEFAULT 'QUEUED' CHECK (state IN ('QUEUED','DONE','FAILED')),
        version_id uuid REFERENCES source_versions(id), error text,
        created_at timestamptz NOT NULL DEFAULT clock_timestamp(), finished_at timestamptz
    );
    CREATE UNIQUE INDEX import_once ON jobs(source_id,digest) WHERE state <> 'FAILED';
    CREATE INDEX pending_imports ON jobs(created_at) WHERE state='QUEUED';
    CREATE TABLE audit (
        id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, project_id uuid NOT NULL REFERENCES projects(id),
        user_id uuid REFERENCES users(id), action text NOT NULL, object_id uuid,
        request_id text NOT NULL, created_at timestamptz NOT NULL DEFAULT clock_timestamp()
    );
    CREATE FUNCTION reject_changes() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
        RAISE EXCEPTION 'immutable record: %', TG_TABLE_NAME;
        RETURN NULL;
    END;
    $$;
    CREATE TRIGGER immutable_version BEFORE UPDATE OR DELETE ON source_versions
        FOR EACH ROW EXECUTE FUNCTION reject_changes();
    CREATE TRIGGER immutable_section BEFORE UPDATE OR DELETE ON sections
        FOR EACH ROW EXECUTE FUNCTION reject_changes();
    CREATE TRIGGER immutable_chunk BEFORE UPDATE OR DELETE ON chunks
        FOR EACH ROW EXECUTE FUNCTION reject_changes();
    CREATE TRIGGER immutable_embeddings BEFORE UPDATE OR DELETE ON embeddings
        FOR EACH ROW EXECUTE FUNCTION reject_changes();
    CREATE TRIGGER immutable_audit BEFORE UPDATE OR DELETE ON audit
        FOR EACH ROW EXECUTE FUNCTION reject_changes();
    """)


def downgrade():
    op.execute("""
    DROP TABLE audit,jobs,embeddings,chunks,sections,source_versions,sources,members,projects,sessions,users;
    DROP FUNCTION reject_changes();
    DROP EXTENSION vector;
    """)
