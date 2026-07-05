from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db

router = APIRouter()


@router.get("/api/delete-repo")
def delete_repo(
    repo_id: str,
    user_id: str = Depends(get_current_user)
):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Secrets WHERE repo_id = %s", (repo_id,))
        cursor.execute("DELETE FROM Deployments WHERE repo_id = %s", (repo_id,))
        cursor.execute(
            "DELETE FROM Repos WHERE id = %s",
            (repo_id,)
        )
        conn.commit()
        conn.close()
        return {"status": "repo deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error (DB Delete for repo) - " + str(e))
