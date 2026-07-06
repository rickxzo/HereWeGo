from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db

router = APIRouter()

@router.get("/api/repos")
def list_repos(user_id: str = Depends(get_current_user)):
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT ON (R.id) R.id, R.user_id, R.name, R.build_cmd, R.run_cmd, R.domain, D.id, D.status, S.port, I.host 
            FROM Repos R LEFT JOIN Deployments D ON R.id = D.repo_id 
            LEFT JOIN Slots S ON D.slot_id = S.id 
            LEFT JOIN Instances I ON S.instance_id = I.id
            WHERE R.user_id = %s
            ORDER BY R.id, D.last_modified DESC
            """,
            (user_id,)
        )
        projects = cursor.fetchall()
        return [{"id": p[0], "name": p[2], "build_cmd": p[3], "run_cmd": p[4], "status": p[7], "deploy_id": p[6], "link": f"https://{p[5]}.herewego.website", "url": f"http://{p[9]}:{p[8]}"} for p in projects]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error (DB Query) - {str(e)}")
    finally:
        if conn:
            conn.close()
