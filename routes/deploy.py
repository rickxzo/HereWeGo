from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db
from create_ec2 import create_ec2
from uuid import UUID
import time
import boto3
ssm = boto3.client("ssm")

router = APIRouter()


@router.get("/api/deploy")
async def deploy_repo(
    repo_id: UUID,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in deploy)")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT access_token FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        github_token = result[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query for user in deploy) - " + str(e))
    
    try:
        cursor.execute(
            "SELECT name, build_cmd, run_cmd, domain FROM Repos WHERE id = %s",
            (str(repo_id),)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Repo not found")
        repo_name, build, run, domain = result
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in deploy) - " + str(e))
    

    clone_url = f"https://{github_token}@github.com/{repo_name}.git"


    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in deploy)")
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, value FROM Secrets WHERE repo_id = %s",
            (str(repo_id),)  
        )
        secrets = cursor.fetchall()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query for secrets in deploy)")
    
    conn = connect_db()
    cursor = conn.cursor()
    '''
    cursor.execute(
        "SELECT S.instance_id, I.host, S.port FROM Slots S JOIN Instances I ON S.instance_id = I.id WHERE S.occupied = false ORDER BY S.created_at LIMIT 1"
    )
    '''
    cursor.execute(
        '''
        SELECT I.id, I.host, S.port, S.id
        FROM Slots S JOIN Instances I ON I.id = S.instance_id 
        WHERE S.occupied = FALSE ORDER BY S.created_at LIMIT 1;
        '''
    )
    slot = cursor.fetchone()
    if not slot:
        ec2_res = create_ec2()
        time.sleep(2)
        instance_id = ec2_res["instance_id"]
        host = ec2_res["host"]
        port = 3000
    else:
        instance_id, host, port, slot_id = slot
        cursor.execute(
            "UPDATE Slots SET occupied = true WHERE id = %s",
            (slot_id,)
        )
        conn.commit()
    conn.close()

    env_vars = ""
    for name, value in secrets:
        env_vars += f"export {name}={value}\n"

    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters = {
            "commands": [
                f"yum update -y > /home/ec2-user/{repo_name.split('/')[-1] + str(port)}.log 2>&1",
                f"yum install -y git python3 python3-pip >> /home/ec2-user/{repo_name.split('/')[-1] + str(port)}.log 2>&1",
                
                "cd /home/ec2-user",

                f"rm -rf {repo_name.split('/')[-1] + str(port)}",

                f"git clone {clone_url} {repo_name.split('/')[-1] + str(port)} >> {repo_name.split('/')[-1] + str(port)}.log 2>&1",

                f"mv {repo_name.split('/')[-1] + str(port)}.log {repo_name.split('/')[-1] + str(port)}/",

                f"cat {repo_name.split('/')[-1] + str(port)}/{repo_name.split('/')[-1] + str(port)}.log > {repo_name.split('/')[-1] + str(port)}/app.log",

                #f"cat {repo_name.split('/')[-1] + str(port)}.log >> /{repo_name.split('/')[-1] + str(port)}/app.log 2>&1",

                f"cd /home/ec2-user/{repo_name.split('/')[-1] + str(port)}",

                "python3 -m venv venv",

                f"cd /home/ec2-user/{repo_name.split('/')[-1] + str(port)} && venv/bin/pip install requests",

                "source venv/bin/activate",

                f"{build} >> app.log 2>&1",

                f"export PORT={port}",

                env_vars,

                f"nohup sh -c 'source venv/bin/activate && {run}' >> app.log 2>&1 & echo $! > app.pid\n",
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    time.sleep(2)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    url = f"http://{host}:{port}"
    link = f"{domain}.herewego.website"
    nginx_cmd = f"""
server {{
    listen 80;

    server_name {link};

    location / {{
        proxy_pass {url};

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
    """
    response2 = ssm.send_command(
        InstanceIds=["i-0053d531be504c4a1"],
        DocumentName="AWS-RunShellScript",
        Parameters = {
            "commands": [
                f"cat > /etc/nginx/conf.d/{domain}.conf << 'EOF'\n{nginx_cmd}\nEOF",
                "nginx -t",
                "systemctl reload nginx"
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    conn = connect_db()
    cursor = conn.cursor()
    '''
    cursor.execute(
        "INSERT INTO Deployments (repo_id, instance_id, link, url, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (str(repo_id), instance_id, url, link, "running")
    )
    '''
    cursor.execute(
        '''
        INSERT INTO Deployments (repo_id, status, slot_id) VALUES (%s, %s, %s) RETURNING id
        ''',
        (str(repo_id), "running", slot_id)
    )
    deployment_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return {
        "status": "deploy started",
        "url": link,
        "deployment_id": deployment_id
    }
