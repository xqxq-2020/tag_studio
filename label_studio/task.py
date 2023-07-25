import json
import base64
import uvicorn
import requests
from urllib import parse
from fastapi import FastAPI
from datetime import datetime

app = FastAPI()
headers = {"Content-Type": "application/x-www-form-urlencoded"}
url = "http://192.168.1.20:8190/realms/didaima/protocol/openid-connect/token"


def decode_token(token):
    try:
        # 将token按照"."进行分割
        parts = token.split('.')
        # 获取payload部分（第二部分）并解码
        payload = base64.b64decode(parts[1] + '=' * (-len(parts[1]) % 4)).decode('utf-8')
        # 将payload部分解析为JSON格式
        payload_data = json.loads(payload)

        # 获取token过期时间，如果没有过期时间则默认为当前时间
        if 'exp' in payload_data:
            expiration = datetime.fromtimestamp(payload_data['exp'])
        else:
            expiration = datetime.now()

        # 获取当前时间
        now = datetime.now()

        # 如果token已过期，则抛出异常
        if expiration < now:
            raise Exception('Token has expired')

        # 获取token签发时间，如果没有签发时间则默认为当前时间
        if 'iat' in payload_data:
            issued_at = datetime.fromtimestamp(payload_data['iat'])
        else:
            issued_at = datetime.now()

        # 计算token已经存在的时间
        token_lifetime = now - issued_at

        # 返回解码后的payload和token存在时间
        return payload_data, token_lifetime.total_seconds()
    except (IndexError, TypeError, KeyError, ValueError):
        # 如果解码失败或者解析JSON失败，则抛出异常
        raise Exception('Invalid token')


@app.get('/get_token', summary="获取token及对应解析用户详情")
async def get_token_user(username: str, password: int):
    data = {
        "username": username,
        "password": password,
        "client_id": "jwtClient",
        "client_secret": "lVAaYQbqkMUciBrE3igAnHi9QB7SIb45",
        "grant_type": "password"
    }
    try:
        response = requests.post(url, timeout=3, headers=headers, data=parse.urlencode(data))
        result = eval(response.text)["access_token"]
        user_info = decode_token(result)[0]["sub"]
        return {"code": 1000, "msg": "已获取到token及对应解析用户详情",
                "data": {"token": result, "user_info": user_info}}
    except Exception as err:
        return {"code": 1001, "msg": str(err) + eval(response.text)["error"],
                "data": eval(response.text)["error_description"]}


@app.get('/get_user', summary="根据token解析用户详情")
async def get_token_user(refresh_token: str):
    access_token = get_access_token(refresh_token)
    user_url = 'http://192.168.1.20:8190/realms/didaima/protocol/openid-connect/userinfo'
    user_headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(user_url, headers=user_headers)
    if response.status_code == 200:
        user_info = response.json()
        return user_info
    else:
        result = 'Token令牌已失效！'
        return {'status': -1, 'result': result}


def get_access_token(refresh_token: str):
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": "front-task"
    }
    response = requests.post(url, timeout=3, headers=headers, data=parse.urlencode(data))
    try:
        result = eval(response.text)["access_token"]
        return result
    except Exception as err:
        return {"code": 1001, "msg": str(err) + eval(response.text)["error"],
                "data": eval(response.text)["error_description"]}


if __name__ == "__main__":
    uvicorn.run("task:app", host="0.0.0.0", port=8190)
