"""
Supabase Realtime module for real-time updates and notifications.
"""

from typing import Dict, List, Optional, Callable, Any
from .client import SupabaseClient


class SupabaseRealtime:
    """Class for managing real-time updates with Supabase"""

    def __init__(self, client=None):
        """Initialize the realtime module with a Supabase client"""
        if client:
            self.client = client
        else:
            self.client = SupabaseClient().get_client()

        # Store active channels
        self.channels = {}

    def subscribe_to_changes(
        self,
        table_name: str,
        schema: str = "public",
        event: str = "*",
        callback: Callable[[Dict], None] = None,
        filter_string: Optional[str] = None,
    ) -> str:
        """
        Subscribe to Postgres changes on a table.

        Args:
            table_name: Name of the table to subscribe to
            schema: Database schema the table belongs to (default: "public")
            event: Event type to listen for ("INSERT", "UPDATE", "DELETE", or "*" for all)
            callback: Function to call when changes occur
            filter_string: Optional filter for the changes

        Returns:
            Channel ID
        """
        # Generate a unique channel ID
        channel_id = f"{schema}:{table_name}:{event}"
        if filter_string:
            channel_id += f":{filter_string}"

        # Create a new channel if it doesn't exist
        if channel_id not in self.channels:
            # Create the channel
            channel = self.client.channel(channel_id)

            # Define postgres changes handler
            def handle_postgres_changes(payload):
                if callback:
                    callback(payload)
                else:
                    print(f"Received change in {table_name}: {payload}")

            # Set up postgres changes subscription
            channel_config = {"event": event, "schema": schema, "table": table_name}
            if filter_string:
                channel_config["filter"] = filter_string

            channel.on("postgres_changes", channel_config, handle_postgres_changes)

            # Subscribe to the channel
            channel.subscribe()

            # Store the channel
            self.channels[channel_id] = channel

        return channel_id

    def unsubscribe(self, channel_id: str) -> bool:
        """
        Unsubscribe from a specific channel

        Args:
            channel_id: Channel ID returned from subscribe_to_changes

        Returns:
            Success status
        """
        if channel_id in self.channels:
            channel = self.channels[channel_id]
            channel.unsubscribe()
            del self.channels[channel_id]
            return True
        return False

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all channels"""
        for channel_id in list(self.channels.keys()):
            self.unsubscribe(channel_id)

    def get_channels(self) -> List[str]:
        """Get a list of all active channel IDs"""
        return list(self.channels.keys())

    def broadcast(
        self,
        channel_name: str,
        event: str,
        payload: Dict,
        broadcast_to_all: bool = False,
    ) -> Dict:
        """
        Broadcast a message to a channel

        Args:
            channel_name: Name of the channel
            event: Event name
            payload: Message payload
            broadcast_to_all: Whether to broadcast to all subscribers including sender

        Returns:
            Response from Supabase
        """
        channel = self.client.channel(channel_name)
        return channel.send(
            {
                "type": "broadcast",
                "event": event,
                "payload": payload,
                "broadcast_to_all": broadcast_to_all,
            }
        )

    def presence_track(self, channel_name: str, presence_data: Dict) -> Dict:
        """
        Track presence for a user on a channel

        Args:
            channel_name: Name of the channel
            presence_data: User presence data

        Returns:
            Response from Supabase
        """
        channel = self.client.channel(channel_name)
        return channel.track(presence_data)

    def presence_untrack(self, channel_name: str) -> Dict:
        """
        Untrack presence for a user on a channel

        Args:
            channel_name: Name of the channel

        Returns:
            Response from Supabase
        """
        channel = self.client.channel(channel_name)
        return channel.untrack()
