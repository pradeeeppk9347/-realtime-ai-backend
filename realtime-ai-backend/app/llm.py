import openai
from app.config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

async def stream_llm(messages):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=messages,
        stream=True
    )

    async for chunk in response:
        if "content" in chunk.choices[0].delta:
            yield chunk.choices[0].delta.content
