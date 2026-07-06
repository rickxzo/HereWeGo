from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID
from auth import get_current_user
from db import connect_db

router = APIRouter()

@router.post('/api/add-secrets')
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
        conn.close()
        return {"status": "secret added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Insert for secrets) - " + str(e))
