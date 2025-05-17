-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- Test that pgvector is working
DO $$ 
BEGIN
    -- Check if vector extension is installed
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        -- Try vector operations to confirm extension is working
        EXECUTE 'CREATE TEMPORARY TABLE test_vectors (id int, embedding vector(3));';
        EXECUTE 'INSERT INTO test_vectors VALUES (1, ''[1,2,3]'');';
        EXECUTE 'SELECT * FROM test_vectors;';
        EXECUTE 'DROP TABLE test_vectors;';
        RAISE NOTICE 'Vector extension test successful';
    ELSE
        RAISE EXCEPTION 'Vector extension not installed properly';
    END IF;
END $$;

-- Create tables (these will be created by SQLAlchemy ORM, but we can add extensions here)

-- Add pgvector index after SQLAlchemy creates tables (needs table to exist first)
CREATE OR REPLACE FUNCTION create_vector_indexes() RETURNS void AS $$
BEGIN
    -- Check if profiles exists and has embedding column
    IF EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'profiles'
    ) AND EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'profiles' AND column_name = 'embedding'
    ) THEN
        -- Create vector index on profiles.embedding if not exists
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes WHERE indexname = 'profiles_embedding_idx'
        ) THEN
            -- Check if vector extension is available
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            ) THEN
                -- Use ivfflat index type instead of vector access method
                EXECUTE 'CREATE INDEX profiles_embedding_idx ON profiles USING ivfflat (embedding vector_l2_ops)';
            END IF;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Call the function to create indexes
SELECT create_vector_indexes();

-- Create a trigger to automatically create/update indexes when tables are created
CREATE OR REPLACE FUNCTION create_vector_indexes_trigger() RETURNS event_trigger AS $$
BEGIN
    -- Wait a bit to ensure tables are fully created
    PERFORM pg_sleep(1);
    -- Create the vector indexes
    PERFORM create_vector_indexes();
END;
$$ LANGUAGE plpgsql;

-- Register the event trigger
DROP EVENT TRIGGER IF EXISTS vector_indexes_trigger;
CREATE EVENT TRIGGER vector_indexes_trigger ON ddl_command_end
WHEN TAG IN ('CREATE TABLE', 'ALTER TABLE')
EXECUTE FUNCTION create_vector_indexes_trigger();
