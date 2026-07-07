from fastapi import APIRouter, Depends, HTTPException
from botocore.exceptions import ClientError
from auth import get_current_user
from db import connect_db
import time
import boto3
ssm = boto3.client("ssm")

router = APIRouter()

@router.get("/api/logs")
def get_logs(
    deployment_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = None
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT R.name, S.instance_id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON D.repo_id = R.id WHERE D.id = %s AND R.user_id = %s", (deployment_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Deployment not found"
            )
        name, instance_id, port = row
        dir_name = name.split("/")[1] + str(port)
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": [
                    f"tail -n 100 /home/ec2-user/{dir_name}/app.log",
                ]
            }
        )
    
        command_id = response["Command"]["CommandId"]
        for _ in range(20):
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
            except ClientError as e:
                if e.response["Error"]["Code"] == "InvocationDoesNotExist":
                    time.sleep(1)
                    continue
                raise
        
            if result["Status"] in ("Success","Failed","Cancelled","TimedOut"):
                break
        
            time.sleep(0.5)
        else:
            raise HTTPException(
                status_code=504,
                detail="Timed out waiting for logs."
            )

        if result["Status"] != "Success":
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve logs."
            )
    
        stdout = result["StandardOutputContent"]
        stderr = result["StandardErrorContent"]
        
        
        return {
            "logs": stdout,
            "errs": stderr
        }
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
