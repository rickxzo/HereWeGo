from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import urllib.parse
import httpx
from jose import jwt
from datetime import datetime, timedelta
from db import connect_db
import logging

from routes import functions, create_function, deployments, github_repos, repos, create_repo, delete_repo, logs, add_secrets, deploy, rollback

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://herewego-fv2-1.onrender.com",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(functions.router)
app.include_router(create_function.router)
app.include_router(deployments.router)
app.include_router(repos.router)
app.include_router(create_repo.router)
app.include_router(delete_repo.router)
app.include_router(github_repos.router)
app.include_router(logs.router)
app.include_router(add_secrets.router)
app.include_router(deploy.router)
app.include_router(rollback.router)

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
        '''
        cursor.execute(
            """
            INSERT INTO users (github_id, username, avatar, access_token)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_data["id"], user_data["login"], user_data["avatar_url"], access_token)
        )
        '''
        cursor.execute(
            """
            INSERT INTO users (github_id, access_token)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (user_data["id"], access_token)
        )
        user_id = cursor.fetchone()[0]

    conn.commit()
    cursor.close()
    conn.close()

    jwt_token = create_access_token({"user_id": str(user_id)})

    frontend_url = "https://herewego-fv2-1.onrender.com/auth"

    params = urllib.parse.urlencode({
        "token": jwt_token,
        "id": user_id,
        "username": user_data["login"],
        "avatar": user_data["avatar_url"]
    })

    return RedirectResponse(f"{frontend_url}?{params}")
