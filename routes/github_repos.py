from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db
import requests

router = APIRouter()


@router.get("/api/github-repos")
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
            headers={"Authorization": f"Bearer {github_token}"},
            params={
                "per_page": 100,
                "page": 1
            }
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
