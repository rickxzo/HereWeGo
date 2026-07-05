from fastapi import APIRouter, Depends
from auth import get_current_user
from db import connect_db

router = APIRouter()

@router.get("/api/deployments")
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
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Query in list deployments) - " + str(e))
    return [{"id": d[0], "link": d[1], "status": d[2]} for d in deployments]
