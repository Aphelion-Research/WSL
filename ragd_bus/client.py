"""WebSocket client for RAGD /bus endpoint."""
import asyncio
import json
import websockets
from typing import Optional, Callable
from datetime import datetime


class RAGDBusClient:
    """WebSocket client for RAGD event bus."""

    def __init__(self, url: str = "ws://127.0.0.1:7474/bus"):
        """Initialize bus client.

        Args:
            url: WebSocket URL
        """
        self.url = url
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.reconnect_delay = 1.0  # Start at 1s
        self.max_reconnect_delay = 30.0
        self.heartbeat_interval = 30.0

    async def connect(self) -> bool:
        """Connect to bus.

        Returns:
            True if connected
        """
        try:
            self.ws = await websockets.connect(self.url, ping_interval=20)
            self.running = True
            self.reconnect_delay = 1.0  # Reset backoff
            print(f"Connected to {self.url}")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from bus."""
        self.running = False
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def send(self, topic: str, payload: dict) -> bool:
        """Send message to bus.

        Args:
            topic: Message topic
            payload: Message payload

        Returns:
            True if sent successfully
        """
        if not self.ws or not self.running:
            print("Not connected")
            return False

        message = {
            "topic": topic,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }

        try:
            await self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"Send failed: {e}")
            self.running = False
            return False

    async def receive(self) -> Optional[dict]:
        """Receive message from bus.

        Returns:
            Message dict or None
        """
        if not self.ws or not self.running:
            return None

        try:
            msg = await self.ws.recv()
            return json.loads(msg)
        except Exception as e:
            print(f"Receive failed: {e}")
            self.running = False
            return None

    async def run_with_reconnect(self, handler: Callable[[dict], None]):
        """Run client with automatic reconnection.

        Args:
            handler: Callback for received messages
        """
        while True:
            if not self.running:
                if await self.connect():
                    pass
                else:
                    await asyncio.sleep(self.reconnect_delay)
                    self.reconnect_delay = min(
                        self.reconnect_delay * 2,
                        self.max_reconnect_delay
                    )
                    continue

            try:
                msg = await self.receive()
                if msg:
                    handler(msg)
            except Exception as e:
                print(f"Error in receive loop: {e}")
                await asyncio.sleep(1)


# Sync wrapper for simple usage
class RAGDBusSync:
    """Synchronous wrapper for bus client."""

    def __init__(self, url: str = "ws://127.0.0.1:7474/bus"):
        self.url = url

    def send(self, topic: str, payload: dict) -> bool:
        """Send message synchronously."""
        async def _send():
            client = RAGDBusClient(self.url)
            if await client.connect():
                result = await client.send(topic, payload)
                await client.disconnect()
                return result
            return False

        return asyncio.run(_send())

    def test_connectivity(self) -> bool:
        """Test if bus is reachable."""
        async def _test():
            client = RAGDBusClient(self.url)
            connected = await client.connect()
            if connected:
                await client.disconnect()
            return connected

        try:
            return asyncio.run(_test())
        except Exception as e:
            print(f"Connectivity test failed: {e}")
            return False
