"""Agent service — điểm ráp nối của cả lab (CP1, CP3, CP4).

Luồng một request tới /ask:

    client ──► verify_api_key ──► rate_limiter ──► cost_guard
                                                       │
                              store.get_history ◄──────┘
                                       │
                                    ask_llm
                                       │
                              store.append × 2 ──► cost_guard.record ──► log_event
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from utils.mock_llm import ask_llm

from .auth import verify_api_key
from .config import get_settings
from .cost_guard import CostGuard
from .lifecycle import lifecycle
from .logging_utils import log_event
from .rate_limiter import RateLimiter
from .store import ConversationStore, get_redis_client

SERVICE_NAME = "day12-agent"
SERVICE_VERSION = "1.0.0"


# ─────────────────────────────────────────────────────────────
# Providers — CHO SẴN
# Tách ra thành hàm để test có thể thay bằng Redis giả qua
# app.dependency_overrides, và để kết nối Redis chỉ tạo khi thật sự cần.
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_store() -> ConversationStore:
    return ConversationStore(get_redis_client())


@lru_cache(maxsize=1)
def get_rate_limiter() -> RateLimiter:
    return RateLimiter(get_redis_client(), get_settings().rate_limit_per_minute)


@lru_cache(maxsize=1)
def get_cost_guard() -> CostGuard:
    return CostGuard(get_redis_client(), get_settings().monthly_budget_usd)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """CHO SẴN — chạy lúc app khởi động và lúc tắt."""
    lifecycle.install()
    log_event("service_started", service=SERVICE_NAME, version=SERVICE_VERSION)
    yield
    log_event("service_stopped", service=SERVICE_NAME)


app = FastAPI(title="Day 12 Production Agent", version=SERVICE_VERSION, lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


CHAT_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Day 12 — Cloud AI Agent</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0b0f19;
      color: #f1f5f9;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      padding: 12px;
    }
    .chat-container {
      width: 100%;
      max-width: 720px;
      height: 90vh;
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    header {
      padding: 14px 18px;
      background: #1e293b;
      border-bottom: 1px solid #334155;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .title { font-size: 1.1rem; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }
    .badge {
      font-size: 0.75rem;
      background: #064e3b;
      color: #34d399;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .dot { width: 8px; height: 8px; background: #34d399; border-radius: 50%; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }
    .config-bar {
      background: #0f172a;
      padding: 10px 16px;
      border-bottom: 1px solid #1e293b;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .config-field { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 180px; }
    .config-field label { font-size: 0.75rem; color: #94a3b8; font-weight: 600; white-space: nowrap; }
    .config-field input {
      flex: 1;
      padding: 6px 10px;
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      color: #f8fafc;
      font-size: 0.8rem;
      outline: none;
    }
    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 14px;
      font-size: 0.92rem;
      line-height: 1.5;
      word-break: break-word;
    }
    .msg.bot {
      align-self: flex-start;
      background: #1e293b;
      border: 1px solid #334155;
      border-bottom-left-radius: 4px;
    }
    .msg.user {
      align-self: flex-end;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: #ffffff;
      border-bottom-right-radius: 4px;
    }
    .msg-meta {
      font-size: 0.7rem;
      color: #94a3b8;
      margin-top: 6px;
      padding-top: 6px;
      border-top: 1px solid #334155;
      display: flex;
      gap: 12px;
    }
    .input-bar {
      padding: 12px 16px;
      background: #1e293b;
      border-top: 1px solid #334155;
      display: flex;
      gap: 10px;
    }
    .input-bar input {
      flex: 1;
      padding: 10px 14px;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 10px;
      color: #f8fafc;
      font-size: 0.95rem;
      outline: none;
    }
    .input-bar input:focus { border-color: #38bdf8; }
    .send-btn {
      padding: 0 18px;
      background: #0284c7;
      color: #ffffff;
      border: none;
      border-radius: 10px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }
    .send-btn:hover { background: #0369a1; }
    .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  </style>
</head>
<body>
  <div class="chat-container">
    <header>
      <div class="title">
        <span>🤖</span>
        <span>Day 12 Production AI Agent</span>
      </div>
      <div class="badge">
        <span class="dot"></span>
        <span>Online</span>
      </div>
    </header>

    <div class="config-bar">
      <div class="config-field">
        <label>X-API-Key:</label>
        <input type="password" id="apiKey" placeholder="Nhập API Key..." />
      </div>
      <div class="config-field">
        <label>User ID:</label>
        <input type="text" id="userId" value="sv-test" />
      </div>
    </div>

    <div class="messages-area" id="messages">
      <div class="msg bot">
        👋 Xin chào! Mình là AI Agent được triển khai trên Cloud.<br><br>
        Nhập <strong>API Key</strong> ở thanh trên rồi gửi câu hỏi (ví dụ: <em>"Docker là gì?"</em>, <em>"Stateless là gì?"</em>) để trò chuyện!
      </div>
    </div>

    <div class="input-bar">
      <input type="text" id="questionInput" placeholder="Nhập câu hỏi của bạn..." autocomplete="off" />
      <button class="send-btn" id="sendBtn">Gửi</button>
    </div>
  </div>

  <script>
    const savedKey = localStorage.getItem("agent_api_key") || "";
    const apiKeyInput = document.getElementById("apiKey");
    const userIdInput = document.getElementById("userId");
    const questionInput = document.getElementById("questionInput");
    const sendBtn = document.getElementById("sendBtn");
    const messagesArea = document.getElementById("messages");

    if (savedKey) apiKeyInput.value = savedKey;

    apiKeyInput.addEventListener("change", () => {
      localStorage.setItem("agent_api_key", apiKeyInput.value.trim());
    });

    async function sendQuestion() {
      const q = questionInput.value.trim();
      if (!q) return;

      const apiKey = apiKeyInput.value.trim();
      const userId = userIdInput.value.trim() || "sv-test";

      appendMsg(q, "user");
      questionInput.value = "";
      sendBtn.disabled = true;

      const loadingElem = appendMsg("Đang suy nghĩ...", "bot");

      try {
        const headers = { "Content-Type": "application/json" };
        if (apiKey) headers["X-API-Key"] = apiKey;
        if (userId) headers["X-User-Id"] = userId;

        const res = await fetch("/ask", {
          method: "POST",
          headers: headers,
          body: JSON.stringify({ question: q })
        });

        const data = await res.json();
        loadingElem.remove();

        if (res.status === 200) {
          appendMsg(data.answer, "bot", {
            tokens: `${data.tokens.in} in / ${data.tokens.out} out`,
            cost: `$${data.cost_usd.toFixed(6)}`,
            history: `${data.history_length} tin nhắn trước`
          });
        } else if (res.status === 401) {
          appendMsg("❌ 401 Unauthorized: Thiếu hoặc sai API Key. Hãy nhập đúng X-API-Key vào thanh cấu hình phía trên.", "bot");
        } else if (res.status === 429) {
          appendMsg("⚠️ 429 Too Many Requests: Bạn đã gọi quá nhanh (vượt hạn mức Rate Limit).", "bot");
        } else if (res.status === 402) {
          appendMsg("⛔ 402 Payment Required: Đã vượt ngân sách hàng tháng (Cost Guard).", "bot");
        } else {
          appendMsg(`Lỗi (${res.status}): ${JSON.stringify(data.detail || data)}`, "bot");
        }
      } catch (err) {
        loadingElem.remove();
        appendMsg(`⚠️ Lỗi kết nối: ${err.message}`, "bot");
      } finally {
        sendBtn.disabled = false;
        questionInput.focus();
      }
    }

    function appendMsg(text, type, meta) {
      const div = document.createElement("div");
      div.className = "msg " + type;
      div.innerHTML = text.replace(/\\n/g, "<br>");
      if (meta) {
        const metaDiv = document.createElement("div");
        metaDiv.className = "msg-meta";
        metaDiv.innerHTML = `<span>Tokens: ${meta.tokens}</span><span>Chi phí: ${meta.cost}</span><span>${meta.history}</span>`;
        div.appendChild(metaDiv);
      }
      messagesArea.appendChild(div);
      messagesArea.scrollTop = messagesArea.scrollHeight;
      return div;
    }

    sendBtn.addEventListener("click", sendQuestion);
    questionInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") sendQuestion();
    });
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """Giao diện chat trực quan với Agent."""
    return HTMLResponse(content=CHAT_PAGE)


# ─────────────────────────────────────────────────────────────
# Health & readiness
# ─────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    """Liveness probe — process còn sống không?

    TODO (CP1 + CP4):
      - Đang tắt dần (``lifecycle.shutting_down``) → trả
        ``JSONResponse(status_code=503, content={"status": "shutting_down"})``
      - Bình thường → ``{"status": "ok", "service": SERVICE_NAME,
        "version": SERVICE_VERSION}`` (mặc định FastAPI trả 200).

    Endpoint này phải **nhẹ**: không gọi Redis, không query DB. Nó chỉ trả
    lời câu hỏi "có cần restart container này không?". Nếu nó phụ thuộc
    Redis, Redis chết một nhịp là cả cụm container bị restart theo.
    """
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}


@app.get("/ready")
def ready(store: ConversationStore = Depends(get_store)):
    """Readiness probe — đã sẵn sàng nhận traffic chưa?

    TODO (CP4):
      - Đang tắt dần → 503 ``{"status": "shutting_down"}``
      - ``store.ping()`` False → 503 ``{"status": "not ready", "redis": False}``
      - Ngược lại → ``{"status": "ready", "redis": True}``

    Khác /health ở chỗ: endpoint này ĐƯỢC PHÉP kiểm tra dependency. Load
    balancer dùng nó để quyết định có đẩy request vào instance này không.
    """
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    if not store.ping():
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}


# ─────────────────────────────────────────────────────────────
# Endpoint chính
# ─────────────────────────────────────────────────────────────
@app.post("/ask")
def ask(
    payload: AskRequest,
    user_id: str = Depends(verify_api_key),
    store: ConversationStore = Depends(get_store),
    limiter: RateLimiter = Depends(get_rate_limiter),
    guard: CostGuard = Depends(get_cost_guard),
):
    """Hỏi agent một câu.

    TODO (CP3 + CP4) — làm ĐÚNG THỨ TỰ sau:
      1. ``limiter.check(user_id)``           → 429 nếu gọi quá nhanh
      2. ``guard.check(user_id)``             → 402 nếu hết ngân sách
      3. ``history = store.get_history(user_id)``
      4. ``result = ask_llm(payload.question, history)``
      5. ``store.append(user_id, "user", payload.question)`` và
         ``store.append(user_id, "assistant", result["answer"])``
      6. ``guard.record(user_id, result["cost_usd"])``
      7. ``log_event("ask_completed", user_id=user_id,
         tokens_in=result["tokens_in"], tokens_out=result["tokens_out"],
         cost_usd=result["cost_usd"])``
      8. trả về::

            {
                "answer": result["answer"],
                "user_id": user_id,
                "history_length": len(history),
                "cost_usd": result["cost_usd"],
                "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
            }

    Vì sao check trước rồi mới gọi LLM? Vì tiền mất ở bước gọi LLM. Chặn sau
    khi đã gọi thì bạn vừa trả tiền vừa trả lỗi.

    ``user_id`` do ``verify_api_key`` trả về, nên request không có API key
    hợp lệ sẽ dừng ở 401 trước khi chạm vào bất cứ dòng nào ở đây.
    """
    limiter.check(user_id)
    guard.check(user_id)
    history = store.get_history(user_id)
    result = ask_llm(payload.question, history)
    store.append(user_id, "user", payload.question)
    store.append(user_id, "assistant", result["answer"])
    guard.record(user_id, result["cost_usd"])
    log_event(
        "ask_completed",
        user_id=user_id,
        tokens_in=result["tokens_in"],
        tokens_out=result["tokens_out"],
        cost_usd=result["cost_usd"],
    )
    return {
        "answer": result["answer"],
        "user_id": user_id,
        "history_length": len(history),
        "cost_usd": result["cost_usd"],
        "tokens": {"in": result["tokens_in"], "out": result["tokens_out"]},
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
