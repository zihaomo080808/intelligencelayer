#!/bin/bash
set -e

# Create and switch to the postgres user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Install pgvector extension
    CREATE EXTENSION IF NOT EXISTS vector;
    
    -- Test that pgvector is working properly
    CREATE TEMPORARY TABLE test_vectors (id int, embedding vector(3));
    INSERT INTO test_vectors VALUES (1, '[1,2,3]');
    SELECT * FROM test_vectors;
    DROP TABLE test_vectors;
EOSQL

echo "pgvector extension installed and tested successfully"