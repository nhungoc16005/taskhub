# feat(day7): hoàn thiện Swagger/ReDoc, cấu hình đa môi trường và Docker

## Vấn đề và kết quả

Dự án đã có các API nghiệp vụ nhưng thiếu quy trình chạy thống nhất bằng Docker, cấu hình tách theo môi trường và tài liệu API đầy đủ để thử xác thực trực tiếp. Thay đổi này bổ sung stack PostgreSQL + Redis + app chạy bằng `docker compose up --build`, kiểm tra cấu hình trước startup và hoàn thiện Swagger/ReDoc.

Ví dụ: trước đây chưa có kiểm tra riêng cho cấu hình production; nay `APP_ENV=prod` với key mẫu hoặc `DB_ECHO=true` sẽ bị từ chối trước khi server nhận request. Trên Swagger, người dùng đăng nhập bằng form, dán `access_token` vào Authorize và gọi được các endpoint có bảo vệ.

## Phạm vi thay đổi

### 1. Configuration đa môi trường

- Thêm `APP_ENV`: `dev`, `test`, `prod`; mặc định `dev`.
- Chọn `.env.dev`, `.env.test`, `.env.prod` theo APP_ENV của process; riêng dev hỗ trợ fallback `.env` cũ nếu không có `.env.dev`.
- Không lấy cấu hình thiếu từ file của môi trường khác. Biến process ưu tiên hơn file; tham số khởi tạo Settings ưu tiên hơn biến process.
- Kiểm tra DATABASE_URL theo driver PostgreSQL asyncpg, thông tin kết nối và port; SQLite aiosqlite chỉ được phép trong test.
- Kiểm tra REDIS_URL: scheme redis/rediss, host, port và chỉ số DB; không nhận query string hoặc fragment.
- Production bắt buộc SECRET_KEY đủ độ dài, không phải mẫu hoặc chuỗi lặp đơn giản; DB_ECHO phải tắt; REDIS_URL phải được cấu hình rõ.
- Giới hạn TTL/token lifetime ở số dương và thuật toán JWT ở HS256.
- Thêm DOCS_ENABLED: mặc định bật ở dev/test, tắt ở prod; có thể ghi đè rõ ràng.
- Bổ sung các file `.env.*.example`; bỏ qua file môi trường thật trong Git và Docker context. Không đưa giá trị đầu vào nhạy cảm vào chuỗi lỗi validation.

### 2. Swagger/ReDoc và OpenAPI

- Bổ sung title, mô tả, version 0.7.0 và mô tả cho 8 nhóm endpoint.
- Dùng HTTP Bearer JWT cho nút Authorize. Endpoint login vẫn giữ form `username=email` và `password`; không thay đổi hợp đồng đăng nhập.
- Bổ sung summary và ví dụ request cho đăng ký, đăng nhập, tạo workspace, tạo task.
- Dùng chung khai báo schema/response lỗi tại `app/api/responses.py`; nhóm auth chọn mã phù hợp, các nhóm tài nguyên dùng bộ lỗi chung.
- Các lỗi nghiệp vụ giữ `{"detail": "..."}`. Lỗi 422 được mô tả bằng `ValidationErrorResponse` với danh sách lỗi FastAPI, giữ tương thích client và test hiện có.
- Header WWW-Authenticate và status 401 vẫn được giữ cho request thiếu/sai token.
- Tắt cả `/docs`, `/redoc`, `/openapi.json` khi docs bị vô hiệu hóa; `/health` vẫn hoạt động.

### 3. Docker và dependencies

- Dockerfile multi-stage: build dependencies trong virtualenv riêng, copy sang runtime Python 3.12 slim.
- Chạy app bằng user không phải root, UID/GID 10001.
- Compose có app, PostgreSQL 16 và Redis 7.4; app phụ thuộc healthcheck của DB/Redis và có healthcheck `/health` riêng.
- PostgreSQL dùng named volume. Redis chỉ lưu cache, không bật persistence.
- Entrypoint kiểm tra cấu hình, chạy `alembic upgrade head`, sau đó `exec` Uvicorn; cấu hình/migration lỗi sẽ chặn startup.
- Không publish cổng DB/Redis ra máy; API mặc định bind `127.0.0.1:8000`.
- Tách dependencies runtime, test/dev và browser smoke test; container không cài pytest, fakeredis, Ruff hoặc Playwright.
- Alembic escape dấu `%` trong URL trước khi đưa vào ConfigParser, hỗ trợ mật khẩu đã URL-encode; không tạo migration mới và không thay đổi schema.

### 4. Test và tài liệu

- Thêm 76 test cho configuration và OpenAPI: cấu hình bắt buộc, key yếu, URL, thứ tự ưu tiên, cô lập môi trường, docs production, schema lỗi, examples và Bearer authentication.
- Thêm script smoke test thao tác thực trên Swagger bằng Playwright; chỉ chấp nhận địa chỉ local và dùng tài khoản thử ngẫu nhiên.
- README tiếng Việt hướng dẫn Docker, cấu hình local/prod, Swagger, test, volume và troubleshooting cơ bản.
- Ghi lại kiểm chứng thực tế tại `docs/DAY7_VALIDATION.md`.

## Cách chạy và review

```bash
docker compose up --build
```

Mở `http://localhost:8000/docs`; đăng ký → đăng nhập → sao chép access_token → Authorize → gọi GET `/api/v1/users/me`. ReDoc nằm ở `/redoc`; kiểm tra tiến trình ở `/health`.

```bash
docker compose ps
docker compose exec app id
docker compose exec app alembic current
```

Kiểm thử tự động:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q test -p no:cacheprovider
python -m ruff check app test alembic scripts
```

Kiểm thử UI tùy chọn trên Windows có Edge:

```bash
python -m pip install -r requirements-browser.txt
python scripts/smoke_swagger.py --channel msedge
```

## Kết quả xác minh

- 259 test pass: 183 test nền + 76 test Day 7.
- Ruff pass cho app, test, alembic và scripts.
- Docker build và khởi động thật thành công; ba service healthy.
- App chạy bằng UID 10001; PostgreSQL migration ở `a24d5e9b0011 (head)`.
- Swagger thực hiện thành công register 201, login 200, Authorize và `/users/me` 200; ReDoc render; `/health` 200.
- Container production từ chối key dev trước khi chạy server.
- Tạo lại toàn bộ container bằng `down` rồi `up` (giữ volume): 3 tài khoản thử vẫn còn, app healthy và migration vẫn ở head.

## Phụ thuộc và giới hạn

- Nhánh `feature/day7-docs-docker` được tạo từ Day 6 khi PR #7 chưa merge. Khi mở PR, nếu Day 6 chưa merge thì dùng nhánh Day 6 làm base; nếu đã merge thì cập nhật theo main và kiểm tra diff chỉ chứa Day 7.
- Compose đi kèm là stack dev/demo một máy, chưa phải bộ triển khai production hoàn chỉnh. Cần cấu hình secret riêng, TLS/reverse proxy và backup phù hợp khi triển khai thật.
- `/health` là kiểm tra liveness của API, không khẳng định kết nối DB/Redis luôn sẵn sàng.
- Migration tự động phù hợp một app instance; triển khai nhiều replica cần job migration riêng trước rollout.
- Swagger/ReDoc tải tài nguyên giao diện từ CDN mặc định của FastAPI; kiểm thử giao diện cần truy cập được CDN.
- Quyết định dùng file riêng theo APP_ENV, tắt docs mặc định ở prod, tự chạy migration và triển khai Docker optional cần được đối chiếu với yêu cầu của thầy.

## Cấu trúc commit

1. `feat(config): validate settings for dev, test and production` — cấu hình, file example, tắt/bật docs theo môi trường, xử lý URL Alembic và 53 test cấu hình.
2. `docs(api): complete OpenAPI and Swagger bearer authorization` — metadata, response schema, examples, auth dependency và 23 test OpenAPI.
3. `build(docker): package the app with PostgreSQL and Redis` — Docker, dependencies, smoke script và tài liệu kiểm chứng.

Các commit được sắp xếp theo phụ thuộc: cấu hình → tài liệu API → đóng gói Docker. Phần thay đổi chung trong constants và app factory được stage riêng theo mục đích. File này là bản mô tả PR chuẩn bị sẵn tại local; chưa tạo PR hoặc push nhánh Day 7.
