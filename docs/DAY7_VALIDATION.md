# Kiểm chứng Day 7

Hoàn tất kiểm tra ngày 23/11/2026 (Asia/Saigon), trên nhánh `feature/day7-docs-docker`.

## Môi trường kiểm tra

- Máy Windows, Docker Desktop với Linux containers.
- Project Compose riêng: `taskhub-day7-check`, dùng cùng `docker-compose.yml` của dự án.
- Python container: 3.12 slim bookworm; PostgreSQL 16; Redis 7.4.
- Unit/API tests: Python trong virtualenv, SQLite in-memory và fakeredis.
- UI smoke: Playwright 1.65.2 với Microsoft Edge headless. Trình duyệt tích hợp của phiên làm việc không khả dụng nên dùng trình duyệt cục bộ.

## Test tự động

```powershell
venv/Scripts/python.exe -m pytest -q test -p no:cacheprovider --basetemp=.pytest_tmp/day7-final-20261123-a --tb=short
```

Kết quả: **259 passed in 25.33s**. Trong đó 183 test có sẵn và 76 test Day 7. `--basetemp` là điều chỉnh cho máy kiểm thử do thư mục temp mặc định của pytest bị từ chối truy cập; không phải yêu cầu của ứng dụng.

```powershell
venv/Scripts/ruff.exe check app test alembic scripts --output-format concise
git diff --check
```

Kết quả: **All checks passed**, không có lỗi whitespace trong diff.

## Docker thật

```bash
docker compose -p taskhub-day7-check up -d --build --wait --wait-timeout 120
docker compose -p taskhub-day7-check ps
docker compose -p taskhub-day7-check exec -T app id
docker compose -p taskhub-day7-check exec -T app alembic current
```

Kết quả: app, db, redis healthy; app phục vụ ở `127.0.0.1:8000`; user `uid=10001(taskhub)`; migration `a24d5e9b0011 (head)`. Image build được bằng dependencies runtime riêng; không cần Python virtualenv của máy host trong image.

## Swagger và ReDoc thật

```powershell
venv/Scripts/python.exe scripts/smoke_swagger.py --channel msedge
```

Kết quả:

```text
PASS: /health, Swagger register 201, login 200, Authorize + /users/me 200, ReDoc rendered
```

Script thao tác trên giao diện Swagger: mở operation, Try it out, điền dữ liệu, Execute, nhập access token vào Authorize, rồi gọi endpoint được bảo vệ. ReDoc được xác nhận đã render tiêu đề tài liệu, không chỉ kiểm tra response HTML. Không ghi access token vào output.

## Fail-fast trên container

```bash
docker compose -p taskhub-day7-check run --rm --no-deps -e APP_ENV=prod app
```

Với key dev mặc định, container thoát khác 0 trước migration/server. Lỗi xác định đúng nguyên nhân:

```text
SECRET_KEY in prod must be a randomly generated secret, not a sample or a repetitive value
```

Các trường hợp thiếu SECRET_KEY/DATABASE_URL, DB_ECHO ở prod, Redis chưa khai báo ở prod, URL sai và chính sách docs được kiểm tra trong test tự động.

## PostgreSQL giữ dữ liệu khi tạo lại container

Đếm số bản ghi users trong stack kiểm thử, chạy `docker compose -p taskhub-day7-check down` rồi `up -d --wait --wait-timeout 120`, sau đó đếm lại.

Kết quả: **3 users trước và sau khi tạo lại container**, ba service healthy, app vẫn dùng UID 10001 và migration ở head. Không dùng `down -v`, không xóa volume. Kiểm tra này xác nhận dữ liệu được lưu ở named volume thay vì filesystem tạm của container.

Sau khi kiểm tra, stack riêng được dừng bằng `down` để giải phóng cổng 8000; volume kiểm thử được giữ nguyên.

## Cách kiểm tra lại

Khi chia commit, nội dung đã stage được xuất bằng `git write-tree` và `git archive` vào thư mục riêng, không lấy các file chưa stage trong working tree:

- Snapshot commit cấu hình: **236 test pass**, Ruff pass (183 test nền + 53 test cấu hình).
- Snapshot sau commit Swagger/OpenAPI: **259 test pass**, Ruff pass (thêm 23 test OpenAPI).
- Commit Docker bổ sung đóng gói, dependencies và tài liệu; code ứng dụng/test giữ nguyên nội dung đã kiểm tra. Kết quả chạy Docker và UI thật được ghi ở các mục trên.

- Docker default: `docker compose up --build`.
- Nếu dùng tên project khác, giữ `-p <tên>` nhất quán trong các lệnh.
- Stop stack bằng `docker compose -p taskhub-day7-check down`; lệnh này giữ volume.
- Chỉ dùng `down -v` khi chủ động muốn xóa dữ liệu kiểm thử.
- Kết quả trên là kiểm thử local, không phải kết quả CI GitHub. Nhánh Day 7 chưa push, chưa mở PR.
