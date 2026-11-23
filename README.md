# TaskHub

API quản lý công việc theo workspace, xây dựng bằng FastAPI, SQLAlchemy async, Pydantic và PostgreSQL. Redis cache danh sách task; phân quyền theo workspace; email gán task hiện được ghi log bằng background task.

## Chạy nhanh bằng Docker

Yêu cầu Docker Engine/Docker Desktop đang chạy, Docker Compose v2 và cổng 8000 còn trống.

```bash
docker compose up --build
```

Không cần tạo `.env` cho lần chạy thử: Compose có cấu hình **dev** mặc định. Lần build đầu cần Internet để tải image và dependencies.

| Địa chỉ | Chức năng |
| --- | --- |
| http://localhost:8000/health | Kiểm tra tiến trình API |
| http://localhost:8000/docs | Swagger UI, thử request và Authorize |
| http://localhost:8000/redoc | Tài liệu ReDoc |
| http://localhost:8000/openapi.json | OpenAPI schema |

Compose chạy ba service `app`, `db` và `redis`. App chờ healthcheck của DB và Redis, kiểm tra cấu hình, chạy `alembic upgrade head`, sau đó mở Uvicorn. Nếu cấu hình hoặc migration lỗi, container app dừng và không mở server. Runtime dùng image Python slim và user `taskhub` có UID/GID 10001.

```bash
docker compose ps
docker compose logs -f app
docker compose exec app alembic current
docker compose exec app id
docker compose down
```

`docker compose down` giữ volume PostgreSQL. Chỉ dùng `docker compose down -v` khi chủ động muốn **xóa toàn bộ dữ liệu DB của stack**. Redis dùng làm cache nên không lưu lâu dài. DB/Redis chỉ mở cổng trong mạng Docker; API bind vào loopback của máy.

Nếu cổng 8000 bận, đặt `TASKHUB_PORT=8001` trước khi chạy Compose. Với PowerShell:

```powershell
$env:TASKHUB_PORT = "8001"
docker compose up --build
```

## Thử đăng ký, đăng nhập trên Swagger

1. Mở `/docs`, chọn **POST /api/v1/auth/register → Try it out**. Dùng ví dụ có sẵn hoặc email khác nếu tài khoản đã tồn tại, rồi **Execute**. Kết quả mong đợi: 201.
2. Mở **POST /api/v1/auth/login → Try it out**. `username` là email vừa đăng ký; `password` là mật khẩu. Endpoint nhận `application/x-www-form-urlencoded`, không nhận JSON. Kết quả: 200, có `access_token`, `refresh_token` và `token_type=bearer`.
3. Sao chép `access_token`, bấm **Authorize** ở đầu trang. Dán riêng token, không thêm chữ `Bearer`, rồi xác nhận và đóng hộp thoại.
4. Gọi **GET /api/v1/users/me**. Kết quả: 200, đúng tài khoản vừa tạo.
5. Tạo workspace bằng **POST /api/v1/workspaces**. Dùng ID trả về để tạo project, rồi tạo task bằng **POST /api/v1/projects/{project_id}/tasks**.

Swagger gửi header `Authorization: Bearer <access_token>` cho các endpoint được bảo vệ. Token không được giữ sau khi reload trang. `/redoc` dùng để đọc tài liệu; thao tác thử API thực hiện ở Swagger.

Lỗi nghiệp vụ dùng `{"detail": "..."}`. Lỗi 422 giữ định dạng validation của FastAPI: `{"detail": [{"loc": [...], "msg": "...", "type": "..."}]}`. Khai báo lỗi được dùng chung tại `app/api/responses.py`, không thay đổi response runtime cũ chỉ để khớp tài liệu.

## Configuration đa môi trường

Chọn môi trường bằng biến **process** `APP_ENV` trước khi chạy Python/Uvicorn/Alembic. Giá trị hợp lệ: `dev`, `test`, `prod`; mặc định `dev`.

| APP_ENV | File được đọc | Swagger/ReDoc mặc định | Database |
| --- | --- | --- | --- |
| dev | `.env.dev`; nếu file này không tồn tại thì dùng `.env` cũ | Bật | PostgreSQL asyncpg |
| test | `.env.test` | Bật | PostgreSQL hoặc SQLite aiosqlite |
| prod | `.env.prod` | Tắt cả docs, redoc, openapi.json | PostgreSQL asyncpg |

Các file môi trường **không trộn lẫn**: thiếu key trong `.env.prod` không lấy key từ `.env.dev` hoặc `.env`. File không bắt buộc tồn tại nếu process environment đã cung cấp đủ cấu hình. `APP_ENV` trong file chỉ ghi rõ mục đích file, không được đổi môi trường đã chọn từ process.

Thứ tự ưu tiên: tham số truyền trực tiếp vào `Settings` → biến process → file môi trường được chọn → giá trị mặc định. Khi test cần cô lập file, dùng `Settings(_env_file=None, ...)`.

| Biến | Mặc định/quy tắc |
| --- | --- |
| `APP_ENV` | `dev`; chỉ nhận `dev`, `test`, `prod` |
| `DATABASE_URL` | Bắt buộc; `postgresql+asyncpg://user:password@host:port/database`; SQLite chỉ ở test |
| `REDIS_URL` | Dev/test: `redis://localhost:6379/0`; prod phải khai báo rõ; hỗ trợ `redis://` và `rediss://` |
| `SECRET_KEY` | Bắt buộc, ít nhất 32 ký tự; prod từ chối key mẫu và chuỗi quá ít ký tự khác nhau |
| `DB_ECHO` | `false`; prod bắt buộc tắt |
| `DOCS_ENABLED` | Tự bật ở dev/test, tắt ở prod; có thể ghi đè bằng `true`/`false` |
| `CACHE_TTL_SECONDS` | `60`, phải lớn hơn 0 |
| `LOG_LEVEL` | `INFO`; nhận DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30`, phải lớn hơn 0 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7`, phải lớn hơn 0 |

URL Redis có host, port hợp lệ và chỉ số DB không âm; không hỗ trợ query string hoặc fragment. Thông tin kết nối PostgreSQL phải có host, user, password và tên database. Ký tự đặc biệt trong user/password cần URL-encode. Alembic xử lý được dấu `%` trong URL đã encode.

Fail-fast kiểm tra cấu trúc cấu hình trước khi mở server, không thay thế kiểm tra kết nối mạng hoặc chứng minh độ ngẫu nhiên của secret. Lỗi hiển thị tên biến và yêu cầu cần sửa; đầu vào nhạy cảm không được đưa vào chuỗi lỗi validation.

## Chạy local không dùng container app

Dùng Python 3.12 trở lên, PostgreSQL và Redis có thể kết nối từ máy. Compose mặc định không publish cổng DB/Redis, vì vậy cách chạy local này cần hai dịch vụ riêng hoặc một Compose override chủ động publish cổng.

```powershell
python -m venv venv
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.dev.example .env.dev
$env:APP_ENV = "dev"
```

Sửa `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` trong `.env.dev` rồi chạy:

```powershell
venv/Scripts/python.exe -m alembic upgrade head
venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Trên Linux/macOS, dùng `.venv/bin/python` hoặc `venv/bin/python` và `export APP_ENV=dev` tương ứng. Không commit `.env`, `.env.dev`, `.env.test`, `.env.prod`; chỉ commit các file `.example`.

`requirements.txt` chứa dependencies runtime trực tiếp đã ghim phiên bản. `requirements-dev.txt` thêm pytest, SQLite, HTTP client, fakeredis và Ruff. `requirements-browser.txt` chỉ dùng cho kiểm thử giao diện tùy chọn. Image runtime không cài bộ test hoặc trình duyệt.

## Cấu hình Docker và production

Compose truyền biến trực tiếp cho app, không copy hoặc mount file `.env.*` vào image. Những biến Compose bắt đầu bằng `TASKHUB_` giúp tránh vô tình lấy `DATABASE_URL` localhost từ `.env` local.

| Biến Compose | Tác dụng |
| --- | --- |
| `TASKHUB_APP_ENV` | APP_ENV của container, mặc định dev |
| `TASKHUB_PORT` | Cổng API trên máy, mặc định 8000 |
| `TASKHUB_SECRET_KEY` | SECRET_KEY của app; mặc định chỉ dành cho dev |
| `TASKHUB_DATABASE_URL` | URL DB của app, mặc định trỏ `db:5432` |
| `TASKHUB_POSTGRES_PASSWORD` | Password khởi tạo PostgreSQL của stack |
| `TASKHUB_REDIS_URL` | URL Redis của app, mặc định `redis://redis:6379/0` |
| `TASKHUB_LOG_LEVEL` | Mức log, mặc định INFO |
| `TASKHUB_CACHE_TTL_SECONDS` | TTL cache, mặc định 60 |

Compose đọc những biến này từ shell hoặc file truyền qua `docker compose --env-file <file>`. Đó là cơ chế nội suy của Compose, khác với việc Python chọn `.env.prod` bằng APP_ENV.

Trước khi dùng cấu hình production:

1. Đặt `TASKHUB_APP_ENV=prod`.
2. Tạo key bằng `python -c "import secrets; print(secrets.token_urlsafe(48))"`, lưu vào `TASKHUB_SECRET_KEY` qua hệ thống quản lý cấu hình của môi trường triển khai.
3. Đặt password DB riêng và cập nhật đồng thời `TASKHUB_POSTGRES_PASSWORD`, `TASKHUB_DATABASE_URL` cho khớp. Với volume đã tồn tại, thay biến `POSTGRES_PASSWORD` không tự đổi password trong PostgreSQL.
4. Cấu hình Redis/TLS, reverse proxy HTTPS, backup và phân quyền hạ tầng theo môi trường thực tế. Compose đi kèm phục vụ chạy thử một stack trên một máy, chưa thay thế cấu hình triển khai production hoàn chỉnh.

Nếu chỉ chuyển APP_ENV sang prod mà giữ key dev, app sẽ dừng đúng yêu cầu fail-fast. `.env.prod.example` cố tình chứa placeholder và không thể dùng nguyên trạng để khởi động app. Docs production mặc định tắt; khi cần bật tạm, truyền `DOCS_ENABLED=true` vào môi trường container qua Compose override.

Migration tự chạy ở mỗi lần container app khởi động. Với một app instance, Alembic chạy lại `upgrade head` là thao tác không tạo migration mới. Nếu triển khai nhiều replica, cần tách bước migration thành job chạy một lần trước rollout để tránh chạy đồng thời.

## Kiểm thử

```powershell
venv/Scripts/python.exe -m pip install -r requirements-dev.txt
venv/Scripts/python.exe -m pytest -q test -p no:cacheprovider
venv/Scripts/ruff.exe check app test alembic scripts
docker compose config --quiet
```

Test tự chọn `APP_ENV=test`, SQLite in-memory và fakeredis, không cần PostgreSQL/Redis thật. Nếu Windows chặn thư mục temp mặc định, tạo `.pytest_tmp` rồi thêm `--basetemp=.pytest_tmp/<ten-lan-chay-moi>` vào lệnh pytest; luôn dùng thư mục dành riêng cho pytest vì pytest có thể dọn thư mục đó.

Kiểm thử UI thật, sau khi Docker đã healthy:

```powershell
venv/Scripts/python.exe -m pip install -r requirements-browser.txt
venv/Scripts/python.exe scripts/smoke_swagger.py --channel msedge
```

Nếu không có Edge, cài Chromium bằng `venv/Scripts/python.exe -m playwright install chromium`, rồi chạy script không có `--channel`. Script chỉ chấp nhận host loopback, tạo một tài khoản thử với email ngẫu nhiên, thao tác đăng ký/đăng nhập/Authorize trong Swagger, kiểm tra `/users/me`, `/health` và ReDoc. Tài khoản thử được giữ trong DB của stack kiểm thử.

## Phạm vi Day 7 và PR

Nhánh: `feature/day7-docs-docker`. Nhánh được tạo từ Day 6 khi PR #7 chưa merge. Khi code còn chưa commit, dùng `git status --short` để xem cả file mới và `git diff feature/day6-cache-logging` để xem thay đổi ở các file đã được Git theo dõi. Sau khi commit Day 7, xem diff riêng giữa hai nhánh bằng:

```bash
git diff feature/day6-cache-logging...feature/day7-docs-docker
```

Mô tả PR tiếng Việt và checklist review: [docs/PR_DAY7.md](docs/PR_DAY7.md). Kết quả chạy thực tế: [docs/DAY7_VALIDATION.md](docs/DAY7_VALIDATION.md).
