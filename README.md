# TaskHub

## Kiến trúc và quyết định thiết kế

Luồng xử lý: **API/dependency → service → repository → SQLAlchemy model → DB**.
`app/api` nhận request và gắn dependency xác thực; `app/schemas` mô tả dữ liệu
Pydantic; `app/services` xử lý nghiệp vụ, phân quyền và chuyển schema thành dữ liệu
cập nhật; `app/repositories` truy vấn/lưu dữ liệu; `app/models` khai báo bảng và quan hệ.
`app/core` chứa cấu hình, bảo mật, cache, logging và các thành phần dùng chung.

`resolve_nested_resource` thống nhất cách tìm tài nguyên con và kiểm tra quyền qua
cha. `ProjectResourcePolicy` dùng chung cho task/label; dependency `require_role`
khai báo vai trò cần thiết ngay tại route. Không gộp các quy tắc nghiệp vụ khác nhau
chỉ vì chúng có cùng tên hàm. `update_from_schema` dùng `exclude_unset=True` để
PATCH phân biệt trường không gửi với trường gửi `null`; repository chỉ nhận dict,
không phụ thuộc Pydantic.

`BaseRepository` dùng chung CRUD và commit cho thao tác đơn. Với task, label,
comment, `TransactionalRepository` chỉ flush: service điều phối commit/rollback
cho nhiều thao tác liên quan, rồi mới vô hiệu hóa cache. Một số repository chuyên
biệt như membership quản lý khóa ghép và các thao tác riêng; không ép chúng vào
CRUD theo ID đơn. Đây là quy ước hiện tại, chưa phải Unit of Work thống nhất toàn ứng dụng.

### Schema và tính toàn vẹn

| Bảng | Vai trò và ràng buộc chính |
| --- | --- |
| `users` | Tài khoản, email duy nhất, mật khẩu băm, vai trò hệ thống và trạng thái hoạt động |
| `workspaces` | Không gian làm việc, tham chiếu chủ sở hữu |
| `workspace_members` | Quan hệ user–workspace; khóa chính ghép `(workspace_id, user_id)`, vai trò OWNER/EDITOR/VIEWER |
| `projects` | Thuộc workspace, hỗ trợ archive |
| `tasks` | Thuộc project, người tạo, người được giao, trạng thái, ưu tiên và hạn hoàn thành |
| `labels` | Thuộc project; tên duy nhất trong cùng project |
| `task_labels` | Bảng nối nhiều–nhiều task/label, khóa ghép ngăn gắn trùng |
| `comments` | Thuộc task, tham chiếu tác giả |
| `refresh_tokens` | Lưu JTI, thời hạn và trạng thái thu hồi refresh token |

Khóa ngoại và unique constraint bảo vệ dữ liệu ngay tại DB. Các cột quan hệ dùng
để tìm kiếm có index; không thêm index cho mọi cột vì tăng chi phí ghi và dung lượng.
Xóa project kéo theo tài nguyên con; xóa assignee đặt `tasks.assignee_id` về NULL,
trong khi tham chiếu người tạo task dùng RESTRICT. Migration là nguồn lịch sử schema:
chạy `alembic upgrade head`, không sửa migration đã áp dụng để đổi cấu trúc mới.

### Phân quyền và xác thực

Vai trò hệ thống ADMIN có quyền vượt kiểm tra membership. Trong workspace,
OWNER quản lý thành viên và tài nguyên, EDITOR được thao tác ghi được cho phép,
VIEWER chỉ đọc. Quy tắc tác giả/chủ sở hữu được kiểm tra thêm ở thao tác tương ứng.
Tài nguyên ngoài workspace người gọi được trả 404 để tránh tiết lộ sự tồn tại;
thành viên thiếu quyền nhận 403. Project đã archive chặn thao tác ghi kể cả ADMIN.
Tài khoản bị khóa không được tiếp tục sử dụng API bảo vệ.

Access token JWT mặc định sống 30 phút, refresh token 7 ngày. Refresh token có
JTI lưu tại DB để hỗ trợ thu hồi; logout và đổi mật khẩu áp dụng thu hồi theo
nghiệp vụ tương ứng. Không lưu mật khẩu thô. Bcrypt chạy qua `asyncio.to_thread`
ở đăng ký, đăng nhập và đổi mật khẩu, để công việc CPU không chặn event loop.
Thread không làm giảm chi phí bcrypt; tải đăng nhập lớn vẫn cần giới hạn lưu lượng
ở tầng triển khai và đo CPU/thread pool trên môi trường thực tế.

### Cache và truy vấn

Redis cache danh sách task với TTL mặc định 60 giây. Key phân biệt project,
phiên bản và các tham số lọc/phân trang/sắp xếp. Quyền truy cập được kiểm tra
**trước** khi đọc cache; cache không thay thế authorization. Sau khi transaction
ghi thành công, service invalidation cache. Redis lỗi thì API dùng DB; invalidation
là best-effort, nên worker khác có thể thấy dữ liệu cũ tới hết TTL.

Danh sách task trả các trường scalar, không tải từng quan hệ trong vòng lặp.
Danh sách thành viên dùng `selectinload(user)` để tránh N+1. Kiểm thử Day 8 đếm
hai truy vấn cho một trang task kèm count (cả 1 và 12 task), và hai truy vấn cho
danh sách 8 thành viên kèm dữ liệu user. Đây là kiểm tra đường truy vấn cụ thể,
không phải khẳng định mọi endpoint luôn có hai truy vấn.

Migration `e5b7218cf012` thêm index `(project_id, status, priority, id)` cho lọc
đồng thời project/status/priority và sắp xếp theo ID. Index này không thay thế
mọi index hay tối ưu mọi tổ hợp lọc/sort. Test kiểm tra upgrade/downgrade, giữ dữ
liệu và query plan SQLite. Trước triển khai DB lớn, cần đo `EXPLAIN (ANALYZE,
BUFFERS)` trên PostgreSQL với dữ liệu đại diện; tạo index thường có thể chặn ghi.

### Connection pool và đo hiệu năng

| Biến app | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `DB_POOL_SIZE` | 5 | Số connection giữ trong pool, tối thiểu 1 |
| `DB_MAX_OVERFLOW` | 10 | Connection bổ sung khi tải tăng, tối thiểu 0 |
| `DB_POOL_TIMEOUT_SECONDS` | 30 | Thời gian chờ lấy connection, số dương hữu hạn |
| `DB_POOL_RECYCLE_SECONDS` | 1800 | Tuổi connection trước khi tái tạo lúc checkout, tối thiểu 1 |

Compose dùng các biến cùng tên với tiền tố `TASKHUB_`, ví dụ
`TASKHUB_DB_POOL_SIZE=5`. PostgreSQL bật `pool_pre_ping` để kiểm tra connection
trước sử dụng. SQLite test không nhận các tùy chọn pool PostgreSQL. Pool thuộc
từng process: với N worker, trần theo cấu hình mặc định là `N × (5 + 10)` connection;
cần chừa ngân sách DB cho migration và ứng dụng khác. Recycle không ngắt một
transaction đang chạy.

Chạy phép đo độc lập, không truy cập DB hay tài khoản thật:

```powershell
venv/Scripts/python.exe -m scripts.benchmark_bcrypt --rounds 12 --operations 4
```

Kết quả JSON so sánh thời gian tổng và độ trễ lớn nhất của heartbeat event loop
khi bcrypt chạy trực tiếp hoặc trong thread. Số đo phụ thuộc máy/tải; đây không
phải load test HTTP hay cam kết độ trễ production. Test tự động còn xác minh
hash/verify thực sự chạy ngoài thread event loop ở các luồng xác thực.

### Quy chuẩn chất lượng

Ruff lint/format và mypy được cấu hình trong `pyproject.toml`, nhắm Python 3.12.
Mypy kiểm tra cả thân hàm chưa có annotation và không bỏ qua toàn bộ import thiếu
kiểu; dự án dùng gradual typing, chưa bật strict cho mọi hàm. Migration lịch sử
được loại khỏi Ruff để giữ nguyên file đã áp dụng; migration Day 8 được kiểm tra riêng:

```powershell
venv/Scripts/python.exe -m ruff check alembic/versions/e5b7218cf012_task_composite_index.py
venv/Scripts/python.exe -m ruff format --check alembic/versions/e5b7218cf012_task_composite_index.py
```

Để tự sửa format dùng `python -m ruff format .`. Bộ kiểm thử chính ở `test/`;
script đo có mục đích rõ ràng ở `scripts/`. Không dùng các script thử tạm ở root
như `check_db.py` hay `test_jwt.py` làm công cụ vận hành. Pytest dùng riêng
`.pytest_tmp-tests` tại root để chạy ngay trên checkout mới và không dọn nhầm
các artifact khác trong `.pytest_tmp`.

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

Các file môi trường **không trộn lẫn**: thiếu key trong `.env.prod` không lấy key từ `.env.dev` hoặc `.env`. File không bắt buộc tồn tại nếu process environment đã cung cấp đủ cấu hình. `APP_ENV` trong file được đọc và kiểm tra: nếu khác môi trường chọn tường minh qua process hoặc tham số khởi tạo thì ứng dụng dừng. Khi không chọn tường minh, APP_ENV trong file được chọn quyết định các kiểm tra môi trường. Đường dẫn file luôn tính từ thư mục gốc dự án, không phụ thuộc thư mục chạy lệnh.

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

`requirements.txt` chứa dependencies runtime trực tiếp đã ghim phiên bản. `requirements-dev.txt` thêm pytest, SQLite, HTTP client, fakeredis và Ruff. Image runtime không cài bộ test hoặc trình duyệt.

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
venv/Scripts/python.exe -m ruff check .
venv/Scripts/python.exe -m ruff format --check .
venv/Scripts/python.exe -m mypy app
docker compose config --quiet
```

Test tự chọn `APP_ENV=test`, SQLite in-memory và fakeredis, không cần PostgreSQL/Redis thật. Nếu Windows chặn thư mục temp mặc định, tạo `.pytest_tmp` rồi thêm `--basetemp=.pytest_tmp/<ten-lan-chay-moi>` vào lệnh pytest; luôn dùng thư mục dành riêng cho pytest vì pytest có thể dọn thư mục đó.

Chạy production bằng Compose override, bắt buộc khai báo cấu hình riêng:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build
```

Các biến bắt buộc: `TASKHUB_SECRET_KEY`, `TASKHUB_DATABASE_URL`, `TASKHUB_REDIS_URL`, `TASKHUB_POSTGRES_PASSWORD`. Password trong DATABASE_URL phải khớp PostgreSQL; app từ chối password mẫu trong production.

`REDIS_TIMEOUT_SECONDS` (mặc định 0.25, phải dương và hữu hạn) cấu hình thời gian chờ kết nối và đọc Redis. Compose dùng biến `TASKHUB_REDIS_TIMEOUT_SECONDS` tương ứng. Cache là best-effort: khi invalidation thất bại, worker khác có thể đọc dữ liệu cũ tới khi TTL hết hạn; retry trong bộ nhớ chỉ tác dụng trên worker hiện tại.

Email gán task hiện chỉ ghi user_id/task_id, bỏ qua tài khoản bị khóa. Khi tích hợp nhà cung cấp email thật, dùng I/O bất đồng bộ. Traceback lỗi bất ngờ do Uvicorn ghi một lần; access log chứa request ID.

Kiểm thử HTTPX trong `test/test_day7_openapi.py` xác minh đăng ký, đăng nhập, Bearer authorization và schema OpenAPI. Mã 403 trên route cần đăng nhập bao gồm trường hợp tài khoản bị khóa; list users/workspaces không khai 400/404/409. List tài nguyên con vẫn có 404 nếu workspace/project/task cha không tồn tại hoặc không hiển thị với người gọi.
