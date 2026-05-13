import random
import boto3
ec2 = boto3.client("ec2", region_name="us-east-1")
ssm = boto3.client("ssm")

from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, logger
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

import httpx
import psycopg2
import subprocess
import requests

from jose import jwt
from datetime import datetime, time, timedelta
import time as time2


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

app = FastAPI()

def connect_db():
    return psycopg2.connect(
        host="ep-soft-field-aoewhaic-pooler.c-2.ap-southeast-1.aws.neon.tech",
        dbname="neondb",
        user="neondb_owner",
        password=os.getenv('NEONDB_PASS'),
        sslmode="require",
    )


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)


security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("user_id")
    except:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/", response_class=HTMLResponse)
async def docs():
    with open("demo.html", encoding="utf-8") as f:
        return f.read()


@app.get("/login/github")
def login_github():
    url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={CLIENT_ID}&scope=repo user"
    )
    return RedirectResponse(url)



@app.get("/auth/github/callback")
async def github_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
            },
        )

        access_token = token_res.json().get("access_token")

        user_res = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        user_data = user_res.json()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM users WHERE github_id = %s",
        (user_data["id"],)
    )
    existing_user = cursor.fetchone()

    if existing_user:
        user_id = existing_user[0]

        cursor.execute(
            "UPDATE users SET access_token = %s WHERE github_id = %s",
            (access_token, user_data["id"])
        )

    else:
        cursor.execute(
            """
            INSERT INTO users (github_id, username, avatar, access_token)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_data["id"], user_data["login"], user_data["avatar_url"], access_token)
        )
        user_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    jwt_token = create_access_token({"user_id": str(user_id)})

    return {
        "token": jwt_token,
        "user": {
            "id": user_id,
            "username": user_data["login"],
            "avatar": user_data["avatar_url"]
        }
    }



@app.get("/api/me")
def get_me(user_id: str = Depends(get_current_user)):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username, avatar FROM users WHERE id = %s",
        (user_id,)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": user_id,
        "username": user[0],
        "avatar": user[1]
    }


@app.get("/api/github-repos")
def get_github_repos(user_id: str = Depends(get_current_user)):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection)")

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT access_token FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query) - " + str(e))

    cursor.close()
    conn.close()

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    github_token = result[0]

    try:
        res = requests.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {github_token}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (GitHub API) - " + str(e))

    repos = [
        {   
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"]
        }
        for repo in res.json()
    ]
    return repos



@app.get("/api/create-repo")
def create_repo(
    repo_name: str,
    build: str,
    run: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection)")
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Repos (user_id, name, build_cmd, run_cmd)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, repo_name, build, run)
        )
        conn.commit()
        return {"repo_id": cursor.fetchone()[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error (DB Insert for repo) {str(e)}")
    

@app.get("/api/repos")
def list_repos(user_id: str = Depends(get_current_user)):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM Repos WHERE user_id = %s",
            (user_id,)
        )
        projects = cursor.fetchall()
        return [{"id": p[0], "name": p[2], "build_cmd": p[3], "run_cmd": p[4]} for p in projects]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query)")
    

@app.post('/api/add-secrets')
async def add_secrets(
    repo_id: UUID,
    request: Request,
    user_id: str = Depends(get_current_user)
):
    try:
        body = await request.body()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (Request Body)")
    content = body.decode("utf-8")
    content = content.split("\n")
    secrets = {}
    try:
        for line in content:
            if "=" in line:
                name, value = line.split("=", 1)
                secrets[name.strip()] = value.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (Processing Secrets) - " + str(e))
    cmd = "INSERT INTO Secrets (repo_id, name, value) VALUES "

    for name, value in secrets.items():
        cmd += f"('{str(repo_id)}', '{name}', '{value}'),"

    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            cmd[:-1]
        )
        conn.commit()
        return {"status": "secret added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Insert for secrets) - " + str(e))
    

@app.get("/api/deploy")
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
            "SELECT name, build_cmd, run_cmd FROM Repos WHERE id = %s",
            (str(repo_id),)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Repo not found")
        repo_name, build, run = result
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
    cursor.execute(
        "SELECT S.instance_id, I.host, S.port FROM Slots S JOIN Instances I ON S.instance_id = I.id WHERE S.occupied = false ORDER BY S.created_at LIMIT 1"
    )
    slot = cursor.fetchone()
    if not slot:
        ec2_res = create_ec2()
        instance_id = ec2_res["instance_id"]
        host = ec2_res["host"]
        port = 3000
    else:
        instance_id, host, port = slot
        cursor.execute(
            "UPDATE Slots SET occupied = true WHERE instance_id = %s AND port = %s",
            (instance_id, port)
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
                "yum update -y",
                "yum install -y git python3 python3-pip",

                "cd /home/ec2-user",

                f"rm -rf {repo_name.split('/')[-1] + str(port)}",

                f"git clone {clone_url} {repo_name.split('/')[-1] + str(port)}",

                f"cd /home/ec2-user/{repo_name.split('/')[-1] + str(port)}",

                "python3 -m venv venv",

                "source venv/bin/activate",

                f"{build} > app.log 2>&1",

                f"export PORT={port}",

                env_vars,

                f"nohup sh -c 'source venv/bin/activate && {run}' > app.log 2>&1 & echo $! > app.pid\n"

                #"echo $! > app.pid"
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    print(output)
    url = f"http://{host}:{port}"
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Deployments (repo_id, instance_id, link, status) VALUES (%s, %s, %s, %s) RETURNING id",
        (str(repo_id), instance_id, url, "deploy started")
    )
    conn.commit()
    conn.close()
    return {
        "status": "deploy started",
        "url": url,
        "deployment_id": cursor.lastrowid
    }


@app.get("/api/rollback")
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
        cursor.execute(
            "SELECT D.instance_id, R.name, D.link FROM Deployments D JOIN Repos R ON D.repo_id = R.id WHERE D.id = %s",
            (deployment_id,)
        )
        result = cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in rollback) - " + str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    instance_id = result[0]
    repo_name = result[1].split("/")[-1]
    port = result[2].split(":")[-1]
    dir_name = repo_name + port
    print(instance_id)
    print(repo_name)
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                f"cd /home/ec2-user/{dir_name}",
                "kill $(cat app.pid)"
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    time2.sleep(3)
    print("Command sent:", command_id)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    conn = connect_db()
    cursor = conn.cursor()
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


@app.get("/api/logs")
def get_logs(
    deployment_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in get logs)")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT D.instance_id, R.name, D.link FROM Deployments D JOIN Repos R ON D.repo_id = R.id WHERE D.id = %s",
            (deployment_id,)
        )
        result = cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in get logs) - " + str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Deployment not found")
    instance_id = result[0]
    repo_name = result[1].split("/")[-1]
    port = result[2].split(":")[-1]
    dir_name = repo_name + port
    print(instance_id)
    print(repo_name)
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                f"cd /home/ec2-user/{dir_name}",
                "tail -n 10 app.log"
            ]
        }
    )
    command_id = response["Command"]["CommandId"]
    time2.sleep(3)
    print("Command sent:", command_id)
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )
    print(output["StandardOutputContent"])
    return {
        "logs": output["StandardOutputContent"]
    }


@app.get("/api/deployments")
async def list_deployments(
    repo_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Connection in list deployments)")
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, link, status FROM Deployments WHERE repo_id = %s",
            (repo_id,)
        )
        deployments = cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in list deployments) - " + str(e))
    return [{"id": d[0], "link": d[1], "status": d[2]} for d in deployments]


@app.post("/api/send-logs")
def send_logs(
    deployment_id: str,
    logs: str
):
    logger.error(logs)
    return {"status": "logs received"}
    


@app.get("/api/create-ec2")
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
            "INSERT INTO Slots (instance_id, port, occupied) VALUES (%s, %s, %s), (%s, %s, %s), (%s, %s, %s), (%s, %s, %s), (%s, %s, %s)",
            (instance_id, 3000, True, instance_id, 3001, False, instance_id,
              3002, False, instance_id, 3003, False, instance_id, 3004, False
            )
        )
        conn.commit()
        conn.close()
        return {"instance_id": instance_id, "host": host}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (EC2 Creation) - " + str(e))
