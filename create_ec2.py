import boto3
ec2 = boto3.client("ec2", region_name="us-east-1")
from db import connect_db
from fastapi import HTTPException


def create_ec2():
    try:
        response = ec2.run_instances(
            ImageId="ami-0ed094fb1304fd857",  
            InstanceType="t3.micro",
            MinCount=1,
            MaxCount=1,
            KeyName="new-key",
            SecurityGroupIds=["sg-0566bb2c3c816c67f"], 
            IamInstanceProfile={
                "Name": "HereWeGo-SSM"
            }, 
        )
        instance_id = response["Instances"][0]["InstanceId"]
        ec2.get_waiter('instance_running').wait(
            InstanceIds=[instance_id]
        )
        desc = ec2.describe_instances(InstanceIds=[instance_id])
        host = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Instances (id, host) VALUES (%s, %s)", (instance_id, host)
        )
        cursor.execute(
            """
            INSERT INTO Slots (instance_id, port, occupied)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (instance_id, 3000, True)
        )
        slot_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO Slots (instance_id, port, occupied) VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s), (%s, %s, %s)",
            (instance_id, 3001, False, instance_id,
              3002, False, instance_id, 3003, False, instance_id, 3004, False
            )
        )
        conn.commit()
        conn.close()
        return {"instance_id": instance_id, "host": host, "slot_id": slot_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (EC2 Creation) - " + str(e))
