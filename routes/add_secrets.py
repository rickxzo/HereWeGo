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
        raise HTTPException(status_code=400, detail="Invalid Request Body.")
    content = body.decode("utf-8").splitlines()
    secrets = {}
    try:
        for line in content:
            if "=" in line:
                name, value = line.split("=", 1)
                secrets[name.strip()] = value.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Secrets parsing error")

    rows = [
        (str(repo_id), name, value)
        for name, value in secrets.items()
    ]

    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id
            FROM Repositories
            WHERE repo_id = %s
            """,
            (str(repo_id),)
        )
        
        repo = cursor.fetchone()
        
        if repo is None:
            raise HTTPException(404, "Repository not found")
        
        if repo[0] != user_id:
            raise HTTPException(403, "You do not own this repository")
            
        cursor.execute(
            "DELETE FROM Secrets WHERE repo_id = %s",
            (str(repo_id),)
        )
        cursor.executemany(
            """
            INSERT INTO Secrets (repo_id, name, value)
            VALUES (%s, %s, %s)
            """,
            rows
        )
        conn.commit()
        return {"status": "secret added"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="DB error."
        )
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
