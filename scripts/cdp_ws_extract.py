#!/usr/bin/env python3
"""通过CDP WebSocket直接连接已有Yupoo页面, 提取相册图片URL"""
import json
import time
import threading
import websocket

ALBUMS = [
    {'album_id': '232960495', 'title': 'h150 BAPE/猿人头 26ss经典菱格老花印花短袖T恤。'},
    {'album_id': '230251075', 'title': 'H110 1002 BAPE经典前后猿人头印花T恤 M-3XL'},
    {'album_id': '230251057', 'title': 'H120 8002 蓝&粉&绿 M-3XL'},
    {'album_id': '230251022', 'title': 'H120 8003 蓝&黄&紫&绿&红 M-3XL'},
    {'album_id': '230251020', 'title': 'H120 8008 黑 M-3XL'},
    {'album_id': '230251011', 'title': 'H120 8007 黑 M-3XL'},
    {'album_id': '230251004', 'title': 'H110 1003 黑绿&白绿&黑黄&白黄 M-3XL'},
]

OUTPUT_FILE = "C:/Users/Administrator/Documents/GitHub/ERP/logs/re_extract_cdp.json"
# 使用首页tab的WS URL - 这是已登录的tab
HOME_TAB_WS = "ws://localhost:9222/devtools/page/1FF6EDAC23C8BF8F14593873E58E3F83"

class CDPClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, suppress_origin=True)
        self.msg_id = 0
        self._event = threading.Event()
        self._responses = {}
        self._running = True
        self._thread = threading.Thread(target=self._reader)
        self._thread.daemon = True
        self._thread.start()
        time.sleep(0.5)  # 等待连接稳定

    def _reader(self):
        while self._running:
            try:
                msg = self.ws.recv()
                data = json.loads(msg)
                if data.get('id') in self._responses:
                    self._responses[data['id']] = data
                    self._event.set()
            except Exception as e:
                if self._running:
                    print(f'Reader error: {e}')
                break

    def send(self, method, params=None, timeout=10):
        self.msg_id += 1
        msg = {'id': self.msg_id, 'method': method}
        if params:
            msg['params'] = params
        self.ws.send(json.dumps(msg))
        return self.msg_id

    def recv(self, timeout=15):
        self._event.clear()
        start = time.time()
        while time.time() - start < timeout:
            if self._event.wait(0.1):
                self._event.clear()
                for mid, resp in list(self._responses.items()):
                    del self._responses[mid]
                    return resp
        return None

    def cmd(self, method, params=None, timeout=15):
        mid = self.send(method, params)
        resp = self.recv(timeout)
        if resp is None:
            raise Exception(f'Timeout waiting for {method}')
        if 'error' in resp:
            raise Exception(f"CDP error: {resp['error']}")
        return resp.get('result', {})

    def close(self):
        self._running = False
        try:
            self.ws.close()
        except:
            pass

def extract_album(client, album_id, title):
    """创建新tab访问相册，提取图片"""
    photos = []

    # 1. 创建新target (新tab)
    print(f"    创建新tab...")
    result = client.cmd('Target.createTarget', {
        'url': f'https://lol2024.x.yupoo.com/albums/{album_id}',
        'browserContextId': None,
    })
    new_target_id = result.get('targetId', '')
    print(f"    新target: {new_target_id}")
    if not new_target_id:
        return {'album_id': album_id, 'title': title, 'photo_count': 0, 'photos': [], 'error': 'no targetId'}

    # 2. 等待tab创建
    time.sleep(1)

    # 3. 找到新tab的WS URL
    import urllib.request
    targets = json.loads(urllib.request.urlopen('http://localhost:9222/json').read())
    new_ws = None
    for t in targets:
        if t.get('id') == new_target_id:
            new_ws = t.get('webSocketDebuggerUrl')
            break
    if not new_ws:
        return {'album_id': album_id, 'title': title, 'photo_count': 0, 'photos': [], 'error': 'no WS URL'}

    # 4. 连接到新tab
    print(f"    连接到新tab...")
    new_client = CDPClient(new_ws)

    # 5. 启用Page和Network
    try:
        new_client.cmd('Page.enable')
        new_client.cmd('Network.enable')
    except Exception as e:
        print(f"    启用失败: {e}")

    # 6. 等待内容加载
    print(f"    等待页面加载...")
    time.sleep(8)

    # 7. 提取DOM中的图片
    print(f"    提取DOM图片...")
    try:
        eval_result = new_client.cmd('Runtime.evaluate', {
            'expression': '''
(function() {
    const imgs = [...document.querySelectorAll('img')]
        .filter(img => img.src && (img.src.includes('photo.yupoo') || img.src.includes('ypcdn')))
        .map(img => img.src);
    const dataSrcs = [...document.querySelectorAll('[data-src]')]
        .map(el => el.getAttribute('data-src'))
        .filter(s => s && (s.includes('photo.yupoo') || s.includes('ypcdn')));
    const bgImages = [...document.querySelectorAll('*')]
        .map(el => {
            const style = el.currentStyle || window.getComputedStyle(el, null);
            const bg = style.backgroundImage;
            if (bg && bg.includes('photo.yupoo') || (bg && bg.includes('ypcdn'))) {
                const match = bg.match(/url\\(["\']?([^"\'\\)]+)/);
                if (match) return match[1];
            }
            return null;
        })
        .filter(Boolean);
    return JSON.stringify({
        imgs: imgs,
        dataSrcs: dataSrcs,
        bgImages: bgImages,
        totalImgs: document.querySelectorAll('img').length,
        title: document.title,
        url: location.href,
    });
})()
            ''',
            'returnByValue': True,
        }, timeout=20)
        eval_val = eval_result.get('result', {}).get('result', {}).get('value', '{}')
        data = json.loads(eval_val)
        print(f"    标题: {data.get('title', '?')}")
        print(f"    img总数: {data.get('totalImgs', 0)}")
        photos = data.get('imgs', []) + data.get('dataSrcs', []) + data.get('bgImages', [])
        photos = list(dict.fromkeys(photos))
        print(f"    提取: {len(photos)} 张")
        for p in photos[:3]:
            print(f"      {p[:80]}")
    except Exception as e:
        print(f"    DOM提取失败: {e}")

    new_client.close()

    # 8. 关闭新tab
    try:
        client.cmd('Target.closeTarget', {'targetId': new_target_id})
        print(f"    已关闭tab")
    except Exception as e:
        print(f"    关闭tab失败: {e}")

    return {
        'album_id': album_id,
        'title': title,
        'photo_count': len(photos),
        'photos': photos[:20],
        'first_photo': photos[0] if photos else '',
    }

def main():
    print(f"连接到首页tab WS: {HOME_TAB_WS}")
    client = CDPClient(HOME_TAB_WS)
    print("已连接")

    # 启用Page
    try:
        client.cmd('Page.enable')
        print("Page enabled")
    except Exception as e:
        print(f"Page.enable failed: {e}")

    results = []
    for i, album in enumerate(ALBUMS, 1):
        print(f"\n[{i}/{len(ALBUMS)}] 相册 {album['album_id']}: {album['title'][:40]}...")
        try:
            result = extract_album(client, album['album_id'], album['title'])
            results.append(result)
        except Exception as e:
            print(f"  错误: {e}")
            results.append({
                'album_id': album['album_id'],
                'title': album['title'],
                'photo_count': 0,
                'photos': [],
                'error': str(e),
            })
        time.sleep(2)

    client.close()

    # 保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[完成] 结果已保存: {OUTPUT_FILE}")

    # 摘要
    for r in results:
        status = 'OK' if r.get('photo_count', 0) > 0 else 'FAIL'
        print(f"  [{status}] {r['album_id']}: {r.get('photo_count', 0)} photos")
        if r.get('photo_count', 0) > 0:
            print(f"       首图: {r.get('first_photo', '')[:80]}")

if __name__ == '__main__':
    main()
