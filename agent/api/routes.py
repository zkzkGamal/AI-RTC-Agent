from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from agent.service.chat import Chat

chat_service = Chat()


class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    user_id: str
    response: str
    pending_confirmation: Optional[Dict[str, Any]] = None
    messages_count: int


class CvUploadResponse(BaseModel):
    user_id: str
    file_name: str
    keywords: List[str]
    summary: str
    knowledge: Dict[str, Any]


def register_routes(app: FastAPI) -> None:
    @app.post("/api/chat", response_model=ChatResponse)
    async def chat_endpoint(payload: ChatRequest):
        try:
            result = await chat_service.send_message(
                user_id=payload.user_id,
                session_id=payload.session_id,
                message=payload.message,
            )
            return result
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.post("/api/cv/upload", response_model=CvUploadResponse)
    async def upload_cv_endpoint(
        user_id: str = Form(...),
        file: UploadFile = File(...),
    ):
        """
        Accept a candidate CV (PDF / Word / Markdown), save it into the global
        content/ folder, read it, extract keywords + knowledge, and store it as
        the user's CV memory so the agent can answer based on it.
        """
        try:
            data = await file.read()
            result = await chat_service.ingest_cv_upload(
                user_id=user_id,
                filename=file.filename,
                data=data,
            )
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/sessions/{user_id}")
    def get_user_sessions_endpoint(user_id: str):
        try:
            sessions = chat_service.get_user_sessions(user_id)
            return {"sessions": sessions}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))

    @app.get("/api/sessions/{session_id}/messages")
    def get_session_messages_endpoint(session_id: str):
        try:
            messages = chat_service.get_session_messages(session_id)
            return {"messages": messages}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
