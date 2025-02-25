from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from backend.functions import s3_functions

router = APIRouter()

class S3CreateRequest(BaseModel):
    bucket_name: str
    access: str 

@router.post("/create")
async def create_s3(request: S3CreateRequest):
    try:
        s3_functions.create_s3(request.bucket_name, request.access)
        return {"message": f"S3 bucket '{request.bucket_name}' created successfully with {request.access} access."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))  


@router.get("/list")
async def list_s3():
    buckets = s3_functions.list_s3() 
    if not buckets:
        return {"message": "No S3 buckets found."}
    return {"buckets": buckets}


@router.post("/upload")
async def upload_file(
    bucket_name: str = Form(...),
    file: UploadFile = File(...)
    ):
    try:
        s3_functions.upload_to_s3(bucket_name, file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"File uploaded successfully to bucket '{bucket_name}'."}

@router.delete("/delete/{bucket_name}")
async def delete_s3(bucket_name: str):
    try:
        s3_functions.delete_s3(bucket_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"S3 bucket '{bucket_name}' deleted successfully."}


