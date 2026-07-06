from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import connect_db

router = APIRouter()


@router.get("/api/functions")
def list_functions(
    user_id: str = Depends(get_current_user)
):
    conn = None
    cursor = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name, url, code, language FROM Functions WHERE user_id = %s", (user_id,))
        functions = cursor.fetchall()
        return [
            {'name': function[0], 'url': function[1], 'code': function[2], 'language': function[3]} for function in functions 
        ] 
    except Exception as e:
        raise HTTPException(status_code=500, detail = "Function fetching error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
