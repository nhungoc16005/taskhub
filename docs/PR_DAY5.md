Hoàn thiện Task, Label, Comment và cập nhật member trên nền RBAC Day 4.

## Chức năng

- Task CRUD; created_by từ user đăng nhập, TODO/MEDIUM mặc định, due_date,
  status, priority, gán/bỏ gán assignee là member workspace.
- Chặn tạo task trong project ARCHIVED.
- Lọc status/priority/assignee_id; phân trang skip + limit, trả items/total.
- Label CRUD, validate màu hex, gán/bỏ gán label cùng project.
- Comment tạo/xem/phân trang/xóa; EDITOR trở lên được viết comment.
- Người tạo task còn là member hoặc OWNER/ADMIN được xóa task.
- Tác giả comment hoặc OWNER/ADMIN được xóa comment.
- PATCH role member cho OWNER/ADMIN; bảo vệ OWNER. Xóa member tự bỏ gán task.
- Rollback khi update dữ liệu lỗi và khi liên kết label trùng.

## Kiểm chứng

`venv/Scripts/python.exe -m pytest -q`: **123 passed in 22.53s**.
Giữ 58 test nền Day 1–4, thêm 65 test: phân quyền, 404/403, validation,
lọc/phân trang, ownership, label khác project, xóa dây chuyền.
SQLite in-memory với foreign keys bật; bcrypt 4 vòng chỉ trong test.
Chưa kiểm thử PostgreSQL thật. Không có migration mới.

## Phụ thuộc

Base: `feature/day4-rbac` vì PR #5 đang mở. Merge Day 4 trước rồi đổi base
Day 5 về main. Giữ skip + limit tương thích API cũ. Archive chỉ chặn tạo task mới.
Báo cáo công việc trong NOTES.md; actual work chưa có số giờ do người dùng cung cấp.
