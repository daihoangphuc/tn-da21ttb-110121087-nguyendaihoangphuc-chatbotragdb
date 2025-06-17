"""
Module to initialize database tables and RLS policies
"""

import os
from .client import SupabaseClient
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def init_db():
    """Initialize database tables and policies"""
    client = SupabaseClient().get_client()

    # Create document_files table if it doesn't exist
    try:
        # Check if table exists
        response = client.table("document_files").select("*").limit(1).execute()
        print("document_files table already exists")
    except Exception as e:
        print(f"Creating document_files table: {str(e)}")
        # Create table using RPC function
        client.rpc(
            "create_document_files_table",
            {
                "sql_query": """
                    CREATE TABLE IF NOT EXISTS document_files (
                        file_id UUID PRIMARY KEY,
                        filename TEXT,
                        file_path TEXT,
                        user_id UUID,
                        file_type TEXT,
                        upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        metadata JSONB,
                        is_deleted BOOLEAN DEFAULT FALSE,
                        deleted_at TIMESTAMP WITH TIME ZONE
                    )
                """
            }
        ).execute()
        print("Created document_files table")

    # Create user_roles table if it doesn't exist
    try:
        # Check if table exists
        response = client.table("user_roles").select("*").limit(1).execute()
        print("user_roles table already exists")
    except Exception as e:
        print(f"Creating user_roles table: {str(e)}")
        # Create table using RPC function
        client.rpc(
            "create_user_roles_table",
            {
                "sql_query": """
                    CREATE TABLE IF NOT EXISTS user_roles (
                        id UUID PRIMARY KEY,
                        user_id UUID NOT NULL,
                        role TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """
            }
        ).execute()
        print("Created user_roles table")

    # Create RLS policies for document_files
    try:
        # Enable RLS on document_files
        client.rpc(
            "enable_rls_on_document_files",
            {"sql_query": "ALTER TABLE document_files ENABLE ROW LEVEL SECURITY;"}
        ).execute()

        # Create policy for selecting files
        client.rpc(
            "create_select_policy",
            {
                "sql_query": """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Users can view all files'
                        ) THEN
                            EXECUTE 'CREATE POLICY "Users can view all files" ON document_files
                            FOR SELECT
                            USING (true)';
                        END IF;
                    END
                    $$;
                """
            }
        ).execute()

        # Create policy for inserting files - only admin can insert
        client.rpc(
            "create_insert_policy",
            {
                "sql_query": """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Only admin can insert files'
                        ) THEN
                            EXECUTE 'CREATE POLICY "Only admin can insert files" ON document_files
                            FOR INSERT
                            USING (
                                EXISTS (
                                    SELECT 1 FROM user_roles
                                    WHERE user_id = auth.uid() AND role = ''admin''
                                )
                            )';
                        END IF;
                    END
                    $$;
                """
            }
        ).execute()

        # Create policy for updating files - only admin can update their own files
        client.rpc(
            "create_update_policy",
            {
                "sql_query": """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Only admin can update their files'
                        ) THEN
                            EXECUTE 'CREATE POLICY "Only admin can update their files" ON document_files
                            FOR UPDATE
                            USING (
                                EXISTS (
                                    SELECT 1 FROM user_roles
                                    WHERE user_id = auth.uid() AND role = ''admin''
                                ) AND user_id = auth.uid()
                            )';
                        END IF;
                    END
                    $$;
                """
            }
        ).execute()

        # Create policy for deleting files - only admin can delete their own files
        client.rpc(
            "create_delete_policy",
            {
                "sql_query": """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_policies WHERE tablename = 'document_files' AND policyname = 'Only admin can delete their files'
                        ) THEN
                            EXECUTE 'CREATE POLICY "Only admin can delete their files" ON document_files
                            FOR DELETE
                            USING (
                                EXISTS (
                                    SELECT 1 FROM user_roles
                                    WHERE user_id = auth.uid() AND role = ''admin''
                                ) AND user_id = auth.uid()
                            )';
                        END IF;
                    END
                    $$;
                """
            }
        ).execute()

        print("RLS policies created for document_files")
    except Exception as e:
        print(f"Error creating RLS policies: {str(e)}")


if __name__ == "__main__":
    init_db() 