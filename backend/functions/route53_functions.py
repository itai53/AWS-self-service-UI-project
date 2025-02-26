import boto3
from fastapi import HTTPException

# -------------------------
# RECORD FUNCTIONS
# -------------------------

def create_route53_record(zone_id, record_name, record_type, record_value, ttl=300):
    client = boto3.client('route53')
    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": record_name,
                    "Type": record_type,
                    "TTL": ttl,  # default TTL to 300
                    "ResourceRecords": [{"Value": record_value}]
                }
            }]
        }
    )
    change_info = response.get("ChangeInfo", {})
    change_id = change_info.get("Id")
    status = change_info.get("Status")
    print(f"Record {record_name} ({record_type}) created in zone {zone_id}")
    print(f"Change ID: {change_id}, Status: {status}")

def list_dns_records(zone_id):
    client = boto3.client('route53')
    try:
        response = client.list_resource_record_sets(HostedZoneId=zone_id)
        records = response.get('ResourceRecordSets', [])
        if not records:
            return {"message": f"No DNS records found in zone {zone_id}."}
        record_list = []
        for record in records:
            name = record.get('Name')
            record_type = record.get('Type')
            ttl = record.get('TTL', 'N/A')
            values = ', '.join([r.get('Value') for r in record.get('ResourceRecords', [])]) if record.get('ResourceRecords') else "N/A"
            record_list.append({
                "Name": name,
                "Type": record_type,
                "TTL": ttl,
                "Values": values
            })
        return {"records": record_list}
    except Exception as e:
        return {"error": str(e)}

def update_route53_record(zone_id, record_name, record_type, record_value, ttl=300):
    client = boto3.client('route53')
    response = client.list_resource_record_sets(HostedZoneId=zone_id)
    records = response.get("ResourceRecordSets", [])
    normalized_target = record_name.rstrip(".")
    target_record = None
    for record in records:
        existing_name = record.get("Name", "").rstrip(".")
        if existing_name == normalized_target and record.get("Type") == record_type:
            target_record = record
            break
    if not target_record:
        error_msg = f"Error: Record {record_name} of type {record_type} does not exist in zone {zone_id}."
        print(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)
    response = client.change_resource_record_sets(
        HostedZoneId=zone_id,
        ChangeBatch={
            "Changes": [{
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": record_name,
                    "Type": record_type,
                    "TTL": ttl,
                    "ResourceRecords": [{"Value": record_value}]
                }
            }]
        }
    )
    change_info = response.get("ChangeInfo", {})
    change_id = change_info.get("Id")
    status = change_info.get("Status")
    print(f"Record {record_name} ({record_type}) updated in zone {zone_id}")
    print(f"Change ID: {change_id}, Status: {status}")

def delete_route53_record(zone_id, record_name):
    client = boto3.client('route53')
    # Fetch existing records in the hosted zone
    response = client.list_resource_record_sets(HostedZoneId=zone_id)
    records = response.get('ResourceRecordSets', [])
    # Find the record to delete
    for record in records:
        if record['Name'] == record_name:
            record_type = record['Type']
            if record_type in ["NS", "SOA"]:
                # raise an exception so the user sees an error
                raise HTTPException(status_code=400, detail=f"Cannot delete default record of type {record_type}.")
            record_value = record['ResourceRecords'][0]['Value']
            client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    "Changes": [{
                        "Action": "DELETE",
                        "ResourceRecordSet": {
                            "Name": record_name,
                            "Type": record_type,
                            "TTL": record['TTL'],
                            "ResourceRecords": [{"Value": record_value}]
                        }
                    }]
                }
            )
            print(f"Record {record_name} ({record_type}) deleted from zone {zone_id}")
            return
    raise HTTPException(status_code=404, detail=f"Record {record_name} not found in zone {zone_id}")

def get_existing_record(zone_id, record_name):
    client = boto3.client('route53')
    response = client.list_resource_record_sets(HostedZoneId=zone_id)
    records = response.get("ResourceRecordSets", [])
    normalized_target = record_name.rstrip(".")
    for record in records:
        existing_name = record.get("Name", "").rstrip(".")
        if existing_name == normalized_target:
            return record
    return None


# -------------------------
# ZONE FUNCTIONS
# -------------------------

def create_route53_zone(zone_name):
    client = boto3.client('route53')
    response = client.create_hosted_zone(
        Name=zone_name,
        CallerReference=str(hash(zone_name)),
        HostedZoneConfig={"Comment": "CLI-managed zone", "PrivateZone": False},
    )
    # Extract the zone ID and add tags
    zone_id = response['HostedZone']['Id'].split('/')[-1]
    client.change_tags_for_resource(
        ResourceType='hostedzone',
        ResourceId=zone_id,
        AddTags=[{"Key": "cli-managed", "Value": "true"}]
    )
    print("Hosted zone created:")
    print(f"Hosted zone {zone_name} created with ID {response['HostedZone']['Id']}")
    return zone_id

def list_route53_zones():
    client = boto3.client('route53')
    zones = client.list_hosted_zones()['HostedZones']
    
    cli_managed_zones = []
    for zone in zones:
        zone_id = zone['Id'].split('/')[-1]  # Extract only the Zone ID
        try:
            tags = client.list_tags_for_resource(ResourceType='hostedzone', ResourceId=zone_id)['ResourceTagSet']['Tags']
            if any(tag['Key'] == 'cli-managed' and tag['Value'] == 'true' for tag in tags):
                cli_managed_zones.append({
                    "ZoneId": zone_id, 
                    "HostName": zone['Name']
                })
        except Exception as e:
            print(f"Error retrieving tags for {zone_id}: {e}")
            continue 

    return cli_managed_zones



def delete_hosted_zone(zone_id):
    client = boto3.client('route53')
    # Try to get tags for the hosted zone
    try:
        tags_response = client.list_tags_for_resource(
            ResourceType='hostedzone',
            ResourceId=zone_id
        )
        tags = tags_response.get('ResourceTagSet', {}).get('Tags', [])
        cli_managed = any(tag.get('Key') == 'cli-managed' and tag.get('Value') == 'true' for tag in tags)
    except Exception as e:
        print(f"Error retrieving tags for hosted zone {zone_id}: {e}")
        return {"error": "Invalid or non-existent hosted zone ID."}  

    if not cli_managed:
        return {"message": "No CLI-managed zone found for deletion."}  
    # List all records in the zone
    try:
        response = client.list_resource_record_sets(HostedZoneId=zone_id)
        records = response.get('ResourceRecordSets', [])
    except Exception as e:
        print(f"Error listing records for hosted zone {zone_id}: {e}")
        return {"error": "Failed to list records for the hosted zone."}  # ✅ More user-friendly error

    # Filter out default NS and SOA records
    records_to_delete = [record for record in records if record.get('Type') not in ['NS', 'SOA']]

    # Delete each non-default record
    for record in records_to_delete:
        try:
            print(f"Deleting record {record.get('Name')} ({record.get('Type')})...")
            client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    "Changes": [{
                        "Action": "DELETE",
                        "ResourceRecordSet": record
                    }]
                }
            )
        except Exception as e:
            print(f"Error deleting record {record.get('Name')} ({record.get('Type')}): {e}")
            return {"error": f"Failed to delete record {record.get('Name')}."}  

    # Delete the hosted zone
    try:
        client.delete_hosted_zone(Id=zone_id)
        print(f"Hosted zone {zone_id} deleted successfully.")
        return {"message": "Hosted zone deleted successfully."}  
    except Exception as e:
        print(f"Error deleting hosted zone {zone_id}: {e}")
        return {"error": "Failed to delete hosted zone."}  
