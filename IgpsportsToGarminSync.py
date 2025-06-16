import base64
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import json
import garth
import hashlib
import base64
import os.path
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import zipfile
from garth.http import Client

def encrpt(password, public_key):
    rsa = RSA.importKey(public_key)
    cipher = PKCS1_v1_5.new(rsa)
    return base64.b64encode(cipher.encrypt(password.encode())).decode()


def syncData(username, password, garmin_email=None, garmin_password=None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        "Accept-Encoding": "gzip, deflate",
    }

    igp_host = "my.igpsport.com"
    if os.getenv("IGPSPORT_REGION") == "global":
        igp_host = "i.igpsport.com"

    session = requests.session()

    # login account
    print("同步IGP数据")

    url = "https://%s/Auth/Login" % igp_host
    data = {
        'username': username,
        'password': password,
    }
    res = session.post(url, data, headers=headers)

    # get igpsport list
    url = "https://%s/Activity/ActivityList" % igp_host
    res = session.get(url)
    result = json.loads(res.text, strict=False)

    activities = result["item"]

    global_garth = Client()
    try:
        global_garth.login(garmin_email, garmin_password)
        print("")
    except Exception as e:
        print("登录态失败")
        print(e)
        return False

    global_activities = global_garth.connectapi(
        f"/activitylist-service/activities/search/activities",
        params={"activityType": "cycling", "limit": 10, "start": 0, 'excludeChildren': False},
        # 这里是跑步数据 骑行数据可修改成cycling
    )
    sync_data = []
    # get not upload activity
    timezone = ZoneInfo('Asia/Shanghai')  # to Shanghai timezero in Gtihub Action env
    for activity in activities:
        dt = datetime.strptime(activity["StartTime"], "%Y-%m-%d %H:%M:%S")
        mk_time = dt.strftime("%Y-%m-%d %H:%M")


        need_sync = True
        for item in global_activities:
            dt = datetime.strptime(item["startTimeLocal"],"%Y-%m-%d %H:%M:%S")
            ger_mk_timed = dt.strftime("%Y-%m-%d %H:%M")
            if ger_mk_timed == mk_time:
                need_sync = False
                break
        if need_sync:
            sync_data.append(activity)
    if len(sync_data) == 0:
        print("nothing data need sync")

    else:
        # down file
        for sync_item in sync_data:
            rid = sync_item["RideId"]
            dt = datetime.strptime(sync_item["StartTime"], "%Y-%m-%d %H:%M:%S")
            start_time_str = dt.strftime("%Y-%m-%d-%H-%M")
            rid = str(rid)
            fit_url = "https://%s/fit/activity?type=0&rideid=%s" % (igp_host, rid)
            res = session.get(fit_url)
            upload_file_name = "rid-" + rid +"-"+start_time_str +".fit"
            print("sync upload_file_name:" + upload_file_name)
            with open(upload_file_name, "wb") as file2:
                file2.write(res.content)
            with open(upload_file_name, 'rb') as fd:
                uploaded = requests.post('https://connectapi.garmin.com/upload-service/upload',
                                         files={'file': fd},
                                         headers={'authorization': global_garth.oauth2_token.__str__()})
                # uploaded = global_garth.upload(fd)
                print(uploaded.content)

# USERNAME/PASSWORD配置IGPSports的账号  GARMIN_EMAIL/GARMIN_PASSWORD配置Garmin国际区的账号
activity = syncData(os.getenv("USERNAME"), os.getenv("PASSWORD"), os.getenv("GARMIN_EMAIL"), os.getenv("GARMIN_PASSWORD"))
