from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from model import ChatEntry, SessionLocal, engine, Base
from sqlalchemy import func

app = FastAPI()

# Create the database tables
Base.metadata.create_all(bind=engine)

# HTML for the frontend
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Chat</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container mt-3">
            <h1>FastAPI WebSocket Chat</h1>
            <h2>Your Role: <span id="role"></span></h2>
            <form action="" onsubmit="sendMessage(event)">
                <input type="text" class="form-control" id="messageText" autocomplete="off" />
                <button class="btn btn-outline-primary mt-2">Send</button>
            </form>
            <ul id="messages" class="mt-5"></ul>
        </div>
        
        <script>
            var client_id = prompt("Enter your ID (1234 for counselor):");
            var role = client_id == "1234" ? "Counselor" : "Student";
            document.querySelector("#role").textContent = role;

            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages');
                var message = document.createElement('li');
                var content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };

            function sendMessage(event) {
                var input = document.getElementById("messageText");
                ws.send(input.value);
                input.value = '';
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Connection manager to handle active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, exclude_client_id: str):
        for client_id, connection in self.active_connections.items():
            if client_id != exclude_client_id:
                await connection.send_text(message)

manager = ConnectionManager()

# Endpoint to render the chat page
@app.get("/")
async def get():
    return HTMLResponse(html)

# WebSocket endpoint for chat
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, client_id)
    role = "Counselor" if client_id == "1234" else "Student"

    try:
        while True:
            data = await websocket.receive_text()

            # Store the message in the database
            chat_entry = ChatEntry(
                client=role,
                message=data,
                timestamp=datetime.now()
            )
            db.add(chat_entry)
            db.commit()

            # Send a personal confirmation message
            await manager.send_personal_message(f"You wrote: {data}", websocket)

            # Broadcast the message to other clients, excluding the sender
            await manager.broadcast(f"{role} says: {data}", exclude_client_id=client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"{role} has left the chat", exclude_client_id=client_id)

# Endpoint to view all chat messages from the database
@app.get("/chats")
def get_chats(db: Session = Depends(get_db)):
    chats = db.query(ChatEntry).all()
    return [{"client": chat.client, "message": chat.message, "timestamp": chat.timestamp} for chat in chats]

# Endpoint to clear the chat database
@app.delete("/chats")
def clear_chats(db: Session = Depends(get_db)):
    db.query(ChatEntry).delete()
    db.commit()
    return {"message": "All chats have been cleared."}
