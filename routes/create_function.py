from fastapi import APIRouter, Depends
from auth import get_current_user
from db import connect_db
import io
import boto3
import zipfile
import time
lambda_client = boto3.client("lambda", region_name="us-east-1")
ROLE_ARN = "arn:aws:iam::113831246595:role/HereWeGo-Lambda"

router = APIRouter()


@router.get("/api/create-function")
async def create_function(
    code: str,
    name: str,
    language: str,
    user_id: str = Depends(get_current_user)
):

    if "main" not in code:
        return {"error": "function header main() has to be present."}

    langs = {
        "Python 3.10": {
            "runtime": "python3.10",
            "filename": "lambda.py",
            "handler": "lambda.main"
        },
        "Python 3.11": {
            "runtime": "python3.11",
            "filename": "lambda.py",
            "handler": "lambda.main"
        },
        "Python 3.12": {
            "runtime": "python3.12",
            "filename": "lambda.py",
            "handler": "lambda.main"
        },
        "Python 3.13": {
            "runtime": "python3.13",
            "filename": "lambda.py",
            "handler": "lambda.main"
        },
        "Python 3.14": {
            "runtime": "python3.14",
            "filename": "lambda.py",
            "handler": "lambda.main"
        },
    
        "Node.js 22.x": {
            "runtime": "nodejs22.x",
            "filename": "index.js",
            "handler": "index.main"
        },
        "Node.js 24.x": {
            "runtime": "nodejs24.x",
            "filename": "index.js",
            "handler": "index.main"
        },
    
        "Java 11": {
            "runtime": "java11",
            "filename": "Main.java",
            "handler": "Main::main"
        },
        "Java 17": {
            "runtime": "java17",
            "filename": "Main.java",
            "handler": "Main::main"
        },
        "Java 21": {
            "runtime": "java21",
            "filename": "Main.java",
            "handler": "Main::main"
        },
        "Java 25": {
            "runtime": "java25",
            "filename": "Main.java",
            "handler": "Main::main"
        },
    
        "Ruby 3.3": {
            "runtime": "ruby3.3",
            "filename": "lambda.rb",
            "handler": "lambda.main"
        },
        "Ruby 3.4": {
            "runtime": "ruby3.4",
            "filename": "lambda.rb",
            "handler": "lambda.main"
        },
        "Ruby 4.0": {
            "runtime": "ruby4.0",
            "filename": "lambda.rb",
            "handler": "lambda.main"
        },
    
    }

    details = langs[language]
    
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(details["filename"], code)

    zip_bytes = zip_buffer.getvalue()

    response = lambda_client.create_function(
        FunctionName=str(user_id)+name,
        Runtime=details["runtime"],
        Role=ROLE_ARN,
        Handler=details["handler"],
        Code={"ZipFile": zip_bytes},
        Timeout=30,
        MemorySize=128,
        Publish=True,
    )

    arn = response["FunctionArn"]
    while True:
        config = lambda_client.get_function(
            FunctionName=arn
        )["Configuration"]

        state = config["State"]

        if state == "Active":
            break

        if state == "Failed":
            raise Exception("Lambda deployment failed")

        time.sleep(2)
    try:
        url_response = lambda_client.create_function_url_config(
            FunctionName=arn,
            AuthType="NONE"
        )

        url = url_response["FunctionUrl"]

        lambda_client.add_permission(
            FunctionName=arn,
            StatementId="FunctionURLAllowPublicAccess",
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE"
        )

        lambda_client.add_permission(
            FunctionName=arn,
            StatementId="FunctionURLAllowPublicInvoke",
            Action="lambda:InvokeFunction",
            Principal="*"
        )
    except lambda_client.exceptions.ResourceConflictException:
        url = lambda_client.get_function_url_config(
            FunctionName=arn
        )["FunctionUrl"]

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO Functions VALUES (%s, %s, %s, %s, %s, %s)", (user_id, arn, url, name, code, language)
    )
    conn.commit()
    conn.close()
    return {
        "arn": arn,
        "url": url
    }
