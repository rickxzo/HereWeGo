from fastapi import APIRouter, Depends, HTTPException
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
    conn = connect_db()
    cursor = conn.cursor()
    '''
    cursor.execute(
        "SELECT R.name, D.instance_id, D.link FROM Repos R JOIN Deployments D ON R.id = D.repo_id WHERE D.id = %s", (deployment_id,)
    )
    '''
    cursor.execute(
        "SELECT R.name, S.instance_id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON D.repo_id = R.id WHERE D.id = %s", (deployment_id,)
    )
    # SELECT R.name, S.instance_id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON D.repo_id = R.id

    
    #name, instance_id, link = cursor.fetchone()
    name, instance_id, port = cursor.fetchone()
    #dir_name = name.split("/")[1] + link.split(":")[2]
    dir_name = name.split("/")[1] + str(port)
    conn.close()
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                f"cat /home/ec2-user/{dir_name}/app.log",
            ]
        }
    )

    command_id = response["Command"]["CommandId"]
    time.sleep(2)
    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    stdout = result["StandardOutputContent"]
    stderr = result["StandardErrorContent"]
    
    
    return {
        "logs": stdout,
        "errs": stderr
    }
