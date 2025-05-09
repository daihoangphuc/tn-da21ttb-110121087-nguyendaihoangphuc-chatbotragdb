"""
Supabase Auth module for user authentication and management.
"""

from typing import Dict, Optional, Any, List
from .client import SupabaseClient


class SupabaseAuth:
    """Class for managing user authentication with Supabase"""

    def __init__(self, client=None):
        """Initialize the auth module with a Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

        # Access the auth API
        self.auth = self.client.auth

    def sign_up(
        self, email: str, password: str, metadata: Optional[Dict] = None
    ) -> Dict:
        """Register a new user with email and password"""
        return self.auth.sign_up(
            {"email": email, "password": password, "options": {"data": metadata or {}}}
        )

    def sign_in(self, email: str, password: str) -> Dict:
        """Sign in a user with email and password"""
        return self.auth.sign_in_with_password({"email": email, "password": password})

    def sign_out(self) -> Dict:
        """Sign out the current user"""
        return self.auth.sign_out()

    def get_user(self) -> Optional[Dict]:
        """Get the current user's information"""
        return self.auth.get_user()

    def get_session(self) -> Optional[Dict]:
        """Get the current session"""
        return self.auth.get_session()

    def update_user(self, attributes: Dict) -> Dict:
        """Update the current user's attributes"""
        return self.auth.update_user(attributes)

    def refresh_session(self) -> Dict:
        """Refresh the current session"""
        return self.auth.refresh_session()

    def sign_in_with_oauth(self, provider: str, options: Optional[Dict] = None) -> Dict:
        """Sign in using a third-party provider"""
        return self.auth.sign_in_with_oauth({"provider": provider, **(options or {})})

    def sign_in_with_otp(self, email: str, options: Optional[Dict] = None) -> Dict:
        """Sign in with a one-time password sent to email"""
        return self.auth.sign_in_with_otp({"email": email, "options": options or {}})

    def verify_otp(self, email: str, token: str, type: str = "email") -> Dict:
        """Verify a one-time password"""
        return self.auth.verify_otp({"email": email, "token": token, "type": type})

    def reset_password_for_email(
        self, email: str, options: Optional[Dict] = None
    ) -> None:
        """Send a password reset request to the user's email"""
        return self.auth.reset_password_for_email(email, options or {})

    # Admin methods (require service role key)
    def create_admin_user(
        self, email: str, password: str, metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a new admin user (requires admin permissions)"""
        admin_auth = self.auth.admin
        return admin_auth.create_user(
            {
                "email": email,
                "password": password,
                "email_confirm": True,
                "user_metadata": metadata or {},
            }
        )

    def list_users(self) -> List[Dict]:
        """List all users (requires admin permissions)"""
        admin_auth = self.auth.admin
        return admin_auth.list_users()

    def delete_user(self, user_id: str) -> Dict:
        """Delete a user by ID (requires admin permissions)"""
        admin_auth = self.auth.admin
        return admin_auth.delete_user(user_id)

    def generate_link(self, email: str, link_type: str = "signup") -> Dict:
        """Generate a signup or magic link"""
        admin_auth = self.auth.admin
        return admin_auth.generate_link({"email": email, "type": link_type})
