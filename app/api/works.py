from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
from app.schemas.work_schemas import WorkCreate, WorkRead

router = APIRouter()

fake_db = {}
work_counter = 0

@router.post("/", response_model=WorkRead)
async def create_work(payload: WorkCreate):
    global work_counter
    work_counter += 1
    data = payload.dict()
    data.update({"id": work_counter})
    fake_db[work_counter] = data
    return data

@router.post("/{work_id}/trial-balance")
async def upload_trial_balance(work_id: int, file: UploadFile = File(...)):
    # save temporarily and parse via csv_parser (stub)
    contents = await file.read()
    # In real app, call app.utils.csv_parser.parse_trial_balance
    return {"filename": file.filename, "size": len(contents)}
