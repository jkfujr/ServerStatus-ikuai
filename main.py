import time,socket,json,requests

from ikuai_login import get_sess_key

# 爱快设置
IKUAI_URL = ""
IKUAI_USER = ""
IKUAI_PASSWORD = ""

# SERVER_STATUS 服务器配置
SERVER_STATUS_SERVER = ""
SERVER_STATUS_PORT = 35601
SERVER_STATUS_USER = ""
SERVER_STATUS_PASSWORD = ""
# 更新间隔(s)
SERVER_STATUS_INTERVAL = 1

# 系统状态请求间隔(s)
IKUAI_STATUS_INTERVAL = 3
# 接口数据请求间隔(s)
IKUAI_IFACE_INTERVAL = 3
# 硬盘数据请求间隔(s)
IKUAI_DISK_INTERVAL = 3600

# 登录并获取 sess_key
def get_new_sess_key():
    return get_sess_key(IKUAI_USER, IKUAI_PASSWORD, IKUAI_URL)

sess_key = get_new_sess_key()

# 请求URL
url = f"{IKUAI_URL}/Action/call"
headers = {
    "Cookie": f"sess_key={sess_key}",
}

# 系统状态
def get_system_status():
    data = {
        "func_name": "homepage",
        "action": "show",
        "param": {
            "TYPE": "sysstat"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 接口流量
def get_iface_stream():
    data = {
        "func_name": "monitor_iface",
        "action": "show",
        "param": {
            "TYPE": "iface_stream"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# 硬盘状态
def get_disk_status():
    data = {
        "func_name": "disk_mgmt",
        "action": "show",
        "param": {
            "TYPE": "data"
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# token失效处理
def handle_request_with_auth(func):
    global sess_key
    global headers
    
    response = func()
    
    if response.get('Result') == 10014:
        print("sess_key 失效，重新登录获取...")
        sess_key = get_new_sess_key()
        headers["Cookie"] = f"sess_key={sess_key}"
        response = func()
    
    return response

if __name__ == '__main__':
    socket.setdefaulttimeout(30)
    
    # 计时器
    status_timer = 0
    iface_timer = 0
    disk_timer = 0
    
    while True:
        try:
            print('Connecting...')
            s = socket.create_connection((SERVER_STATUS_SERVER, SERVER_STATUS_PORT))
            data = s.recv(1024).decode()
            if data.find('Authentication required') > -1:
                s.send((SERVER_STATUS_USER + ':' + SERVER_STATUS_PASSWORD + '\n').encode('utf-8'))
                data = s.recv(1024).decode()
                if data.find('Authentication successful') < 0:
                    print(data)
                    raise socket.error
            else:
                print(data)
                raise socket.error

            print(data)
            if data.find('You are connecting via') < 0:
                data = s.recv(1024).decode()
                print(data)

            while True:
                array = {}

                # 系统状态请求
                if status_timer <= 0:
                    sys_status = handle_request_with_auth(get_system_status)
                    cpu_percentages = sys_status['Data']['sysstat']['cpu']
                    num_cores = len(cpu_percentages) - 1
                    CPU = float(cpu_percentages[-1].replace('%', ''))
                    Uptime = sys_status['Data']['sysstat']['uptime']
                    MemoryTotal = sys_status['Data']['sysstat']['memory']['total']
                    MemoryUsed = MemoryTotal - sys_status['Data']['sysstat']['memory']['available']
                    array['uptime'] = Uptime
                    array['cpu'] = CPU
                    array['memory_total'] = MemoryTotal
                    array['memory_used'] = MemoryUsed
                    array['load'] = CPU
                    array['num_cores'] = num_cores
                    status_timer = IKUAI_STATUS_INTERVAL

                # 接口流量请求
                if iface_timer <= 0:
                    iface_stream = handle_request_with_auth(get_iface_stream)
                    wan1_data = next(iface for iface in iface_stream['Data']['iface_stream'] if iface['interface'] == 'wan1')
                    NetRx = wan1_data['upload']
                    NetTx = wan1_data['download']
                    NET_IN = wan1_data['total_up']
                    NET_OUT = wan1_data['total_down']
                    array['network_rx'] = NetRx
                    array['network_tx'] = NetTx
                    array['network_in'] = NET_IN
                    array['network_out'] = NET_OUT
                    iface_timer = IKUAI_IFACE_INTERVAL

                # 硬盘状态请求
                if disk_timer <= 0:
                    disk_status = handle_request_with_auth(get_disk_status)
                    HDDTotal = disk_status['Data']['data'][0]['partition'][1]['mounted']['mt_total']
                    HDDUsed = disk_status['Data']['data'][0]['partition'][1]['mounted']['mt_used']
                    HDDTotal_MiB = int(HDDTotal) // (1024 * 1024)
                    HDDUsed_MiB = int(HDDUsed) // (1024 * 1024)
                    array['hdd_total'] = HDDTotal_MiB
                    array['hdd_used'] = HDDUsed_MiB
                    disk_timer = IKUAI_DISK_INTERVAL

                # 数据推送
                s.send(("update " + json.dumps(array) + '\n').encode('utf-8'))

                status_timer -= SERVER_STATUS_INTERVAL
                iface_timer -= SERVER_STATUS_INTERVAL
                disk_timer -= SERVER_STATUS_INTERVAL

                time.sleep(SERVER_STATUS_INTERVAL)

        except KeyboardInterrupt:
            raise
        except socket.error:
            print('Disconnected...')
            # 错误断开重连
            if 's' in locals().keys():
                del s
            time.sleep(3)
        except Exception as e:
            print('Caught Exception:', e)
            if 's' in locals().keys():
                del s
            time.sleep(3)