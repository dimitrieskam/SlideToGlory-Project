import uuid
import uvicorn
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, create_db, User  # Your DB setup

app = FastAPI(title="Snake & Ladder Server")

# Track connected clients per session
clients: dict[str, list[WebSocket]] = {}

# Track game states per session
games: dict[str, dict] = {}  # session_id -> {"positions": {}, "turn": str | None}

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB exists
create_db()

# ========= REST API ==========

@app.post("/register")
async def register(username: str, password: str, avatar: str = "🙂"):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            return {"status": "error", "message": "Username taken."}
        user = User(username=username, password=password, avatar=avatar)
        db.add(user)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()


@app.post("/login")
async def login(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username, User.password == password).first()
        if user:
            return {
                "status": "success",
                "user_id": user.id,
                "avatar": user.avatar,
                "username": user.username,
            }
        return {"status": "error", "message": "Invalid credentials."}
    finally:
        db.close()


@app.post("/create_session")
async def create_session(request: Request):
    session_id = str(uuid.uuid4())
    base_url = str(request.base_url).rstrip("/")
    return {"session_id": session_id, "invite_link": f"{base_url}/join/{session_id}"}


# ========= GAME WEBSOCKET ==========

@app.websocket("/ws/{session_id}/{username}")
async def websocket_endpoint(websocket: WebSocket, session_id: str, username: str):
    await websocket.accept()

    # Register client
    if session_id not in clients:
        clients[session_id] = []
        games[session_id] = {"positions": {}, "turn": None}

    clients[session_id].append(websocket)
    games[session_id]["positions"].setdefault(username, 0)

    try:
        # Notify everyone that a player joined
        await broadcast_state(session_id, f"{username} joined the game!")

        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "roll":
                roll = random.randint(1, 6)
                pos = games[session_id]["positions"].get(username, 0)
                new_pos = min(pos + roll, 100)
                games[session_id]["positions"][username] = new_pos

                # Switch turns
                players = list(games[session_id]["positions"].keys())
                if games[session_id]["turn"] is None:
                    games[session_id]["turn"] = players[0]
                else:
                    idx = players.index(username)
                    games[session_id]["turn"] = players[(idx + 1) % len(players)]

                # Build update message
                message = {
                    "type": "state_update",
                    "positions": games[session_id]["positions"],
                    "turn": games[session_id]["turn"],
                    "last_roll": roll,
                    "player": username,
                }
                await broadcast(session_id, message)

    except WebSocketDisconnect:
        clients[session_id].remove(websocket)
        if not clients[session_id]:
            clients.pop(session_id, None)
            games.pop(session_id, None)


async def broadcast(session_id: str, message: dict):
    for ws in list(clients.get(session_id, [])):
        try:
            await ws.send_json(message)
        except Exception:
            pass


async def broadcast_state(session_id: str, notice: str):
    await broadcast(session_id, {
        "type": "notice",
        "message": notice,
        "positions": games[session_id]["positions"],
        "turn": games[session_id]["turn"],
    })


# ========= RUN SERVER =========

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
