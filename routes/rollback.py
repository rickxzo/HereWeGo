from fastapi import APIRouter, Depends, HTTPException
from botocore.exceptions import ClientError
from auth import get_current_user
from db import connect_db
import time
import boto3
ssm = boto3.client("ssm")

router = APIRouter()

@router.get("/api/rollback")
def rollback(
    deployment_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in rollback)")
    try:
        cursor = conn.cursor()
        cursor.execute(
            " SELECT S.instance_id, R.name, S.id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON R.id = D.repo_id WHERE D.id = %s AND R.user_id = %s",
            (deployment_id, user_id)
        )
        result = cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Deployment access error")
    finally:
        conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    instance_id = result[0]
    repo_name = result[1].split("/")[-1]
    port = result[3]
    slot_id = result[2]
    dir_name = repo_name + str(port)

    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={
                "commands": [
                    f"kill $(cat /home/ec2-user/{dir_name}/app.pid)",
                    f"rm -rf /home/ec2-user/{dir_name}",
                ]
            }
        )
        command_id = response["Command"]["CommandId"]
    except Exception:
        raise HTTPException(500, "Failed to contact deployment instance")
    for _ in range(20):
        try:
            output = ssm.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "InvocationDoesNotExist":
                time.sleep(1)
                continue
            raise
        if output["Status"] in (
            "Success",
            "Failed",
            "Cancelled",
            "TimedOut"
        ):
            break
        time.sleep(1)
    else:
        raise HTTPException(
            500,
            "Rollback timed out"
        )
        
        
    if output["Status"] != "Success":
        raise HTTPException(
            500,
            "Rollback failed on instance"
        )
    
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Slots SET occupied = false WHERE id=%s", (slot_id,)
        )
        cursor.execute(
            "UPDATE Deployments SET status = %s WHERE id = %s",
            ("rolled back", deployment_id)
        )
        conn.commit()
        return {
            "status": "rolled back",
            "output": output
        }
    except Exception as e:
        raise HTTPException(
            500,
            "Rollback succeeded, but failed to update deployment state."
        )
    finally:
        conn.close()
