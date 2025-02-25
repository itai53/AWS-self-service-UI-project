from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.functions import ec2_functions

router = APIRouter()

class EC2CreateRequest(BaseModel):
    instance_name: str
    instance_type: str
    ami: str
    pubkey_path: str

class InstanceIdentifierRequest(BaseModel):
    instance_identifier: str

@router.post("/create")
async def create_ec2(request: EC2CreateRequest):
    result = ec2_functions.create_ec2(
        request.instance_name, 
        request.instance_type, 
        request.ami, 
        request.pubkey_path
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {
        "instance_id": result["id"], 
        "instance_name": result["name"], 
        "public_ip": result["public_ip"],
        "message": result["message"]
    }

@router.get("/list")
async def list_ec2():
    instances = ec2_functions.list_ec2()
    return instances

@router.post("/start")
async def start_ec2(request: InstanceIdentifierRequest):
    instance_identifier = request.instance_identifier
    if instance_identifier.startswith("i-"):
        result = ec2_functions.start_ec2(instance_id=instance_identifier)
    else:
        result = ec2_functions.start_ec2(instance_name=instance_identifier)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}

@router.post("/stop")
async def stop_ec2(request: InstanceIdentifierRequest):
    instance_identifier = request.instance_identifier
    if instance_identifier.startswith("i-"):
        result = ec2_functions.stop_ec2(instance_id=instance_identifier)
    else:
        result = ec2_functions.stop_ec2(instance_name=instance_identifier)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}

@router.post("/terminate")
async def terminate_ec2(request: InstanceIdentifierRequest):
    instance_identifier = request.instance_identifier
    if instance_identifier.startswith("i-"):
        result = ec2_functions.delete_ec2(instance_id=instance_identifier)
    else:
        result = ec2_functions.delete_ec2(instance_name=instance_identifier)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": result["message"]}
