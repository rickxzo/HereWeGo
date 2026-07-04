from fastapi import APIRouter, Depends
from auth import get_current_user
from db import connect_db

router = APIRouter()


@router.get("/api/functions")
async def list_functions(
    user_id: str = Depends(get_current_user)
):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, url, code, language FROM Functions WHERE user_id = %s", (user_id,))
    functions = cursor.fetchall()
    conn.close()
    return [
        {'name': function[0], 'url': function[1], 'code': function[2], 'language': function[3]} for function in functions 
    ] 
