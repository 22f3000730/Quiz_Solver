from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from solver import solve_quiz
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI()

class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str
    class Config:
        extra = "allow"

@app.post("/")
async def solve_quiz_endpoint(request: QuizRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received quiz request for URL: {request.url}")
    
    # Verify secret
    expected_secret = os.getenv("QUIZ_SECRET")
    if not expected_secret:
        logger.warning("QUIZ_SECRET not set in environment variables. Skipping secret validation.")
    elif request.secret != expected_secret:
        logger.error("Invalid secret provided.")
        raise HTTPException(status_code=403, detail="Invalid secret")
    
    # Start solving in background
    background_tasks.add_task(solve_quiz, request.url, request.email, request.secret)
    
    return {"message": "Task received, solving started."}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
