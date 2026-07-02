from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.auth.login import router as login_router
from backend.auth.logout import router as logout_router
from backend.api.routes import router as chat_router

app = FastAPI(title="HR Chatbot API")

app.include_router(login_router,  prefix="/auth", tags=["auth"])
app.include_router(logout_router, prefix="/auth", tags=["auth"])
app.include_router(chat_router,   prefix="/api",  tags=["chat"])

app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_login():
    return FileResponse("frontend/login.html")

@app.get("/chat")
def serve_chat():
    return FileResponse("frontend/chat.html")
