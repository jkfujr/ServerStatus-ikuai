# ikuai_login.py

import hashlib
import base64
import requests

# 密码处理
def process_password(password):
    md5_hash = hashlib.md5(password.encode('utf-8')).hexdigest()
    salted_password = "salt_11" + password
    base64_encoded = base64.b64encode(salted_password.encode('utf-8')).decode('utf-8')
    
    return md5_hash, base64_encoded

# 登录请求
def get_sess_key(username, password, ikuai_url):
    md5_hash, base64_encoded = process_password(password)
    
    url = f"{ikuai_url}/Action/login"
    
    payload = {
        "username": username,
        "passwd": md5_hash,
        "pass": base64_encoded,
        "remember_password": "true"
    }
    
    response = requests.post(url, json=payload)

    if response.status_code == 200 and 'Set-Cookie' in response.headers:
        set_cookie = response.headers['Set-Cookie']
        sess_key = set_cookie.split('sess_key=')[1].split(';')[0]
        return sess_key
    else:
        raise Exception("Failed to obtain sess_key")
