from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Harmony")
app.mount("/static", StaticFiles(directory="static"), name="static")


@dataclass
class ClientConnection:
    client_id: str
    username: str
    websocket: WebSocket


class RoomHub:
    def __init__(self) -> None:
        self.rooms: Dict[str, Dict[str, ClientConnection]] = {}

    async def connect(self, room: str, username: str, websocket: WebSocket) -> tuple[ClientConnection, list[dict]]:
        await websocket.accept()
        client = ClientConnection(client_id=uuid4().hex[:12], username=username, websocket=websocket)
        room_clients = self.rooms.setdefault(room, {})
        peers = [{"id": peer.client_id, "username": peer.username} for peer in room_clients.values()]
        room_clients[client.client_id] = client
        return client, peers

    def disconnect(self, room: str, client_id: str) -> None:
        room_clients = self.rooms.get(room)
        if not room_clients:
            return

        room_clients.pop(client_id, None)
        if not room_clients:
            self.rooms.pop(room, None)

    async def send_to(self, room: str, client_id: str, payload: dict) -> None:
        room_clients = self.rooms.get(room, {})
        target = room_clients.get(client_id)
        if not target:
            return
        await target.websocket.send_json(payload)

    async def broadcast(self, room: str, payload: dict, exclude: str | None = None) -> None:
        room_clients = self.rooms.get(room, {})
        for client in list(room_clients.values()):
            if client.client_id == exclude:
                continue
            await client.websocket.send_json(payload)


hub = RoomHub()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/")
async def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    username = websocket.query_params.get("username", "anon").strip()[:32] or "anon"
    room = websocket.query_params.get("room", "general").strip()[:32] or "general"

    client, peers = await hub.connect(room, username, websocket)
    await websocket.send_json({"type": "welcome", "self_id": client.client_id, "room": room, "peers": peers})

    await hub.broadcast(
        room,
        {
            "type": "system",
            "room": room,
            "username": "harmony",
            "message": f"{username} joined #{room}",
            "timestamp": utc_now(),
        },
    )
    await hub.broadcast(
        room,
        {"type": "user_joined", "id": client.client_id, "username": username},
        exclude=client.client_id,
    )

    try:
        while True:
            data = await websocket.receive_json()
            event_type = str(data.get("type", "chat"))

            if event_type == "chat":
                content = str(data.get("message", "")).strip()
                if not content:
                    continue
                await hub.broadcast(
                    room,
                    {
                        "type": "chat",
                        "room": room,
                        "username": username,
                        "message": content[:500],
                        "timestamp": utc_now(),
                    },
                )
                continue

            if event_type == "signal":
                target_id = str(data.get("to", "")).strip()
                if not target_id:
                    continue
                await hub.send_to(
                    room,
                    target_id,
                    {
                        "type": "signal",
                        "from": client.client_id,
                        "from_username": username,
                        "data": data.get("data", {}),
                    },
                )
    except WebSocketDisconnect:
        hub.disconnect(room, client.client_id)
        await hub.broadcast(
            room,
            {
                "type": "system",
                "room": room,
                "username": "harmony",
                "message": f"{username} left #{room}",
                "timestamp": utc_now(),
            },
        )
        await hub.broadcast(room, {"type": "user_left", "id": client.client_id})
