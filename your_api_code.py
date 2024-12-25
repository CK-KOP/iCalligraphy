import base64
import datetime
import hashlib
import hmac
import json
from time import mktime
from urllib.parse import urlencode, urlparse
import websocket
import ssl
import _thread as thread
from wsgiref.handlers import format_date_time

class Ws_Param(object):
    def __init__(self, APPID, APIKey, APISecret, imageunderstanding_url):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.host = urlparse(imageunderstanding_url).netloc
        self.path = urlparse(imageunderstanding_url).path
        self.ImageUnderstanding_url = imageunderstanding_url

    def create_url(self):
        now = datetime.datetime.now()
        date = format_date_time(mktime(now.timetuple()))  # 使用 format_date_time 格式化时间戳

        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        signature_sha = hmac.new(self.APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                     hashlib.sha256).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = (
            f'api_key="{self.APIKey}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_sha_base64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        return f"{self.ImageUnderstanding_url}?{urlencode({'authorization': authorization, 'date': date, 'host': self.host})}"

answer = ""

def on_message(ws, message):
    global answer
    print("Received message:", message)  # 调试信息，打印接收到的消息
    try:
        data = json.loads(message)
        code = data['header']['code']
        if code != 0:
            print(f"请求错误: {code}, {data}")
            ws.close()
        else:
            content = data["payload"]["choices"]["text"][0]["content"]
            answer += content
            if data["payload"]["choices"]["status"] == 2:
                ws.close()
    except Exception as e:
        print("Error in on_message:", e)
        ws.close()


def on_error(ws, error):
    print("### error:", error)


def on_close(ws, *args):
    print("### closed")


def on_open(ws):
    thread.start_new_thread(run, (ws,))


def run(ws, *args):
    data = json.dumps(gen_params(ws.appid, ws.question))
    ws.send(data)


def gen_params(appid, question):
    return {
        "header": {"app_id": appid},
        "parameter": {
            "chat": {
                "domain": "image",
                "temperature": 0.5,
                "top_k": 4,
                "max_tokens": 2048,
                "auditing": "default",
            }
        },
        "payload": {"message": {"text": question}},
    }


def main(appid, api_key, api_secret, imageunderstanding_url, question, callback):
    ws_param = Ws_Param(appid, api_key, api_secret, imageunderstanding_url)
    ws_url = ws_param.create_url()

    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=lambda ws, msg: callback(ws, msg),
        on_error=on_error,
        on_close=on_close,
        on_open=on_open,
    )
    ws.appid = appid
    ws.question = question

    # 直接运行 WebSocket
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})