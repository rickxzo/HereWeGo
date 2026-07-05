from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db

router = APIRouter()

@router.get("/api/create-repo")
def create_repo(
    repo_name: str,
    build: str,
    run: str,
    domain: str,
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
            INSERT INTO Repos (user_id, name, build_cmd, run_cmd, domain)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (user_id, repo_name, build, run, domain)
        )
        repo_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        return {"repo_id": repo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error (DB Insert for repo) {str(e)}")
