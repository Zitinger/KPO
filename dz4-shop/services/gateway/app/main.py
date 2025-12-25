import itertools
from typing import Any, Dict

import httpx
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .config import load_settings


class CreateOrderRequest(BaseModel):
    amount: int = Field(ge=0)
    description: str = Field(min_length=1, max_length=500)


class DepositRequest(BaseModel):
    amount: int = Field(ge=0)


settings = load_settings()

app = FastAPI(title="API Gateway")


_orders_cycle = itertools.cycle(settings.orders_base_urls())


def _orders_url() -> str:
    return next(_orders_cycle)


async def _proxy_json(method: str, url: str, headers: Dict[str, str], json_body: Any = None) -> Any:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.request(method, url, headers=headers, json=json_body)
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail={"raw": f"upstream request failed: {e}"})

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = {"raw": resp.text}
        raise HTTPException(status_code=resp.status_code, detail=detail)

    if resp.content:
        try:
            return resp.json()
        except Exception:
            return {"raw": resp.text}

    return None


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/account")
async def create_account(x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "POST",
        f"{settings.payments_url}/account",
        headers={"X-User-Id": x_user_id},
        json_body=None,
    )


@app.post("/api/account/deposit")
async def deposit(req: DepositRequest, x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "POST",
        f"{settings.payments_url}/account/deposit",
        headers={"X-User-Id": x_user_id},
        json_body=req.model_dump(),
    )


@app.get("/api/account")
async def get_account(x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "GET",
        f"{settings.payments_url}/account",
        headers={"X-User-Id": x_user_id},
        json_body=None,
    )


@app.post("/api/orders")
async def create_order(req: CreateOrderRequest, x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "POST",
        f"{_orders_url()}/orders",
        headers={"X-User-Id": x_user_id},
        json_body=req.model_dump(),
    )


@app.get("/api/orders")
async def list_orders(x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "GET",
        f"{_orders_url()}/orders",
        headers={"X-User-Id": x_user_id},
        json_body=None,
    )


@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, x_user_id: str = Header(...)) -> Any:
    return await _proxy_json(
        "GET",
        f"{_orders_url()}/orders/{order_id}",
        headers={"X-User-Id": x_user_id},
        json_body=None,
    )


@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def ui() -> str:
    return """<!doctype html>
<html lang=\"ru\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>dz4 — уведомления по WebSocket</title>
  <style>
    :root { --bg:#0b1020; --card:#111a33; --text:#e7ecff; --muted:#aab3d1; --accent:#6ea8fe; --ok:#35d07f; --bad:#ff5c7a; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background: linear-gradient(180deg,#0b1020,#070a14); color: var(--text); }
    .wrap { max-width: 980px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 22px; margin: 0 0 12px; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 900px){ .grid{ grid-template-columns:1fr; } }
    .card { background: rgba(17,26,51,.92); border: 1px solid rgba(255,255,255,.08); border-radius: 14px; padding: 16px; box-shadow: 0 14px 40px rgba(0,0,0,.25); }
    label { display:block; font-size: 12px; color: var(--muted); margin-top: 10px; }
    input, textarea { width: 100%; margin-top: 6px; border-radius: 10px; border: 1px solid rgba(255,255,255,.12); background: rgba(0,0,0,.25); color: var(--text); padding: 10px 12px; outline: none; }
    textarea { min-height: 42px; resize: vertical; }
    .row { display:flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }
    button { border: 0; background: var(--accent); color: #081023; padding: 10px 12px; border-radius: 10px; cursor: pointer; font-weight: 600; }
    button.secondary { background: rgba(255,255,255,.12); color: var(--text); }
    button.danger { background: rgba(255,92,122,.85); color:#19040a; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    .hint { color: var(--muted); font-size: 12px; line-height: 1.35; margin-top: 8px; }
    .log { margin-top: 10px; background: rgba(0,0,0,.22); border: 1px solid rgba(255,255,255,.08); border-radius: 12px; padding: 10px; min-height: 120px; max-height: 280px; overflow:auto; font-size: 12px; }

    .toasts { position: fixed; right: 16px; top: 16px; display: flex; flex-direction: column; gap: 10px; z-index: 99999; }
    .toast { min-width: 280px; max-width: 420px; background: rgba(17,26,51,.95); border: 1px solid rgba(255,255,255,.12); border-radius: 14px; padding: 12px 12px; box-shadow: 0 18px 45px rgba(0,0,0,.35); animation: in .18s ease-out; }
    .toast .t { font-weight: 700; font-size: 13px; }
    .toast .m { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .toast.ok { border-color: rgba(53,208,127,.45); }
    .toast.bad { border-color: rgba(255,92,122,.55); }
    @keyframes in { from { transform: translateY(-6px); opacity: .3; } to { transform: translateY(0); opacity: 1; } }
  </style>
</head>
<body>
  <div class=\"toasts\" id=\"toasts\"></div>

  <div class=\"wrap\">
    <h1>dz4: WebSocket + push-уведомления</h1>

    <div class=\"grid\">
      <div class=\"card\">
        <div class=\"hint\">
          1) Создай аккаунт и пополни баланс<br/>
          2) Создай заказ — страница сама подключится к WebSocket<br/>
          3) Когда статус заказа изменится, появится всплывающее уведомление (toast) + (опционально) браузерное Notification.
        </div>

        <label>X-User-Id</label>
        <input id=\"userId\" value=\"u1\" />

        <div class=\"row\">
          <button class=\"secondary\" id=\"btnEnableNotif\">Включить уведомления браузера</button>
          <button class=\"secondary\" id=\"btnGetAccount\">Проверить баланс</button>
        </div>

        <label>Сумма пополнения</label>
        <input id=\"depositAmount\" type=\"number\" value=\"500\" />

        <div class=\"row\">
          <button id=\"btnCreateAccount\">Создать аккаунт</button>
          <button id=\"btnDeposit\">Пополнить</button>
        </div>
      </div>

      <div class=\"card\">
        <label>Сумма заказа</label>
        <input id=\"orderAmount\" type=\"number\" value=\"200\" />

        <label>Описание</label>
        <textarea id=\"orderDesc\">test</textarea>

        <div class=\"row\">
          <button id=\"btnCreateOrder\">Создать заказ</button>
          <button class=\"secondary\" id=\"btnListOrders\">Список заказов</button>
        </div>

        <label>order_id (для ручного подключения к WS)</label>
        <input id=\"orderId\" placeholder=\"UUID\" class=\"mono\" />

        <div class=\"row\">
          <button class=\"secondary\" id=\"btnConnectWs\">Подключиться к WS</button>
          <button class=\"danger\" id=\"btnCloseWs\">Закрыть WS</button>
        </div>

        <div class=\"hint\">WS URL будет вида <span class=\"mono\">ws://&lt;host&gt;/ws/orders/&lt;order_id&gt;?user_id=&lt;X-User-Id&gt;</span></div>
        <div class=\"log mono\" id=\"log\"></div>
      </div>
    </div>
  </div>

<script>
  const $ = (id) => document.getElementById(id);
  const logEl = $('log');
  const toasts = $('toasts');
  let ws = null;

  function now() {
    const d = new Date();
    return d.toLocaleTimeString();
  }

  function appendLog(line) {
    logEl.textContent += `[${now()}] ${line}\n`;
    logEl.scrollTop = logEl.scrollHeight;
  }

  function toast(title, msg, kind='') {
    const el = document.createElement('div');
    el.className = `toast ${kind}`;
    el.innerHTML = `<div class=\"t\">${title}</div><div class=\"m\">${msg}</div>`;
    toasts.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(-6px)'; }, 4200);
    setTimeout(() => { el.remove(); }, 5200);
  }

  async function api(path, method, body=null, userId=null) {
    const headers = { 'accept': 'application/json' };
    if (userId) { headers['X-User-Id'] = userId; }
    if (body !== null) { headers['content-type'] = 'application/json'; }

    const resp = await fetch(path, {
      method,
      headers,
      body: body === null ? undefined : JSON.stringify(body)
    });

    let data = null;
    const text = await resp.text();
    try { data = text ? JSON.parse(text) : null; } catch { data = { raw: text }; }

    if (!resp.ok) {
      throw { status: resp.status, data };
    }
    return data;
  }

  function wsUrl(orderId, userId) {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${location.host}/ws/orders/${encodeURIComponent(orderId)}?user_id=${encodeURIComponent(userId)}`;
  }

  function closeWs() {
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  function connectWs(orderId, userId) {
    closeWs();

    const url = wsUrl(orderId, userId);
    appendLog(`WS connect -> ${url}`);
    toast('WebSocket', `Подключение к ${orderId}`, '');

    ws = new WebSocket(url);

    ws.onopen = () => {
      appendLog('WS open');
    };

    ws.onclose = () => {
      appendLog('WS close');
      toast('WebSocket', 'Соединение закрыто', '');
    };

    ws.onerror = (e) => {
      appendLog('WS error');
      toast('WebSocket', 'Ошибка соединения', 'bad');
      console.log('WS error', e);
    };

    ws.onmessage = (e) => {
      appendLog(`WS message: ${e.data}`);
      let msg = null;
      try { msg = JSON.parse(e.data); } catch { msg = { raw: e.data }; }

      const type = msg.type || 'message';
      const status = msg.status || '';

      const title = type === 'status_update' ? 'Статус заказа изменился' : 'Состояние заказа';
      const kind = status === 'FINISHED' ? 'ok' : (status === 'CANCELLED' ? 'bad' : '');
      toast(title, `order_id=${msg.order_id || orderId}, status=${status}`, kind);

      if (window.Notification && Notification.permission === 'granted') {
        try {
          new Notification(title, { body: `Заказ ${msg.order_id || orderId}: ${status}` });
        } catch {
          // ignore
        }
      }

      // Если статус финальный — можно закрыть WS
      if (type === 'status_update' && (status === 'FINISHED' || status === 'CANCELLED')) {
        setTimeout(() => closeWs(), 1500);
      }
    };
  }

  $('btnEnableNotif').onclick = async () => {
    if (!window.Notification) {
      toast('Notification API', 'В этом браузере нет Notification API', 'bad');
      return;
    }
    const perm = await Notification.requestPermission();
    toast('Notification API', `Разрешение: ${perm}`, perm === 'granted' ? 'ok' : 'bad');
  };

  $('btnCreateAccount').onclick = async () => {
    const userId = $('userId').value.trim();
    try {
      await api('/api/account', 'POST', null, userId);
      toast('Аккаунт', `Создан для ${userId}`, 'ok');
      appendLog(`account created for ${userId}`);
    } catch (e) {
      toast('Аккаунт', `Ошибка: HTTP ${e.status}`, 'bad');
      appendLog(`account error: ${JSON.stringify(e.data)}`);
    }
  };

  $('btnDeposit').onclick = async () => {
    const userId = $('userId').value.trim();
    const amount = Number($('depositAmount').value);
    try {
      await api('/api/account/deposit', 'POST', { amount }, userId);
      toast('Пополнение', `+${amount} для ${userId}`, 'ok');
      appendLog(`deposit ok: +${amount}`);
    } catch (e) {
      toast('Пополнение', `Ошибка: HTTP ${e.status}`, 'bad');
      appendLog(`deposit error: ${JSON.stringify(e.data)}`);
    }
  };

  $('btnGetAccount').onclick = async () => {
    const userId = $('userId').value.trim();
    try {
      const acc = await api('/api/account', 'GET', null, userId);
      toast('Баланс', `balance=${acc.balance}`, '');
      appendLog(`account: ${JSON.stringify(acc)}`);
    } catch (e) {
      toast('Баланс', `Ошибка: HTTP ${e.status}`, 'bad');
      appendLog(`get account error: ${JSON.stringify(e.data)}`);
    }
  };

  $('btnCreateOrder').onclick = async () => {
    const userId = $('userId').value.trim();
    const amount = Number($('orderAmount').value);
    const description = $('orderDesc').value.trim() || 'test';

    try {
      const res = await api('/api/orders', 'POST', { amount, description }, userId);
      const orderId = res.id || res.order_id;
      $('orderId').value = orderId;

      toast('Заказ', `Создан: ${orderId}`, 'ok');
      appendLog(`order created: ${JSON.stringify(res)}`);

      connectWs(orderId, userId);
    } catch (e) {
      toast('Заказ', `Ошибка: HTTP ${e.status}`, 'bad');
      appendLog(`create order error: ${JSON.stringify(e.data)}`);
    }
  };

  $('btnListOrders').onclick = async () => {
    const userId = $('userId').value.trim();
    try {
      const res = await api('/api/orders', 'GET', null, userId);
      toast('Заказы', `Получено: ${Array.isArray(res) ? res.length : 1}`, '');
      appendLog(`orders: ${JSON.stringify(res)}`);
    } catch (e) {
      toast('Заказы', `Ошибка: HTTP ${e.status}`, 'bad');
      appendLog(`list orders error: ${JSON.stringify(e.data)}`);
    }
  };

  $('btnConnectWs').onclick = () => {
    const userId = $('userId').value.trim();
    const orderId = $('orderId').value.trim();
    if (!orderId) {
      toast('WebSocket', 'Сначала укажи order_id', 'bad');
      return;
    }
    connectWs(orderId, userId);
  };

  $('btnCloseWs').onclick = () => {
    closeWs();
  };

  // автоподключение, если есть order_id в URL: /ui?order_id=...&user_id=...
  (function autoConnectFromQuery() {
    const q = new URLSearchParams(location.search);
    const oid = q.get('order_id');
    const uid = q.get('user_id');
    if (uid) { $('userId').value = uid; }
    if (oid) {
      $('orderId').value = oid;
      connectWs(oid, $('userId').value.trim());
    }
  })();
</script>
</body>
</html>"""


_round_robin_counter = itertools.count()


@app.get("/backend")
async def get_backend() -> Dict[str, str]:
    idx = next(_round_robin_counter)
    return {"gateway": "gateway-1", "rr": str(idx)}
