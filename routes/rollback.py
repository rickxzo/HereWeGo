from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db
import time
import boto3
ssm = boto3.client("ssm")

router = APIRouter()

@router.get("/api/rollback")
async def rollback(
    deployment_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in rollback)")
    try:
        cursor = conn.cursor()
        '''
        cursor.execute(
            "SELECT D.instance_id, R.name, D.link FROM Deployments D JOIN Repos R ON D.repo_id = R.id WHERE D.id = %s",
            (deployment_id,)
        )
        '''
        cursor.execute(
            " SELECT S.instance_id, R.name, S.id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON R.id = D.repo_id WHERE D.id = %s",
            (deployment_id,)
        )
        # SELECT R.name, S.id, S.instance_id, S.port FROM Deployments D JOIN Slots S ON D.slot_id = S.id JOIN Repos R ON R.id = D.repo_id;
        result = cursor.fetchone()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in rollback) - " + str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    '''
    instance_id = result[0]
    repo_name = result[1].split("/")[-1]
    port = result[2].split(":")[-1]
    dir_name = repo_name + port
    '''
    instance_id = result[0]
    repo_name = result[1].split("/")[-1]
    port = result[3]
    slot_id = result[2]
    dir_name = repo_name + str(port)
    
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                f"kill $(cat /home/ec2-user/{dir_name}/app.pid)",
                f"rm -r /home/ec2-user/{dir_name}",
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    time.sleep(3)
    print("Command sent:", command_id)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
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
    conn.close()
    return {
        "status": "rolled back",
        "output": output
    }
