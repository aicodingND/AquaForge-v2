"""
WebSocket-based Real-Time Collaboration System

Enables multiple coaches to collaborate on lineups simultaneously.
"""

import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Active connections per session
active_connections: dict[str, set[WebSocket]] = {}


class CollaborationManager:
    """Manages WebSocket connections and broadcasts updates"""

    def __init__(self):
        self.active_sessions: dict[str, set[WebSocket]] = {}
        self.session_state: dict[str, dict] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Connect a client to a collaboration session"""
        await websocket.accept()

        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = set()
            self.session_state[session_id] = {
                "lineup": {},
                "participants": [],
                "last_update": datetime.now().isoformat(),
            }

        self.active_sessions[session_id].add(websocket)

        # Send current state to new participant
        await websocket.send_json(
            {"type": "state", "data": self.session_state[session_id]}
        )

        # Notify others
        await self.broadcast(
            session_id,
            {
                "type": "participant_joined",
                "count": len(self.active_sessions[session_id]),
            },
            exclude=websocket,
        )

        logger.info(f"Client connected to session {session_id}")

    def disconnect(self, session_id: str, websocket: WebSocket):
        """Disconnect a client from a session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id].discard(websocket)

            if not self.active_sessions[session_id]:
                # Clean up empty sessions
                del self.active_sessions[session_id]
                del self.session_state[session_id]

            logger.info(f"Client disconnected from session {session_id}")

    async def broadcast(
        self, session_id: str, message: dict, exclude: WebSocket | None = None
    ):
        """Broadcast message to all clients in a session"""
        if session_id not in self.active_sessions:
            return

        dead_connections: set[WebSocket] = set()

        for connection in self.active_sessions[session_id]:
            if connection == exclude:
                continue

            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(session_id, conn)

    async def update_lineup(
        self, session_id: str, event: str, swimmer: str, websocket: WebSocket
    ):
        """Update lineup and broadcast to all participants"""
        if session_id in self.session_state:
            # Update state
            if "lineup" not in self.session_state[session_id]:
                self.session_state[session_id]["lineup"] = {}

            self.session_state[session_id]["lineup"][event] = swimmer
            self.session_state[session_id]["last_update"] = datetime.now().isoformat()

            # Broadcast update
            await self.broadcast(
                session_id,
                {
                    "type": "lineup_update",
                    "event": event,
                    "swimmer": swimmer,
                    "timestamp": datetime.now().isoformat(),
                },
                exclude=websocket,
            )


manager = CollaborationManager()


@router.websocket("/ws/collaborate/{session_id}")
async def websocket_collaboration(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time collaboration.

    Usage:
        const ws = new WebSocket('ws://localhost:8001/api/v1/ws/collaborate/meet_123');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            // Handle updates
        };
        ws.send(JSON.stringify({
            type: 'lineup_update',
            event: '100 Free',
            swimmer: 'John Smith'
        }));
    """
    await manager.connect(session_id, websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "lineup_update":
                await manager.update_lineup(
                    session_id, data.get("event"), data.get("swimmer"), websocket
                )

            elif message_type == "cursor_move":
                # Broadcast cursor position for collaborative editing UI
                await manager.broadcast(
                    session_id,
                    {
                        "type": "cursor_move",
                        "user": data.get("user"),
                        "x": data.get("x"),
                        "y": data.get("y"),
                    },
                    exclude=websocket,
                )

            elif message_type == "comment":
                # Broadcast comment
                await manager.broadcast(
                    session_id,
                    {
                        "type": "comment",
                        "user": data.get("user"),
                        "text": data.get("text"),
                        "timestamp": datetime.now().isoformat(),
                    },
                )

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

        # Notify remaining participants
        if session_id in manager.active_sessions:
            await manager.broadcast(
                session_id,
                {
                    "type": "participant_left",
                    "count": len(manager.active_sessions[session_id]),
                },
            )


@router.get("/sessions/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current state of a collaboration session"""
    if session_id in manager.session_state:
        return {
            "session_id": session_id,
            "state": manager.session_state[session_id],
            "active_participants": len(manager.active_sessions.get(session_id, set())),
        }
    return {"error": "Session not found"}, 404
