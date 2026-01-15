"""
WebSocket endpoints for real-time updates.
Provides live event streaming to connected clients.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasting.
    
    Handles multiple concurrent connections, heartbeats,
    and message broadcasting to all connected clients.
    """

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
        self.connection_info: Dict[WebSocket, Dict] = {}
        logger.info("ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, client_id: str = None) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Optional client identifier
        """
        await websocket.accept()
        self.active_connections.append(websocket)

        # Store connection metadata
        self.connection_info[websocket] = {
            "client_id": client_id or f"client_{len(self.active_connections)}",
            "connected_at": datetime.utcnow(),
            "messages_sent": 0,
        }

        logger.info(
            "WebSocket connection established",
            extra={
                "client_id": self.connection_info[websocket]["client_id"],
                "total_connections": len(self.active_connections),
            },
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket to disconnect
        """
        if websocket in self.active_connections:
            client_info = self.connection_info.get(websocket, {})
            client_id = client_info.get("client_id", "unknown")

            self.active_connections.remove(websocket)
            if websocket in self.connection_info:
                del self.connection_info[websocket]

            logger.info(
                "WebSocket connection closed",
                extra={
                    "client_id": client_id,
                    "total_connections": len(self.active_connections),
                    "messages_sent": client_info.get("messages_sent", 0),
                },
            )

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> None:
        """
        Send message to a specific client.

        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
                if websocket in self.connection_info:
                    self.connection_info[websocket]["messages_sent"] += 1
        except Exception as e:
            logger.warning(
                f"Failed to send personal message: {e}",
                extra={"client": self.connection_info.get(websocket, {}).get("client_id")},
            )

    async def broadcast(self, message: dict, exclude: Set[WebSocket] = None) -> int:
        """
        Broadcast message to all connected clients.

        Args:
            message: Message dictionary to broadcast
            exclude: Set of WebSocket connections to exclude

        Returns:
            Number of clients that received the message
        """
        exclude = exclude or set()
        sent_count = 0
        failed_connections = []

        for connection in self.active_connections:
            if connection in exclude:
                continue

            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_json(message)
                    if connection in self.connection_info:
                        self.connection_info[connection]["messages_sent"] += 1
                    sent_count += 1
                else:
                    failed_connections.append(connection)
            except Exception as e:
                logger.warning(
                    f"Failed to broadcast to client: {e}",
                    extra={
                        "client": self.connection_info.get(connection, {}).get("client_id")
                    },
                )
                failed_connections.append(connection)

        # Clean up failed connections
        for connection in failed_connections:
            self.disconnect(connection)

        if sent_count > 0:
            logger.debug(
                f"Broadcast message sent to {sent_count} clients",
                extra={"message_type": message.get("type"), "recipients": sent_count},
            )

        return sent_count

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)

    def get_connection_stats(self) -> Dict:
        """
        Get statistics about connections.

        Returns:
            Dictionary with connection statistics
        """
        total_messages = sum(
            info.get("messages_sent", 0) for info in self.connection_info.values()
        )

        return {
            "active_connections": len(self.active_connections),
            "total_messages_sent": total_messages,
            "clients": [
                {
                    "client_id": info.get("client_id"),
                    "connected_at": info.get("connected_at").isoformat()
                    if info.get("connected_at")
                    else None,
                    "messages_sent": info.get("messages_sent", 0),
                }
                for info in self.connection_info.values()
            ],
        }


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/live-updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for live repository updates.

    Clients connect to this endpoint to receive real-time notifications about:
    - New GitHub events (commits, PRs, issues, releases)
    - Repository ranking changes
    - Summary updates
    - Trend changes

    Protocol:
    1. Client connects
    2. Server sends welcome message
    3. Server broadcasts updates as they occur
    4. Server sends periodic heartbeat pings
    5. Client can disconnect anytime

    Example client (JavaScript):
        const ws = new WebSocket('ws://localhost:8000/ws/live-updates');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Update:', data);
        };
    """
    client_id = f"client_{id(websocket)}"

    await manager.connect(websocket, client_id)

    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "message": "Connected to live updates",
                "timestamp": datetime.utcnow().isoformat(),
            },
            websocket,
        )

        # Start heartbeat task
        heartbeat_task = asyncio.create_task(_heartbeat_loop(websocket))

        # Listen for client messages (if any)
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()

                # Parse and handle client message
                try:
                    message = json.loads(data)
                    await _handle_client_message(websocket, message)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from client: {data}")

            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected normally")
                break
            except Exception as e:
                logger.error(f"Error in WebSocket loop: {e}", exc_info=True)
                break

    finally:
        # Cleanup
        heartbeat_task.cancel()
        manager.disconnect(websocket)


async def _heartbeat_loop(websocket: WebSocket) -> None:
    """
    Send periodic heartbeat messages to keep connection alive.

    Args:
        websocket: WebSocket connection
    """
    try:
        while True:
            await asyncio.sleep(30)  # Send ping every 30 seconds

            if websocket.client_state == WebSocketState.CONNECTED:
                await manager.send_personal_message(
                    {
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    websocket,
                )
            else:
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Heartbeat error: {e}", exc_info=True)


async def _handle_client_message(websocket: WebSocket, message: dict) -> None:
    """
    Handle messages from client.

    Args:
        websocket: Client WebSocket connection
        message: Parsed message dictionary
    """
    message_type = message.get("type")

    if message_type == "ping":
        # Respond to client ping
        await manager.send_personal_message(
            {"type": "pong", "timestamp": datetime.utcnow().isoformat()}, websocket
        )

    elif message_type == "subscribe":
        # Handle subscription requests (future feature)
        topics = message.get("topics", [])
        logger.info(f"Client subscription request: {topics}")
        await manager.send_personal_message(
            {
                "type": "subscription",
                "status": "acknowledged",
                "topics": topics,
                "timestamp": datetime.utcnow().isoformat(),
            },
            websocket,
        )

    else:
        logger.debug(f"Unknown message type from client: {message_type}")


@router.get("/ws-stats")
async def get_websocket_stats() -> Dict:
    """
    Get WebSocket connection statistics.

    Returns:
        Statistics about active WebSocket connections
    """
    return manager.get_connection_stats()


# Function to be called by pipeline when data changes
async def broadcast_update(message: dict) -> int:
    """
    Broadcast an update to all connected WebSocket clients.

    This function is called by the pipeline or change detector
    when new data is available.

    Args:
        message: Update message to broadcast

    Returns:
        Number of clients that received the message
    """
    return await manager.broadcast(message)

# Export for use in other modules
__all__ = ["router", "manager", "broadcast_update"]