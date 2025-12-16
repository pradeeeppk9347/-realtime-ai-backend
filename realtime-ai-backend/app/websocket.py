from fastapi import WebSocket
from app.database import supabase
from app.llm import stream_llm
from app.models import event_record
from app.tasks import generate_summary

async def handle_socket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    conversation = [{"role": "system", "content": "You are a helpful assistant."}]

    try:
        while True:
            user_msg = await websocket.receive_text()
            supabase.table("session_events").insert(event_record(session_id, "user", user_msg)).execute()
            conversation.append({"role": "user", "content": user_msg})

            async for token in stream_llm(conversation):
                await websocket.send_text(token)

            supabase.table("session_events").insert(event_record(session_id, "assistant", "[streamed response]")).execute()

    except:
        await generate_summary(session_id)
        await websocket.close()
