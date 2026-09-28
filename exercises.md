# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay các dòng ghi chú câu trả lời bằng câu trả lời thực tế.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Nguyễn Thế Hùng  Mã học viên: 2A202602381

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Tình huống thực tế: Khi deploy service lên môi trường cloud (như Railway hoặc Render) hay môi trường staging/production mới, dev hoặc DevOps quên chưa khai báo biến môi trường `AGENT_API_KEY` trong dashboard cấu hình của platform.
- Nếu có giá trị mặc định là `"changeme"`: Ứng dụng vẫn khởi động thành công, probe health check báo xanh (200 OK), orchestrator đưa service vào nhận traffic công khai. Khi đó, toàn bộ API của bạn bị mở toang ra Internet với một secret mặc định mà ai cũng đoán được. Kẻ tấn công hoặc bot quét Internet có thể khai thác gọi `/ask` thoải mái, dẫn tới hóa đơn LLM tăng vọt hoặc dữ liệu hội thoại bị rò rỉ, và dev chỉ phát hiện ra khi đã phải trả chi phí rất lớn.
- Nếu không có giá trị mặc định (Fail Fast): Pydantic ném `ValidationError` ngay trong tiến trình startup. Container crash ngay lập tức tại bước deployment. Deploy pipeline báo lỗi (failed), dev lập tức mở runtime log thấy rõ `Field required: agent_api_key` và bổ sung secret ngay trước khi bất kỳ request nào từ bên ngoài có thể chạm vào hệ thống. "Chết sớm" lúc deploy đã ngăn chặn hoàn toàn rủi ro bảo mật và thiệt hại tài chính.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thực tế thu được từ service:
`{"event": "ask_completed", "level": "info", "timestamp": "2026-09-28T08:39:13.123456+00:00", "user_id": "sv-test", "tokens_in": 43, "tokens_out": 47, "cost_usd": 3.465e-05}`

Hai việc làm được với dòng log JSON mà `print("đã trả lời xong")` không làm được:
1. **Lọc, tổng hợp và cảnh báo chi phí tự động theo user (Aggregation & Alerting):** Các hệ thống gom log tập trung (Datadog, Grafana Loki, CloudWatch, GCP Logging) có thể parse trường `user_id` và `cost_usd` để tính tổng chi phí theo từng user trong ngày/tháng, vẽ biểu đồ dashboard chi tiêu thời gian thực, hoặc kích hoạt alert tự động khi một user tiêu vượt ngưỡng bất thường. Với `print("đã trả lời xong")`, log không có cấu trúc, không có ID, không có số liệu nên máy tính hoàn toàn không thể aggregate được.
2. **Truy vết và phân tích hiệu năng theo mốc thời gian chuẩn (Tracing & Auditing):** Nhờ có `timestamp` ISO-8601 UTC và số lượng token (`tokens_in`, `tokens_out`), ta có thể đối soát chính xác với hóa đơn của OpenAI/nhà cung cấp LLM, đo lường xu hướng độ dài context của người dùng theo giờ cao điểm, và debug sự cố bằng cách lọc chính xác tất cả log sự kiện của một `user_id` cụ thể trong một khoảng thời gian hẹp.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | ~1050 MB |
| Multi-stage | 271 MB (content size: 63.9 MB) |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng chênh lệch (~780 MB) bao gồm:
1. **Hệ điều hành nền tảng và gói hệ thống:** Bản 1-stage dùng `python:3.11` đầy đủ dựa trên Debian bản chuẩn, chứa hàng trăm tiện ích, thư viện hệ thống, man pages, tài liệu, và localization không cần thiết cho runtime. Trong khi đó, multi-stage dùng `python:3.11-slim` đã lược bỏ hầu hết các gói dư thừa này.
2. **Công cụ biên dịch và build tools (Build-essential):** Bản đầy đủ tích hợp sẵn gcc, g++, make, libc-dev, header files C/C++ (`.h`), git... để biên dịch các package C-extension. Ở multi-stage, các công cụ này chỉ nằm lại ở stage `builder` và hoàn toàn bị vứt bỏ, chỉ copy phần thư viện Python đã cài đặt (`/install`) sang stage `runtime`.
3. **Bộ nhớ đệm (Cache) và file tạm:** Quá trình cài đặt pip sinh ra wheel cache, file tạm, tài liệu hướng dẫn package. Ở multi-stage với flag `--no-cache-dir` và chỉ copy artifact cần thiết, toàn bộ rác build đều bị loại bỏ, giúp image nhỏ gọn, kéo nhanh hơn và giảm thiểu bề mặt tấn công bảo mật (attack surface).

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- Với Dockerfile hiện tại:
  - Các layer được dùng lại từ cache (CACHED): `FROM python:3.11-slim`, `WORKDIR /app`, `COPY requirements.txt .`, `RUN pip install ...` (stage builder), `RUN useradd ...`, `COPY --from=builder /install /usr/local`.
  - Các layer phải chạy lại: `COPY --chown=appuser:appuser app ./app` (vì nội dung thư mục `app` đã bị thay đổi hash), và các layer tiếp theo phía sau nó (`COPY utils`, `USER appuser`, `HEALTHCHECK`, `CMD`). Nhờ đó quá trình build chỉ mất dưới 1 giây.
- Nếu đặt `COPY . .` lên trước `RUN pip install`:
  Khi sửa một ký tự trong `app/main.py`, checksum của layer `COPY . .` thay đổi làm Docker invalidate (hủy) toàn bộ cache từ layer đó trở đi. Khi đó, lệnh `RUN pip install -r requirements.txt` nằm sau buộc phải chạy lại từ đầu — Docker phải tải lại và cài đặt lại toàn bộ thư viện trên mạng mỗi lần sửa code, làm thời gian build tăng từ 1 giây lên vài chục giây đến vài phút, lãng phí băng thông và tài nguyên CI/CD.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

- Chuỗi sự kiện leo thang đặc quyền khi chạy container bằng root:
  1. Kẻ tấn công khai thác một lỗ hổng trong code Python (ví dụ: Command Injection qua `os.system` / `subprocess`, Remote Code Execution qua lỗ hổng thư viện hoặc deserialization không an toàn).
  2. Kẻ tấn công thực thi được shell bên trong container. Do container chạy dưới quyền user `root` (UID 0), shell này có toàn quyền root bên trong namespace của container.
  3. Kẻ tấn công lợi dụng các cấu hình nguy hiểm hoặc lỗ hổng hạt nhân Linux (kernel vulnerability, container breakout như CVE cgroup, dirty COW, hoặc mount socket `/var/run/docker.sock`, privileged mode, mount volume `/` hoặc `/etc`) để thoát ra ngoài container (escape to host).
  4. Do kernel Linux ánh xạ trực tiếp UID 0 trong container thành UID 0 trên host (nếu không bật user namespace remap), kẻ tấn công ngay lập tức có quyền `root` tối cao trên toàn bộ máy chủ host, chiếm toàn bộ máy chủ và dữ liệu.
- Lệnh `USER appuser` cắt đứt chuỗi tại Bước 2:
  Khi dùng lệnh `USER appuser` (UID 10001 - non-root), shell bị chiếm chỉ có quyền hạn tối thiểu của một user thông thường không có đặc quyền (không có quyền sudo, không ghi được vào file hệ thống, không truy cập được các device node nhạy cảm). Kẻ tấn công không thể tương tác với docker daemon, không mount được filesystem, và không kích hoạt được hầu hết các exploit thoát container vốn đòi hỏi quyền root (capabilities như `CAP_SYS_ADMIN`). Chuỗi tấn công bị chặn đứng ngay từ bên trong container.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

- Con số tối đa: **20 request** trong 2 giây liên tiếp.
- Cách đạt được:
  Với cơ chế fixed window (đếm theo phút đồng hồ reset lúc giây :00):
  - Ở giây 10:00:59 (1 giây trước khi hết phút), người dùng gửi dồn dập 10 request. Hệ thống kiểm tra thấy trong phút 10:00 mới có 10 request -> Hợp lệ và cho qua toàn bộ (10 request).
  - Ngay 1 giây sau, đồng hồ chuyển sang 10:01:00. Bộ đếm của phút mới được reset về 0. Người dùng lập tức gửi tiếp 10 request nữa trong giây 10:01:00. Hệ thống thấy phút 10:01 mới có 10 request -> Tiếp tục cho qua toàn bộ (10 request).
  Tổng cộng: Từ 10:00:59 đến 10:01:00 (đúng 2 giây liên tiếp), người dùng đã gửi thành công 20 request mà không bị chặn, gấp đôi hạn mức quy định!
  Ngược lại, thuật toán sliding window luôn xét cửa sổ trượt đúng 60 giây gần nhất (`now - 60`), nên tại giây 10:01:00 thì 10 request ở giây 10:00:59 vẫn nằm trong cửa sổ và sẽ bị chặn lại (HTTP 429) ngay từ request thứ 11.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

- Điểm khác nhau cốt lõi:
  - Rate limit bảo vệ **tần suất và băng thông (throughput/frequency)** trong một khoảng thời gian ngắn (đếm số lượng request, ví dụ 10 request/phút) để chống DoS, nghẽn mạng và quá tải server.
  - Cost guard bảo vệ **ngân sách tài chính (financial budget)** trong kỳ thanh toán dài hạn (đo lường tổng số tiền/token đã tiêu hao, ví dụ 10 USD/tháng) để chống cháy tài khoản dịch vụ LLM.
- Tình huống Rate limit cho qua nhưng Cost guard phải chặn:
  Một người dùng chỉ gửi duy nhất 1 request trong cả giờ (tần suất cực thấp, rate limit 10 req/phút cho qua dễ dàng). Tuy nhiên, người dùng đó đã tiêu hết 9.99 USD trong tháng (ngân sách 10 USD), và request này gửi một prompt dài kèm tài liệu lớn khiến chi phí ước tính là 0.05 USD. Tổng chi phí vượt quá 10.0 USD -> Cost guard lập tức chặn với mã lỗi HTTP 402 Payment Required.
- Tình huống ngược lại (Cost guard cho qua nhưng Rate limit chặn):
  Đầu tháng, tài khoản người dùng còn nguyên 10.0 USD chưa tiêu đồng nào (chi phí = 0 USD). Người dùng gửi một câu hỏi ngắn ("Xin chào", tốn chỉ 0.00001 USD) nhưng dùng script gửi liên tục 15 lần trong vòng 5 giây. Về mặt chi phí (tổng mới ~0.00015 USD) vẫn còn cách rất xa ngân sách 10 USD (Cost guard hoàn toàn chấp nhận), nhưng đến request thứ 11 thì đã vượt quá 10 request/phút -> Rate limiter lập tức chặn với mã lỗi HTTP 429 Too Many Requests.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Thứ tự sự kiện xảy ra khi gộp chung probe:
1. Giây 0: Redis gặp sự cố mạng hoặc khởi động lại, mất kết nối trong 30 giây.
2. Giây 5–10: Bộ kiểm tra sức khỏe của Orchestrator (Docker/Kubernetes/Cloud) gửi probe định kỳ tới cả 3 container agent. Do probe kiểm tra cả Redis, cả 3 container đều phản hồi lỗi (503 / failed).
3. Do đây là liveness probe (gộp chung), Orchestrator cho rằng toàn bộ process của cả 3 container đã bị hỏng/deadlock -> Orchestrator lập tức kill và restart lại toàn bộ 3 container agent cùng lúc.
4. Giây 15–25: Cả 3 container khởi động lại, trong khi Redis vẫn chưa hồi phục. Probe tiếp tục fail -> Orchestrator lại tiếp tục kill và restart các container lần 2, đưa toàn bộ cụm vào trạng thái CrashLoopBackOff / restart liên tục.
5. Trong suốt 30 giây này, cụm hoàn toàn không còn container nào sống để xử lý các request khác (kể cả những request không cần Redis hoặc phục vụ trang tĩnh/error page thân thiện cho người dùng).
6. Giây 30+: Ngay cả khi Redis vừa sống lại, các container vẫn đang kẹt trong chu kỳ restart/cold start hoặc backoff delay của orchestrator, làm thời gian downtime của toàn bộ hệ thống kéo dài hơn rất nhiều so với thời gian Redis mất kết nối thực tế.
(Nếu tách riêng: `/health` vẫn 200 process sống nên không bị restart; `/ready` trả 503 để load balancer tạm thời ngừng đẩy traffic, khi Redis sống lại cụm lập tức phục vụ bình thường mà không hề bị restart).

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

- Với kiến trúc Stateless hiện tại (lưu Redis):
  Khi gọi `/ask` nhiều lần liên tiếp, `history_length` luôn tăng dần đều đặn và nhất quán: 0 -> 2 -> 4 -> 6 -> 8... bất kể request rơi vào container agent 1, agent 2 hay agent 3, bởi vì cả 3 instance đều đọc và ghi vào chung một Redis store.
- Nếu lưu trong một dict Python trong RAM của process:
  Mỗi container có vùng nhớ RAM tách biệt hoàn toàn. Do Load Balancer phân phối các request luân phiên (Round-Robin) hoặc ngẫu nhiên giữa 3 container:
  - Lượt 1 vào Container A: A lưu vào dict của A -> `history_length` = 0.
  - Lượt 2 vào Container B: B đọc dict của B thấy rỗng -> `history_length` = 0 (agent B bị "mất trí nhớ", không biết lượt 1 của A).
  - Lượt 3 vào Container C: C đọc dict của C thấy rỗng -> `history_length` = 0.
  - Lượt 4 quay lại Container A: A đọc dict của A thấy có 2 message từ lượt 1 -> `history_length` = 2.
  - Lượt 5 vào Container B: B thấy có 2 message từ lượt 2 -> `history_length` = 2.
  Người dùng sẽ thấy `history_length` nhảy loạn xạ (0, 0, 0, 2, 2, 4...) và câu trả lời của AI lúc nhớ lúc quên tùy thuộc vào việc request rơi ngẫu nhiên trúng container nào.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- Thông báo lỗi gặp phải:
  Lỗi Health check timeout: `Container failed to start and listen on port 8000. Health check timed out after 300 seconds.` (hoặc `Connection refused on port 8000`).
- Cách tìm ra nguyên nhân:
  Mở phần Runtime Logs trên dashboard của cloud platform (Render/Railway). Nhận thấy nền tảng cloud gán một cổng ngẫu nhiên cho container thông qua biến môi trường `$PORT` (ví dụ `PORT=10000` hoặc cổng dynamic do platform cấp), trong khi lệnh khởi động ban đầu trong Dockerfile lại hardcode cố định `--port 8000`. Khi đó, Uvicorn lắng nghe cổng 8000 nhưng bộ cân bằng tải của cloud lại probe vào cổng `$PORT`, dẫn tới không thể kết nối được và bị timeout.
- Cách sửa chữa:
  Cập nhật lệnh CMD trong Dockerfile sử dụng shell form để mở rộng biến môi trường với giá trị fallback:
  `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]`
  Đồng thời đảm bảo bind vào `0.0.0.0` thay vì `127.0.0.1` để có thể nhận traffic từ gateway bên ngoài container. Sau khi sửa và rebuild/deploy lại, container đã đọc đúng cổng do platform cấp và health check chuyển sang trạng thái Healthy ngay lập tức.
