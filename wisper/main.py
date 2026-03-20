from fastapi import FastAPI, UploadFile
from whisper import transcribe_audio
from llm import process_text
from actions import execute_action

app = FastAPI()

@app.post("/voice")
async def voice_input(file: UploadFile):
    text = transcribe_audio(file)
    structured = process_text(text)
    result = execute_action(structured)
    return {"text": text, "action": result}