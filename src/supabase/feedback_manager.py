"""
Supabase Feedback Manager for handling user feedback with Supabase.
Replaces the traditional feedback storage in filesystem.
"""

import os
import json
import datetime
from typing import Dict, List, Optional, Any
from .client import SupabaseClient
from .database import SupabaseDatabase


class SupabaseFeedbackManager:
    """Manager for user feedback using Supabase database"""

    def __init__(self, client=None):
        """Initialize the feedback manager with Supabase client"""
        if client:
            self.supabase_client = client
        else:
            self.supabase_client = SupabaseClient().get_client()

        # Initialize database access
        self.db = SupabaseDatabase(self.supabase_client)

        # Ensure the feedback table exists
        try:
            self.db.create_feedback_table()
        except Exception as e:
            print(f"Warning: Could not create feedback table: {str(e)}")
            print("User feedback might not be properly stored in the database.")

        # Directory for local fallback storage
        self.feedback_dir = os.path.join("src", "feedback")
        os.makedirs(self.feedback_dir, exist_ok=True)

    def save_feedback(
        self,
        question_id: str,
        rating: int,
        is_helpful: bool,
        comment: Optional[str] = None,
        specific_feedback: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """
        Save user feedback

        Args:
            question_id: Unique identifier for the question
            rating: Numerical rating (1-5)
            is_helpful: Whether the answer was helpful
            comment: Optional comment text
            specific_feedback: Optional structured feedback data
            user_id: Optional user identifier for authenticated users

        Returns:
            Success status
        """
        try:
            # Try to save to Supabase database
            self.db.save_feedback(
                question_id=question_id,
                rating=rating,
                is_helpful=is_helpful,
                comment=comment,
                specific_feedback=specific_feedback,
                user_id=user_id,
            )
            return True
        except Exception as e:
            print(f"Warning: Failed to save feedback to database: {str(e)}")
            # Fall back to local storage
            return self._save_locally(
                question_id=question_id,
                rating=rating,
                is_helpful=is_helpful,
                comment=comment,
                specific_feedback=specific_feedback,
                user_id=user_id,
            )

    def get_feedback_stats(self) -> Dict:
        """
        Get aggregated feedback statistics

        Returns:
            Dictionary with feedback statistics
        """
        try:
            # Try to get stats from Supabase
            return self.db.get_feedback_stats()
        except Exception as e:
            print(f"Warning: Failed to get feedback stats from database: {str(e)}")
            # Fall back to local calculation
            return self._calculate_local_stats()

    def get_feedback_by_question(self, question_id: str) -> List[Dict]:
        """
        Get all feedback for a specific question

        Args:
            question_id: Unique identifier for the question

        Returns:
            List of feedback records
        """
        try:
            # Query Supabase for feedback
            table = self.db.from_table("user_feedback")
            response = table.select("*").eq("question_id", question_id).execute()
            return response.data
        except Exception as e:
            print(f"Warning: Failed to get feedback from database: {str(e)}")
            # Fall back to local storage
            return self._get_feedback_locally(question_id)

    def get_all_feedback(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Get all feedback with pagination

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of feedback records
        """
        try:
            # Query Supabase for all feedback
            table = self.db.from_table("user_feedback")
            response = (
                table.select("*")
                .order("timestamp", ascending=False)
                .range(offset, offset + limit - 1)
                .execute()
            )
            return response.data
        except Exception as e:
            print(f"Warning: Failed to get all feedback from database: {str(e)}")
            # Fall back to local storage
            return self._get_all_feedback_locally(limit, offset)

    # Local storage fallback methods

    def _save_locally(
        self,
        question_id: str,
        rating: int,
        is_helpful: bool,
        comment: Optional[str] = None,
        specific_feedback: Optional[Dict] = None,
        user_id: Optional[str] = None,
    ) -> bool:
        """Save feedback to local filesystem as fallback"""
        try:
            # Create a feedback object
            timestamp = datetime.datetime.now().isoformat()
            filename = f"{question_id}_{timestamp.replace(':', '_')}.json"
            filepath = os.path.join(self.feedback_dir, filename)

            feedback = {
                "question_id": question_id,
                "rating": rating,
                "is_helpful": is_helpful,
                "timestamp": timestamp,
            }

            # Add optional fields if provided
            if comment:
                feedback["comment"] = comment

            if specific_feedback:
                feedback["specific_feedback"] = specific_feedback

            if user_id:
                feedback["user_id"] = user_id

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(feedback, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"Error saving feedback locally: {str(e)}")
            return False

    def _get_feedback_locally(self, question_id: str) -> List[Dict]:
        """Get feedback for a question from local filesystem"""
        try:
            result = []

            # Iterate through all feedback files
            for filename in os.listdir(self.feedback_dir):
                if not filename.endswith(".json"):
                    continue

                filepath = os.path.join(self.feedback_dir, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        feedback = json.load(f)

                    # Check if this feedback matches the question ID
                    if feedback.get("question_id") == question_id:
                        result.append(feedback)
                except Exception:
                    # Skip corrupted files
                    continue

            # Sort by timestamp (newest first)
            result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return result
        except Exception as e:
            print(f"Error getting feedback locally: {str(e)}")
            return []

    def _get_all_feedback_locally(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict]:
        """Get all feedback with pagination from local filesystem"""
        try:
            all_feedback = []

            # Iterate through all feedback files
            for filename in os.listdir(self.feedback_dir):
                if not filename.endswith(".json"):
                    continue

                filepath = os.path.join(self.feedback_dir, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        feedback = json.load(f)

                    all_feedback.append(feedback)
                except Exception:
                    # Skip corrupted files
                    continue

            # Sort by timestamp (newest first)
            all_feedback.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Apply pagination
            return all_feedback[offset : offset + limit]
        except Exception as e:
            print(f"Error getting all feedback locally: {str(e)}")
            return []

    def _calculate_local_stats(self) -> Dict:
        """Calculate feedback statistics from local files"""
        try:
            total_feedback = 0
            total_rating = 0
            helpful_count = 0
            not_helpful_count = 0

            # Iterate through all feedback files
            for filename in os.listdir(self.feedback_dir):
                if not filename.endswith(".json"):
                    continue

                filepath = os.path.join(self.feedback_dir, filename)

                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        feedback = json.load(f)

                    total_feedback += 1
                    total_rating += feedback.get("rating", 0)

                    if feedback.get("is_helpful", False):
                        helpful_count += 1
                    else:
                        not_helpful_count += 1
                except Exception:
                    # Skip corrupted files
                    continue

            # Calculate average rating
            average_rating = total_rating / total_feedback if total_feedback > 0 else 0

            return {
                "total_feedback": total_feedback,
                "average_rating": average_rating,
                "helpful_count": helpful_count,
                "not_helpful_count": not_helpful_count,
            }
        except Exception as e:
            print(f"Error calculating feedback stats locally: {str(e)}")
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "helpful_count": 0,
                "not_helpful_count": 0,
            }
