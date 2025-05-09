"""
Supabase Conversation Manager for handling conversation history with Supabase.
Replaces the traditional conversation_memory.py functionality.
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any
from .client import SupabaseClient
from .database import SupabaseDatabase


class SupabaseConversationManager:
    """Manager for conversation history using Supabase database"""

    def __init__(self, client=None):
        """Initialize the conversation manager with Supabase client"""
        if client:
            self.supabase_client = client
        else:
            self.supabase_client = SupabaseClient().get_client()

        # Initialize database access
        self.db = SupabaseDatabase(self.supabase_client)

        # Ensure the conversation history table exists
        try:
            self.db.create_conversation_history_table()
        except Exception as e:
            print(f"Warning: Could not create conversation history table: {str(e)}")
            print("Conversation history might not be properly stored in the database.")

    def add_user_message(
        self, session_id: str, message: str, user_id: Optional[str] = None
    ) -> None:
        """
        Add a user message to the conversation history

        Args:
            session_id: Unique identifier for the conversation
            message: Content of the user's message
            user_id: Optional user identifier for authenticated users
        """
        try:
            self.db.save_conversation_message(
                session_id=session_id, role="user", content=message, user_id=user_id
            )
        except Exception as e:
            print(f"Warning: Failed to save user message to database: {str(e)}")
            # Fallback to local file storage
            self._save_locally(session_id, "user", message, user_id)

    def add_ai_message(
        self,
        session_id: str,
        message: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """
        Add an AI message to the conversation history

        Args:
            session_id: Unique identifier for the conversation
            message: Content of the AI's message
            metadata: Optional metadata about the message (sources, etc.)
            user_id: Optional user identifier for authenticated users
        """
        try:
            self.db.save_conversation_message(
                session_id=session_id,
                role="assistant",
                content=message,
                user_id=user_id,
                metadata=metadata,
            )
        except Exception as e:
            print(f"Warning: Failed to save AI message to database: {str(e)}")
            # Fallback to local file storage
            self._save_locally(session_id, "assistant", message, user_id, metadata)

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict]:
        """
        Get conversation messages from the history

        Args:
            session_id: Unique identifier for the conversation
            limit: Maximum number of messages to retrieve

        Returns:
            List of message objects with keys 'role' and 'content'
        """
        try:
            history = self.db.get_conversation_history(session_id, limit)
            # Format messages in the expected structure
            formatted_messages = []
            for msg in history:
                formatted_message = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                }
                # Add metadata if available
                if msg.get("metadata"):
                    formatted_message["metadata"] = msg.get("metadata")
                formatted_messages.append(formatted_message)
            return formatted_messages
        except Exception as e:
            print(f"Warning: Failed to retrieve messages from database: {str(e)}")
            # Fallback to local file storage
            return self._get_locally(session_id)

    def clear_memory(self, session_id: str) -> bool:
        """
        Clear conversation history for a specific session

        Args:
            session_id: Unique identifier for the conversation

        Returns:
            Success status
        """
        try:
            self.db.clear_conversation_history(session_id)
            # Also clear local backup if it exists
            local_path = self._get_local_path(session_id)
            if os.path.exists(local_path):
                os.remove(local_path)
            return True
        except Exception as e:
            print(f"Warning: Failed to clear conversation history: {str(e)}")
            return False

    def format_for_prompt(self, session_id: str) -> str:
        """
        Format conversation history for prompt context

        Args:
            session_id: Unique identifier for the conversation

        Returns:
            Formatted conversation history string
        """
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        formatted_history = "LỊCH SỬ CUỘC HỘI THOẠI:\n"
        for message in messages:
            role = message.get("role")
            content = message.get("content")
            if role == "user":
                formatted_history += f"Người dùng: {content}\n"
            elif role == "assistant":
                formatted_history += f"Trợ lý: {content}\n"

        return formatted_history

    # Fallback local methods for offline or error situations

    def _get_local_path(self, session_id: str) -> str:
        """Generate local file path for conversation session"""
        history_dir = os.path.join("src", "conversation_history")
        os.makedirs(history_dir, exist_ok=True)
        return os.path.join(history_dir, f"{session_id}.json")

    def _save_locally(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Save message to local file as fallback"""
        file_path = self._get_local_path(session_id)

        # Read existing history if it exists
        history_data = {
            "session_id": session_id,
            "last_updated": datetime.datetime.now().isoformat(),
            "messages": [],
        }

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
            except Exception:
                # If file is corrupted, start with a fresh history
                pass

        # Add new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Add optional fields if provided
        if user_id:
            message["user_id"] = user_id

        if metadata:
            message["metadata"] = metadata

        history_data["messages"].append(message)
        history_data["last_updated"] = datetime.datetime.now().isoformat()

        # Save updated history
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)

    def _get_locally(self, session_id: str) -> List[Dict]:
        """Get messages from local file as fallback"""
        file_path = self._get_local_path(session_id)

        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                history_data = json.load(f)

            # Extract and format messages
            messages = []
            for msg in history_data.get("messages", []):
                formatted_message = {
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                }

                # Add metadata if available
                if "metadata" in msg:
                    formatted_message["metadata"] = msg.get("metadata")

                messages.append(formatted_message)

            return messages
        except Exception as e:
            print(f"Warning: Failed to read local conversation history: {str(e)}")
            return []
