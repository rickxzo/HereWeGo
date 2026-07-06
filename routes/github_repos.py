from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db
import requests

router = APIRouter()


@router.get("/api/github-repos")
def get_github_repos(user_id: str = Depends(get_current_user)):
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT access_token FROM users WHERE id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail="DB connection error.")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    github_token = result[0]
    if not github_token:
        raise HTTPException(
            status_code=400,
            detail="GitHub account not connected"
        )
        
    try:
        res = requests.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {github_token}"},
            params={
                "per_page": 150,
                "page": 1
            },
            timeout=10
        )
        if res.status_code == 401:
            raise HTTPException(
                status_code=400,
                detail="GitHub account needs to be reconnected"
            )
        res.raise_for_status()
    except requests.RequestException:
        raise HTTPException(
            status_code=502,
            detail="GitHub API error"
        )

    repos = [
        {   
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"]
        }
        for repo in res.json()
    ]
    return repos
