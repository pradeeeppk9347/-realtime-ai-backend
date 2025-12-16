from datetime import datetime

def session_record(session_id, user_id):
    return {
        "session_id": session_id,
        "user_id": user_id,
        "start_time": datetime.utcnow().isoformat()
    }

def event_record(session_id, role, content):
    return {
        "session_id": session_id,
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
