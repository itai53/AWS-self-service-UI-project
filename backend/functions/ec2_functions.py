from datetime import datetime
import os
import boto3

config_path = os.path.join(os.path.dirname(__file__), "ec2configuration", "configuration.txt")
data = {}
with open(config_path, "r") as file:
    for line in file:
        key, value = line.strip().split(":", 1)
        data[key.strip()] = value.strip()
subnet_id = data.get("subnet-id")
security_group = data.get("security-group")

def get_or_create_key_pair_boto(pubkey_path: str) -> str:
    basename = os.path.basename(pubkey_path)
    # Remove .pem.pub or .pub if present
    if basename.endswith(".pem.pub"):
        key_name = basename[:-8]
    elif basename.endswith(".pub"):
        key_name = basename[:-4]
    else:
        key_name = basename
    ec2_client = boto3.client("ec2")
    try:
        ec2_client.describe_key_pairs(KeyNames=[key_name])
        print(f"Key pair '{key_name}' exists.")
    except ec2_client.exceptions.ClientError:
        print(f"Key pair '{key_name}' not found. Importing your public key.")
        with open(pubkey_path, 'r', encoding='utf-8') as f:
            public_key = f.read().strip()
        ec2_client.import_key_pair(KeyName=key_name, PublicKeyMaterial=public_key)
    return key_name

def delete_ec2(instance_id=None, instance_name=None):
    ec2_client = boto3.client("ec2")
    if not instance_id:
        if instance_name:
            response = ec2_client.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    {"Name": "tag:cli-managed", "Values": ["true"]}
                ]
            )
            instances = [
                instance for reservation in response.get("Reservations", [])
                for instance in reservation.get("Instances", [])
            ]
            if not instances:
                error_msg = f"No instance found with name {instance_name}."
                print(error_msg)
                return {"error": error_msg}
            instance_id = instances[0]["InstanceId"]
        else:
            error_msg = "Error: Must specify either instance_id or instance_name."
            print(error_msg)
            return {"error": error_msg}
    try:
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        success_msg = f"Terminating instance {instance_id}"
        print(success_msg)
        return {"message": success_msg}
    except Exception as e:
        error_msg = f"Error terminating instance: {e}"
        print(error_msg)
        return {"error": error_msg}

def start_ec2(instance_id=None, instance_name=None):
    ec2_client = boto3.client("ec2")
    if not instance_id:
        if instance_name:
            response = ec2_client.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    {"Name": "tag:cli-managed", "Values": ["true"]},
                    {"Name": "instance-state-name", "Values": ["stopped"]}
                ]
            )
            instances = [
                instance for reservation in response.get("Reservations", [])
                for instance in reservation.get("Instances", [])
            ]
            if not instances:
                error_msg = f"No stopped instance found with name {instance_name}."
                print(error_msg)
                return {"error": error_msg}
            instance_id = instances[0]["InstanceId"]
        else:
            error_msg = "Error: Must specify either instance_id or instance_name."
            print(error_msg)
            return {"error": error_msg}
    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        success_msg = f"Starting instance {instance_id}"
        print(success_msg)
        return {"message": success_msg}
    except Exception as e:
        error_msg = f"Error starting instance: {e}"
        print(error_msg)
        return {"error": error_msg}

def create_ec2(cli_name, cli_instance_type, cli_ami, cli_pubkey_path):
    if not os.path.isfile(cli_pubkey_path):
        error_msg = f"Error: Public key file '{cli_pubkey_path}' does not exist."
        print(error_msg)
        return {"error": error_msg}
    final_key_name = get_or_create_key_pair_boto(cli_pubkey_path)

    if cli_instance_type == "t4g.nano":
        if cli_ami == "ubuntu":
            resolved_ami = "ami-0a7a4e87939439934"  # ARM Ubuntu
            user_data_file = os.path.join(os.path.dirname(__file__), "ec2configuration", "user_data_ubuntu.sh")

        elif cli_ami == "amazon-linux":
            resolved_ami = "ami-0c518311db5640eff"  # ARM Amazon Linux
            user_data_file = os.path.join(os.path.dirname(__file__), "ec2configuration", "user_data_amazon-linux.sh")

        else:
            error_msg = "Invalid AMI selection."
            print(error_msg)
            return {"error": error_msg}
    elif cli_instance_type == "t3.nano":
        if cli_ami == "ubuntu":
            resolved_ami = "ami-04b4f1a9cf54c11d0"  # x86_64 Ubuntu
            user_data_file = os.path.join(os.path.dirname(__file__), "ec2configuration", "user_data_ubuntu.sh")

        elif cli_ami == "amazon-linux":
            resolved_ami = "ami-085ad6ae776d8f09c"  # x86_64 Amazon Linux
            user_data_file = os.path.join(os.path.dirname(__file__), "ec2configuration", "user_data_amazon-linux.sh")

        else:
            error_msg = "Invalid AMI selection."
            print(error_msg)
            return {"error": error_msg}
    else:
        error_msg = "Invalid instance type selection."
        print(error_msg)
        return {"error": error_msg}

    with open(user_data_file, 'r') as f:
        user_data_script = f.read()

    max_instances = 2
    ec2_client = boto3.client("ec2")
    response = ec2_client.describe_instances(
        Filters=[
            {"Name": "tag:cli-managed", "Values": ["true"]},
            {"Name": "instance-state-name", "Values": ["running"]}
        ]
    )
    running_instances = sum(
        1 for reservation in response.get("Reservations", [])
        for _ in reservation.get("Instances", [])
    )
    if running_instances >= max_instances:
        error_msg = "Maximum running instances is 2. Cannot create a new instance if current running instances is 2."
        print(error_msg)
        return {"error": error_msg}

    resource_ec2 = boto3.resource("ec2")
    date_created = datetime.now().strftime("%Y-%m-%d")
    instance_name = f"{cli_name}"
    try:
        instances = resource_ec2.create_instances(
            ImageId=resolved_ami,
            MinCount=1,
            MaxCount=1,
            InstanceType=cli_instance_type,
            KeyName=final_key_name,
            NetworkInterfaces=[{
                "AssociatePublicIpAddress": True,
                "DeviceIndex": 0,
                "SubnetId": subnet_id,
                "Groups": [security_group],
            }],
            TagSpecifications=[{
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": instance_name},
                    {"Key": "creation_date", "Value": date_created},
                    {"Key": "cli-managed", "Value": "true"},
                    {"Key": "owner", "Value": "itaimoshe"},
                ]
            }],
            UserData=user_data_script,
        )
    except Exception as e:
        error_msg = f"Error creating instance: {e}"
        print(error_msg)
        return {"error": error_msg}

    instance = instances[0]
    public_ip = instance.public_ip_address
    success_msg = f"EC2 Instance Created: - Instance ID: {instance.id}, Name: {instance_name}, Public IP: {public_ip}"
    print(success_msg)
    return {"id": instance.id, "name": instance_name, "public_ip": public_ip, "message": success_msg}

def list_ec2():
    ec2_client = boto3.client("ec2")
    instances_list = []
    try:
        response = ec2_client.describe_instances(
            Filters=[{"Name": "tag:cli-managed", "Values": ["true"]}]
        )
        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
                name_tag = tags.get("Name", "Unknown")
                public_ip = instance.get("PublicIpAddress", "N/A")
                instances_list.append({
                    "id": instance["InstanceId"],
                    "name": name_tag,
                    "public_ip": public_ip,
                    "state": instance["State"]["Name"]
                })
        return {"instances": instances_list}
    except Exception as e:
        error_msg = f"No EC2 instances found: {e}"
        print(error_msg)
        return {"error": error_msg}

def stop_ec2(instance_id=None, instance_name=None):
    ec2_client = boto3.client("ec2")
    if not instance_id:
        if instance_name:
            response = ec2_client.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    {"Name": "tag:cli-managed", "Values": ["true"]},
                    {"Name": "instance-state-name", "Values": ["running"]}
                ]
            )
            instances = [
                instance for reservation in response.get("Reservations", [])
                for instance in reservation.get("Instances", [])
            ]
            if not instances:
                error_msg = f"No running instance found with name {instance_name}."
                print(error_msg)
                return {"error": error_msg}
            instance_id = instances[0]["InstanceId"]
        else:
            error_msg = "Error: Must specify either instance_id or instance_name."
            print(error_msg)
            return {"error": error_msg}
    try:
        ec2_client.stop_instances(InstanceIds=[instance_id])
        success_msg = f"Stopping instance {instance_id}"
        print(success_msg)
        return {"message": success_msg}
    except Exception as e:
        error_msg = f"Error stopping instance: {e}"
        print(error_msg)
        return {"error": error_msg}

def start_ec2(instance_id=None, instance_name=None):
    ec2_client = boto3.client("ec2")
    if not instance_id:
        if instance_name:
            response = ec2_client.describe_instances(
                Filters=[
                    {"Name": "tag:Name", "Values": [instance_name]},
                    {"Name": "tag:cli-managed", "Values": ["true"]},
                    {"Name": "instance-state-name", "Values": ["stopped"]}
                ]
            )
            instances = [
                instance for reservation in response.get("Reservations", [])
                for instance in reservation.get("Instances", [])
            ]
            if not instances:
                error_msg = f"No stopped instance found with name {instance_name}."
                print(error_msg)
                return {"error": error_msg}
            instance_id = instances[0]["InstanceId"]
        else:
            error_msg = "Error: Must specify either instance_id or instance_name."
            print(error_msg)
            return {"error": error_msg}
    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        success_msg = f"Starting instance {instance_id}"
        print(success_msg)
        return {"message": success_msg}
    except Exception as e:
        error_msg = f"Error starting instance: {e}"
        print(error_msg)
        return {"error": error_msg}
