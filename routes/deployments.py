from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db

router = APIRouter()

@router.get("/api/deployments")
def list_deployments(
    repo_id: str,
    user_id: str = Depends(get_current_user)
):
    conn = None
    cursor = None

    try:
        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, link, status FROM Deployments WHERE repo_id = %s",
            (repo_id,)
        )

        deployments = cursor.fetchall()

        return [
            {
                "id": d[0],
                "link": d[1],
                "status": d[2]
            }
            for d in deployments
        ]

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal server error (list deployments)"
        )

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
