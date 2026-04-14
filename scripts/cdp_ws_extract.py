"""通过CDP WebSocket直接连接已有Yupoo分类页, 提取gallery链接"""

import json
import time
import threading
import websocket

PAGE_ID = "6789C20AB90AD80E80AF7ADE544AFD3E"
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
    print("WS Opened!")

    # 1. 启用Runtime
    send_cmd(ws, "Runtime.enable")
    time.sleep(0.3)

    # 2. 提取gallery链接
    send_cmd(
        ws,
        "Runtime.evaluate",
        {
            "expression": """
        JSON.stringify({
            title: document.title,
            links: Array.from(document.querySelectorAll('a[href*="/gallery/"]')).map(a => {
                const parts = a.href.split('/gallery/');
                const id = parts.length > 1 ? parts[1].split('?')[0] : '';
                return {id, href: a.href, text: a.innerText.trim().slice(0, 50)};
            }).filter(x => x.id && x.id.length >= 8).slice(0, 20)
        })
        """,
            "returnByValue": True,
        },
    )
    response_event.wait(timeout=5)

    resp = response_map.get(2, {})
    if "result" in resp:
        try:
            data = json.loads(resp["result"]["value"])
            print(f"\nPage title: {data.get('title')}")
            print(f"\n找到 {len(data.get('links', []))} 个gallery链接:")
            for link in data.get("links", []):
                print(f"  ID: {link['id']}  Text: {link['text'][:30]}")
        except Exception as e:
            print(f"Parse error: {e}")
            print(f"Raw: {resp}")
    else:
        print(f"No result: {resp}")

    # 关闭
    time.sleep(0.5)
    ws.close()


def main():
    print(f"Connecting to: {WS_URL}")
    ws = websocket.WebSocketApp(
        WS_URL, on_message=on_message, on_error=on_error, on_close=on_close
    )
    ws.on_open = on_open

    thread = threading.Thread(target=ws.run_forever)
    thread.daemon = True
    thread.start()
    thread.join(timeout=10)

    print("Done")


if __name__ == "__main__":
    main()
