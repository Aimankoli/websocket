from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime
from model import ChatEntry, SessionLocal, engine, Base
from sqlalchemy import func
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the database tables
Base.metadata.create_all(bind=engine)

# HTML for the frontend (keeping this for testing if necessary)
html = ''' ... '''

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, db: Session = Depends(get_db)):
    await manager.connect(websocket, client_id)
    role = "Counselor" if client_id == "1234" else "Student"

    try:
        while True:
            data = await websocket.receive_text()

            chat_entry = ChatEntry(
                client=role,
                message=data,
                timestamp=datetime.now()
            )
            db.add(chat_entry)
            db.commit()

            await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast(f"{role} says: {data}", exclude_client_id=client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"{role} has left the chat", exclude_client_id=client_id)

@app.get("/chats")
def get_chats(db: Session = Depends(get_db)):
    chats = db.query(ChatEntry).all()
    return [{"client": chat.client, "message": chat.message, "timestamp": chat.timestamp} for chat in chats]

@app.delete("/chats")
def clear_chats(db: Session = Depends(get_db)):
    db.query(ChatEntry).delete()
    db.commit()
    return {"message": "All chats have been cleared."}


