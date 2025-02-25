from fastapi import APIRouter, HTTPException
from backend.functions import route53_functions
from pydantic import BaseModel

router = APIRouter()

class DNSRecordUpdateRequest(BaseModel):
    zone_id: str
    record_name: str
    record_type: str
    record_value: str
    ttl: int = 300

class DNSRecordCreateRequest(BaseModel):
    zone_id: str
    record_name: str
    record_type: str
    record_value: str
    ttl: int = 300

class ZoneCreateRequest(BaseModel):
    zone_name: str

@router.post("/zone/create")
async def create_zone(request: ZoneCreateRequest):
    zone_id = route53_functions.create_route53_zone(request.zone_name)
    if not zone_id:
        raise HTTPException(status_code=400, detail="Error creating hosted zone")
    return {"zone_id": zone_id, "message": f"Hosted zone '{request.zone_name}' created."}

@router.get("/zone/list")
async def list_zones():
    zones = route53_functions.list_route53_zones()
    if zones:
        return {"zones": zones}
    return {"message": "No hosted zones found."}

@router.delete("/zone/delete")
async def delete_zone(zone_id: str):
    route53_functions.delete_hosted_zone(zone_id)
    return {"message": f"Hosted zone '{zone_id}' deletion initiated."}

@router.post("/record/create")
async def create_record(request: DNSRecordCreateRequest):
    try:
        route53_functions.create_route53_record(
            request.zone_id, 
            request.record_name, 
            request.record_type, 
            request.record_value, 
            request.ttl
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Record '{request.record_name}' created in zone '{request.zone_id}'."}

@router.get("/record/list")
async def list_records(zone_id: str):
    result = route53_functions.list_dns_records(zone_id)
    return result

@router.put("/record/update")
async def update_record(request: DNSRecordUpdateRequest):
    # Check if the record already exists and if its type is different
    existing_record = route53_functions.get_existing_record(request.zone_id, request.record_name)
    if existing_record:
        if existing_record.get("Type") != request.record_type:
            raise HTTPException(
                status_code=400, 
                detail="Cannot update record type. Please delete the existing record and create a new one."
            )
    try:
        route53_functions.update_route53_record(
            request.zone_id, 
            request.record_name, 
            request.record_type, 
            request.record_value, 
            request.ttl
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Record '{request.record_name}' updated in zone '{request.zone_id}'."}

@router.delete("/record/delete")
async def delete_record(zone_id: str, record_name: str):
    route53_functions.delete_route53_record(zone_id, record_name)
    return {"message": f"Record '{record_name}' deletion initiated in zone '{zone_id}'."}
