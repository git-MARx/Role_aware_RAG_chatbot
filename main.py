from fastapi import FastAPI
from backend.auth.login import router as login_router
from backend.auth.logout import router as logout_router

app = FastAPI(title="HR Chatbot API")

app.include_router(login_router,  prefix="/auth", tags=["auth"])
app.include_router(logout_router, prefix="/auth", tags=["auth"])
