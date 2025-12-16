from fastapi import FastAPI, WebSocket
from app.websocket import handle_socket
from app.database import supabase
from app.models import session_record

app = FastAPI()

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    supabase.table("sessions").insert(session_record(session_id, "demo-user")).execute()
    await handle_socket(websocket, session_id)
