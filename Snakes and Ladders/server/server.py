import uuid  # For generating unique session IDs
import uvicorn  # ASGI server to run FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal, create_db, User  # DB session and User model

# Create FastAPI application
app = FastAPI(title="Snake & Ladder Server")

# Dictionary to keep track of connected WebSocket clients
# Key = session_id (string), Value = list of WebSocket connections
clients: dict[str, list[WebSocket]] = {}

# Enable CORS (so browser-based clients can connect from anywhere)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins (you can restrict this later)
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP methods
    allow_headers=["*"]  # allow all headers
)

# Ensure database/tables exist at startup
create_db()


# ========== REST API ENDPOINTS ==========

# Register a new user
@app.post("/register")
async def register(username: str, password: str, avatar: str = "🙂"):
    db = SessionLocal()
    try:
        # Check if username is already taken
        if db.query(User).filter(User.username == username).first():
            return {"status": "error", "message": "Username taken."}

        # Create and save new user
        user = User(username=username, password=password, avatar=avatar)
        db.add(user)
        db.commit()
        return {"status": "success"}
    finally:
        db.close()


# Login endpoint
@app.post("/login")
async def login(username: str, password: str):
    db = SessionLocal()
    try:
        # Check if username+password match
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


# Create a new game session
@app.post("/create_session")
async def create_session():
    session_id = str(uuid.uuid4())  # Unique session ID
    # Generate an invite link (client extracts session_id from URL)
    return {"session_id": session_id, "invite_link": f"http://localhost:8000/join/{session_id}"}


# WebSocket endpoint (real-time communication for game sessions)
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()  # Accept connection

    # Register client in session
    if session_id not in clients:
        clients[session_id] = []
    clients[session_id].append(websocket)

    try:
        while True:
            # Receive message from one client
            data = await websocket.receive_text()

            # Broadcast message to all other clients in same session
            for client in list(clients.get(session_id, [])):
                if client is not websocket:
                    try:
                        await client.send_text(data)
                    except RuntimeError:
                        # Ignore if sending fails
                        pass
    except WebSocketDisconnect:
        # Remove client when disconnected
        clients[session_id].remove(websocket)
        # If session is empty → delete it
        if not clients[session_id]:
            clients.pop(session_id, None)


# Update user statistics after a game
@app.post("/update_stats")
async def update_stats(username: str, result: str, duration: int | None = None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        # Update stats based on game result
        if result == "win":
            user.wins += 1
            # Update fastest win if better than previous
            if duration is not None and duration < user.fastest_win_seconds:
                user.fastest_win_seconds = duration
        elif result == "loss":
            user.losses += 1
        else:
            return {"status": "error", "message": "Invalid result"}

        db.commit()
        return {"status": "success"}
    finally:
        db.close()


# Update user profile (username or avatar)
@app.post("/update_profile")
async def update_profile(username: str, avatar: str = "🙂", new_name: str | None = None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return {"status": "error", "message": "User not found"}

        # Change username if requested and available
        if new_name and new_name != username:
            if db.query(User).filter(User.username == new_name).first():
                return {"status": "error", "message": "Username already taken"}
            user.username = new_name

        # Change avatar
        if avatar:
            user.avatar = avatar

        db.commit()
        return {"status": "success", "username": user.username, "avatar": user.avatar}
    finally:
        db.close()


# Get user statistics
@app.get("/stats")
async def get_stats(username: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return {"status": "error", "message": "User not found"}
        return {
            "username": user.username,
            "avatar": user.avatar,
            "wins": user.wins,
            "losses": user.losses,
            "fastest_win_seconds": user.fastest_win_seconds
        }
    finally:
        db.close()


# Run server directly (python server.py)
if __name__ == "__main__":
    # Run uvicorn server on localhost:8000 with autoreload
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
