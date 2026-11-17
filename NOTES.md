# TaskHub — Báo cáo Day 4 và Day 5

Ngày cập nhật: Thứ Ba, 17/11/2026 (Asia/Saigon).

## Kết quả kiểm tra dự án

Day 4 đã có ở commit `6f2ead4`, nhánh `feature/day4-rbac`,
PR https://github.com/nhungoc16005/taskhub/pull/5 (đang mở khi kiểm tra).
Nhánh Day 5 ban đầu xuất phát từ Day 3 nên thiếu phần nền Day 4 và không import
được ứng dụng. Đã đưa lại nền Day 4 và hoàn thiện phần Day 5 viết dở.

## Day 4 — Authorization & RBAC

- Workspace CRUD; danh sách workspace của tôi với `skip + limit`.
- Tạo workspace và member OWNER trong cùng transaction.
- Mời member bằng email, mặc định VIEWER; chỉ nhận EDITOR/VIEWER.
- Xem/xóa member; không xóa OWNER.
- Project CRUD, archive, lọc status và phân trang.
- Quyền tập trung ở `WorkspaceService.get_with_role`, thứ bậc trong
  `core/permissions.py`; project kế thừa quyền từ workspace.
- ADMIN có toàn quyền theo ID. Danh sách workspace vẫn là danh sách tham gia.
- Người ngoài nhận 404, member thiếu quyền nhận 403.
- Giữ lại 30 test Day 4 gốc.

## Day 5 — Task, Label, Comment, Filtering & Pagination

- Task CRUD: TODO/MEDIUM mặc định, created_by từ người đăng nhập, due_date,
  status, priority, gán/bỏ gán assignee.
- Assignee phải là member của workspace; không tạo task trong project ARCHIVED.
- Lọc đồng thời status/priority/assignee_id; trả items/total/skip/limit.
- Label CRUD, kiểm tra màu hex, gán/bỏ gán label cùng project.
- Comment: tạo, xem có phân trang, xóa theo quyền tác giả hoặc OWNER/ADMIN.
- Đổi role member bằng PATCH; chỉ OWNER/ADMIN, không đổi role OWNER.
- Xóa member tự bỏ gán các task của member trong workspace đó.
- Xử lý rollback khi update dữ liệu lỗi và khi gán label trùng.
- Kiểm thử thêm các vai trò, người ngoài, validation, lọc/phân trang,
  quyền sở hữu và xóa dây chuyền dữ liệu.

## Quy ước đã áp dụng

- Giữ `skip + limit` để tương thích các ngày trước; chưa chuyển sang page.
- Người tạo task còn là member hoặc OWNER/ADMIN được xóa task.
- EDITOR trở lên được viết comment; VIEWER chỉ đọc.
- Archive chặn tạo task mới; vẫn cho cập nhật task hiện có.
- Không có migration mới; dùng các bảng đã tạo từ Day 2.

## Kiểm tra

```powershell
venv/Scripts/python.exe -m pytest -q
```

Test dùng SQLite in-memory, bật foreign key; bcrypt 4 vòng chỉ trong test.
Kết quả: **123 passed in 22.53s** (58 test nền Day 1–4, thêm 65 test).
Chưa kiểm thử tích hợp với PostgreSQL thật.

## Báo cáo công việc

- Thời gian làm việc: Thứ Ba, 17/11/2026.
- Actual work: chưa có số giờ/giờ bắt đầu và kết thúc do người dùng xác nhận.
- Task hoàn thành: các mục Day 4 và Day 5 ở trên.
- Day 4 PR: https://github.com/nhungoc16005/taskhub/pull/5.
- Day 5: nhánh `feature/day5-tasks`, PR https://github.com/nhungoc16005/taskhub/pull/6,
  dựa trên `feature/day4-rbac`.
- Tomorrow plan: review/merge Day 4 trước, đổi base Day 5 về main sau khi
  Day 4 được merge; xác nhận quy ước phân trang với thầy.
- Khó khăn đã xử lý: Day 5 thiếu nền Day 4; sandbox chặn Python gốc nên
  cần chạy test ngoài sandbox.
