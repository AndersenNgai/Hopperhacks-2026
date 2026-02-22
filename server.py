from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from llm_client import orb_chat_reply, evaluate_page_relevance

app = FastAPI()

# allow Chrome extension requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatReq(BaseModel):
    message: str
    host: str = ""
    url: str = ""
    title: str = ""
    focusTopic: str = ""
    focusSince: int = 0
    history: list = []

class EvalReq(BaseModel):
    host: str = ""
    url: str = ""
    title: str = ""
    focusTopic: str = ""
    reason: str = ""

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat")
def chat(req: ChatReq):
    reply = orb_chat_reply(
        message=req.message,
        focus_topic=req.focusTopic,
        page_host=req.host,
        page_title=req.title,
        page_url=req.url,
        conversation_history=req.history
    )
    return {"reply": reply}

@app.post("/evaluate")
def evaluate(req: EvalReq):
    return evaluate_page_relevance(
        req.focusTopic,
        req.host,
        req.title,
        req.url,
        req.reason
    )