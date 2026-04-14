"""从已有Chrome CDP page导出storage_state, 用于已登录会话"""

import json
import time
import threading
import websocket

PAGE_ID = "6789C20AB90AD80E80AF7ADE544AFD3E"  # Yupoo分类页
WS_URL = f"ws://localhost:9222/devtools/page/{PAGE_ID}"

response_event = threading.Event()
response_map = {}
msg_id = 0


def send_cmd(ws, method, params=None):
    global msg_id
    msg_id += 1
    cmd = {"id": msg_id, "method": method, "params": params or {}}
    ws.send(json.dumps(cmd))
    return msg_id


def on_message(ws, message):
    global response_map
    data = json.loads(message)
    response_map[data.get("id")] = data
    response_event.set()


def on_error(ws, error):
    print(f"WS Error: {error}")


def on_close(ws, *args):
    print("WS Closed")


def on_open(ws):
    global response_event, response_map

    print("WS Opened!")
    send_cmd(ws, "Page.enable")
    send_cmd(ws, "Storage.enable")
    time.sleep(0.5)

    # 尝试获取cookies
    send_cmd(ws, "Network.getAllCookies")
    response_event.wait(timeout=5)

    resp = response_map.get(2, {})
    print(f"Cookies response: {json.dumps(resp, indent=2, ensure_ascii=False)[:1000]}")

    # 尝试用Runtime.evaluate获取localStorage
    send_cmd(
        ws,
        "Runtime.evaluate",
        {
            "expression": """
        JSON.stringify({
            localStorage: Object.fromEntries(
                Object.entries(localStorage).slice(0, 20)
            ),
            sessionStorage: Object.fromEntries(
                Object.entries(sessionStorage).slice(0, 20)
            ),
            document.cookie: document.cookie.slice(0, 500)
        })
        """,
            "returnByValue": True,
        },
    )
    response_event.wait(timeout=5)

    resp2 = response_map.get(3, {})
    print(
        f"\nStorage response: {json.dumps(resp2, indent=2, ensure_ascii=False)[:2000]}"
    )

    time.sleep(0.3)
    ws.close()


def main():
    print(f"Connecting to Yupoo page via WS: {WS_URL}")
    ws = websocket.WebSocketApp(
        WS_URL, on_message=on_message, on_error=on_error, on_close=on_close
    )
    ws.on_open = on_open

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()
    thread.join(timeout=15)

    print("Done")


if __name__ == "__main__":
    main()
