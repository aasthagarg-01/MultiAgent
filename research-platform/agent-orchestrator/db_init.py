# agent-orchestrator/db_init.py
"""
Database initialization script for setting up pgvector and documents table.
Run this once to set up the vector search database schema.

Usage:
    python db_init.py
"""

import os
import logging
import psycopg2
from psycopg2 import sql, OperationalError
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with pgvector extension and documents table."""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connect to database
        logger.info("Connecting to database...")
        conn = psycopg2.connect(database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Enable pgvector extension
        logger.info("Creating pgvector extension...")
        try:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("pgvector extension created/verified")
        except Exception as e:
            logger.warning(f"Could not create pgvector extension: {str(e)}")
            logger.warning("Make sure pgvector is installed in PostgreSQL")
        
        # Create documents table
        logger.info("Creating documents table...")
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            source VARCHAR(512) NOT NULL,
            embedding vector(384),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cur.execute(create_table_sql)
        logger.info("Documents table created/verified")
        
        # Create index on embedding column for fast similarity search
        logger.info("Creating vector index on embedding column...")
        try:
            cur.execute("""
            CREATE INDEX IF NOT EXISTS documents_embedding_idx 
            ON documents USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """)
            logger.info("Vector index created/verified")
        except Exception as e:
            logger.warning(f"Could not create vector index: {str(e)}")
            logger.warning("Vector search may be slower without index")
        
        # Create index on source column for quick lookups
        logger.info("Creating index on source column...")
        try:
            cur.execute("""
            CREATE INDEX IF NOT EXISTS documents_source_idx 
            ON documents (source)
            """)
            logger.info("Source index created/verified")
        except Exception as e:
            logger.warning(f"Could not create source index: {str(e)}")
        
        # Verify table structure
        logger.info("Verifying table structure...")
        cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'documents'
        ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        
        if columns:
            logger.info("Documents table structure:")
            for col_name, col_type in columns:
                logger.info(f"  - {col_name}: {col_type}")
        
        cur.close()
        conn.close()
        
        logger.info("Database initialization completed successfully!")
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection failed: {str(e)}")
        logger.error("Make sure PostgreSQL is running and DATABASE_URL is correct")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {str(e)}")
        return False

def insert_sample_documents():
    """Insert sample documents for testing vector search."""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        from sentence_transformers import SentenceTransformer
        
        logger.info("Loading sentence transformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Sample documents for testing
        sample_docs = [
            {
                "content": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience.",
                "source": "AI_Introduction"
            },
            {
                "content": "Python is a high-level programming language known for its simplicity and readability.",
                "source": "Programming_Languages"
            },
            {
                "content": "PostgreSQL is a powerful, open-source relational database system.",
                "source": "Databases"
            },
            {
                "content": "Docker containerization allows applications to run consistently across different environments.",
                "source": "DevOps"
            },
            {
                "content": "Vector databases enable semantic search by storing and querying embeddings.",
                "source": "Database_Technologies"
            }
        ]
        
        # Connect and insert
        logger.info("Connecting to database for sample insertion...")
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        logger.info("Inserting sample documents...")
        for doc in sample_docs:
            # Generate embedding
            embedding = model.encode(doc['content']).tolist()
            
            # Insert into database
            cur.execute(
                """
                INSERT INTO documents (content, source, embedding)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (doc['content'], doc['source'], embedding)
            )
        
        conn.commit()
        logger.info(f"Inserted {len(sample_docs)} sample documents")
        
        # Verify insertion
        cur.execute("SELECT COUNT(*) FROM documents")
        count = cur.fetchone()[0]
        logger.info(f"Total documents in database: {count}")
        
        cur.close()
        conn.close()
        return True
        
    except ImportError:
        logger.warning("sentence-transformers not installed. Skipping sample document insertion.")
        logger.warning("Install with: pip install sentence-transformers")
        return False
    except Exception as e:
        logger.error(f"Error inserting sample documents: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    
    if init_database():
        logger.info("Database schema ready!")
        
        # Try to insert sample documents
        if insert_sample_documents():
            logger.info("Sample documents loaded!")
        else:
            logger.info("Skipped sample documents (optional)")
    else:
        logger.error("Database initialization failed!")
        exit(1)
