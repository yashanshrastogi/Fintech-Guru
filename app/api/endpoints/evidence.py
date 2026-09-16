from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.domain import FinancialProfile, generate_uuid, User
from app.api.dependencies.auth import get_current_user
from app.services.storage import get_storage_provider
from app.config import settings
from llm.client import LLMClient
from pydantic import BaseModel
import os
import shutil

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB
ALLOWED_EXTENSIONS = {".txt", ".png", ".jpg", ".jpeg", ".pdf"}

@router.post("/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = current_user.profile
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")
        
    file.file.seek(0, 2)
    size = file.file.tell()
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")
    file.file.seek(0)
    
    file_bytes = file.file.read()
    
    storage = get_storage_provider()
    saved_path = storage.upload_file(file_bytes, file.filename, file.content_type)
        
    try:
        # Mocking extraction of text from the file for now, or read if txt
        if ext == ".txt":
            content = file_bytes.decode("utf-8")
        else:
            content = f"[Extracted from image: {file.filename}, stored at {saved_path}]"

        # Call Qwen
        client = LLMClient(endpoint=settings.OLLAMA_BASE_URL, model=settings.OLLAMA_MODEL)
        extracted = client.extract_evidence(content)
        
        # Apply to canonical state if confident
        if extracted:
            # Check for salary updates
            if "extracted_salary" in extracted and extracted["extracted_salary"] is not None:
                incomes = list(profile.recurring_incomes)
                incomes.append({
                    "category": "Salary",
                    "direction": "credit",
                    "average_amount": float(extracted["extracted_salary"]),
                    "frequency_days": 30, # default monthly
                    "is_salary": True
                })
                profile.recurring_incomes = incomes
                
            if "cancellation_request" in extracted and extracted["cancellation_request"]:
                stops = list(profile.expense_categories_willing_to_stop)
                stops.append("Subscriptions") # Generic for now
                profile.expense_categories_willing_to_stop = stops
                
            db.commit()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidence processing failed: {str(e)}")
            
    return {"status": "success", "extracted": extracted, "saved_path": saved_path}
