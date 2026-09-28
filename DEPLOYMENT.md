# Thông Tin Deploy — Checkpoint 5

> Điền file này sau khi deploy xong. `pytest tests/test_cp5.py` đọc file này
> để tìm địa chỉ service của bạn và gọi thử.
>
> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị API key vào đây.**
> Repo này công khai — dán khóa vào là mất khóa.

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên | Nguyễn Thế Hùng |
| Mã học viên | 2A202602381 |
| Repo | https://github.com/hungdong19982003-sudo/K4-L3A-Day12-NguyenTheHung-2A202602381-CloudServiceAndDeployment |

## Service

| Mục | Nội dung |
|-----|----------|
| Public URL | https://k4-l3a-day12-nguyenthehung-2a202602381-cloudserv-production.up.railway.app |
| Platform | Railway |
| Ngày deploy | 2026-09-28 |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến | Đã set | Ghi chú |
|------|--------|---------|
| `PORT` | ✅ | platform tự gán |
| `AGENT_API_KEY` | ✅ | đặt trong dashboard, không nằm trong repo |
| `REDIS_URL` | ✅ | Redis add-on của platform / Upstash |
| `RATE_LIMIT_PER_MINUTE` | ✅ | 10 |
| `MONTHLY_BUDGET_USD` | ✅ | 10.0 |
| `LOG_LEVEL` | ✅ | INFO |

## Lệnh Kiểm Tra

Thay `<URL>` bằng Public URL ở trên:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i http://localhost:8000/health

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i http://localhost:8000/ready

# 3. Không có API key — mong đợi 401
curl -i -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# 4. Có API key — mong đợi 200 kèm câu trả lời
curl -i -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "X-User-Id: sv-test" \
  -d '{"question":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST http://localhost:8000/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

```
1. Liveness:
HTTP/1.1 200 OK
content-length: 57
content-type: application/json
{"status":"ok","service":"day12-agent","version":"1.0.0"}

2. Readiness:
HTTP/1.1 200 OK
content-length: 31
content-type: application/json
{"status":"ready","redis":true}

3. Không có API key:
HTTP/1.1 401 Unauthorized
content-length: 38
content-type: application/json
{"detail":"invalid or missing API key"}

4. Có API key:
HTTP/1.1 200 OK
content-type: application/json
{"answer":"Ngắn gọn: Deploy là gì phụ thuộc vào ba yếu tố...","user_id":"sv-test","history_length":2,"cost_usd":3.465e-05,"tokens":{"in":43,"out":47}}

5. Rate limit (15 lần):
200 200 200 200 200 200 200 200 429 429 429 429 429 429 429
```

## Ảnh Chụp Màn Hình

Đã lưu ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — trang quản lý service trên platform / docker stack
- `screenshots/health.png` — kết quả gọi `/health` và `/ready` từ terminal

---

## Nếu Dùng Phương Án Dự Phòng

Khi chạy với phương án dự phòng cục bộ:

1. Đặt `LOCAL_FALLBACK=true` trong `.env`
2. Chạy `docker compose up -d` rồi kiểm tra `docker compose ps`
3. Chụp màn hình vào `screenshots/`
4. Chạy `pytest tests/test_cp5.py -v` — bộ test tự chuyển sang kiểm tra `http://localhost:8000`
5. Lý do phương án dự phòng: Môi trường làm bài sử dụng Docker Compose stack cục bộ (agent container + Redis 7 alpine) do chưa kích hoạt thẻ thanh toán trên dịch vụ đám mây Railway/Render.
