import json
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")

def create_s3(bucket_name, access):
    try:
        # Check if the bucket already exists
        existing_buckets = s3_client.list_buckets()
        for bucket in existing_buckets["Buckets"]:
            if bucket["Name"] == bucket_name:
                raise Exception(f"Bucket name '{bucket_name}' already exists.")

        # Attempt to create the bucket
        s3_client.create_bucket(Bucket=bucket_name)

        if access == "public":
            try:
                # Disabling block public access settings to allow a public bucket policy.
                s3_client.put_public_access_block(
                    Bucket=bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': False,
                        'IgnorePublicAcls': False,
                        'BlockPublicPolicy': False,
                        'RestrictPublicBuckets': False
                    }
                )
                # Configure the bucket policy for public read access.
                bucket_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{bucket_name}/*"
                        }
                    ]
                }
                s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(bucket_policy))
            except Exception as e:
                raise Exception(f"Error configuring public access: {e}")

        try:
            # Apply tags to the bucket
            s3_client.put_bucket_tagging(
                Bucket=bucket_name,
                Tagging={
                    'TagSet': [
                        {'Key': 'cli-managed', 'Value': 'true'},
                        {'Key': 'access', 'Value': access},
                        {'Key': 'Name', 'Value': bucket_name},
                    ]
                }
            )
        except Exception as e:
            raise Exception(f"Error tagging bucket: {e}")

        print(f"S3 bucket '{bucket_name}' created with {access} access.")
        return {"message": f"S3 bucket '{bucket_name}' created successfully with {access} access."}

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "BucketAlreadyExists":
            raise Exception(f"Bucket name '{bucket_name}' is already in use globally.")
        elif error_code == "BucketAlreadyOwnedByYou":
            raise Exception(f"Bucket name '{bucket_name}' already exists in your AWS account.")
        else:
            raise Exception(f"Error creating S3 bucket: {e}")


def list_s3():
    s3_client = boto3.client("s3")
    buckets_list = []
    try:
        response = s3_client.list_buckets()
    except Exception as e:
        print("Error listing buckets:", e)
        return []
    
    for bucket in response.get("Buckets", []):
        bucket_name = bucket["Name"]
        try:
            tag_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
            tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])}
            if tags.get("cli-managed") == "true":
                access = tags.get("access", "private")
                buckets_list.append({
                    "BucketName": bucket_name,
                    "Access": access
                })
        except s3_client.exceptions.ClientError:
            continue
    return buckets_list

def upload_to_s3(bucket_name, file):
    try:
        tag_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
        tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])}
        if tags.get("cli-managed") != "true":
            raise Exception(f"Bucket '{bucket_name}' is not CLI-managed.")
    except s3_client.exceptions.ClientError:
        raise Exception(f"Bucket '{bucket_name}' does not have CLI-managed tagging.")
        

    try:
        file_name = file.filename
        s3_client.upload_fileobj(file.file, bucket_name, file_name)
        print(f"File '{file_name}' uploaded to '{bucket_name}'.")
    except Exception as e:
        print(f"Error uploading file: {e}")

def delete_s3(bucket_name):
    # Check if the bucket is cli-,manged=true.
    try:
        tag_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
        tags = {tag["Key"]: tag["Value"] for tag in tag_response.get("TagSet", [])}
        if tags.get("cli-managed") != "true":
            raise Exception(f"Bucket '{bucket_name}' is not CLI-managed.")
    except s3_client.exceptions.ClientError as e:
        raise Exception(f"Could not retrieve tags for bucket '{bucket_name}': {e}")
    
    # Empty the bucket by deleting all objects inside.
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                delete_keys = {'Objects': [{'Key': obj['Key']} for obj in page['Contents']]}
                s3_client.delete_objects(Bucket=bucket_name, Delete=delete_keys)
        print(f"Bucket '{bucket_name}' has been emptied.")
    except Exception as e:
        raise Exception(f"Error emptying bucket: {e}")

    # Now delete the bucket.
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"S3 bucket '{bucket_name}' has been deleted.")
    except Exception as e:
        raise Exception(f"Error deleting S3 bucket: {e}")

