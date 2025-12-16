import openai
from datetime import datetime
from app.database import supabase
from app.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def generate_summary(session_id):
    events = supabase.table("session_events").select("role,content").eq("session_id", session_id).execute().data
    conversation = "\n".join([f"{e['role']}: {e['content']}" for e in events])

    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize this conversation briefly."},
            {"role": "user", "content": conversation}
        ]
    )

    supabase.table("sessions").update({
        "end_time": datetime.utcnow().isoformat(),
        "summary": response.choices[0].message.content
    }).eq("session_id", session_id).execute()
