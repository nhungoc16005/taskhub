API_DESCRIPTION = """
API quản lý công việc theo workspace: người dùng, thành viên, project, task, label và comment.

### Đăng nhập và thử API

1. Gọi **POST /api/v1/auth/register** để tạo tài khoản.
2. Gọi **POST /api/v1/auth/login** với form: `username` là email, `password` là mật khẩu.
3. Sao chép `access_token`, bấm **Authorize**, dán token (không thêm `Bearer`) và xác nhận.
4. Gọi **GET /api/v1/users/me** để kiểm tra rồi tạo workspace, project và task.

### Quyền truy cập

- OWNER quản lý workspace và thành viên; EDITOR được chỉnh sửa nội dung; VIEWER chỉ đọc.
- Người ngoài workspace nhận 404 để không tiết lộ tài nguyên; thành viên thiếu quyền nhận 403.
- Project đã archive không cho phép thay đổi nội dung và trả 409.

### Phân trang, cache và lỗi

Danh sách dùng `skip`, `limit` và trả `items`, `total`, `skip`, `limit`.
Danh sách task hỗ trợ lặp lại `status`, `priority` và lọc `assignee_id`.
Cache chỉ lưu dữ liệu; quyền truy cập luôn được kiểm tra trước khi đọc cache.
Lỗi nghiệp vụ trả `{"detail": "..."}`; lỗi 422 giữ danh sách lỗi validation của FastAPI.
Response có `X-Request-ID` để đối chiếu log. Email gán task hiện chỉ được ghi log ở chế độ dev.
"""

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Đăng ký, đăng nhập, làm mới access token và đăng xuất bằng refresh token.",
    },
    {
        "name": "users",
        "description": "Hồ sơ cá nhân, đổi mật khẩu và quản lý người dùng theo quyền ADMIN.",
    },
    {
        "name": "workspaces",
        "description": "Workspace, thành viên và phân quyền OWNER / EDITOR / VIEWER.",
    },
    {
        "name": "projects",
        "description": "Project thuộc workspace; hỗ trợ archive để khóa chỉnh sửa.",
    },
    {
        "name": "tasks",
        "description": "Task, người được gán, trạng thái, độ ưu tiên, filter và phân trang có cache Redis.",
    },
    {
        "name": "labels",
        "description": "Nhãn thuộc project và thao tác gắn hoặc gỡ nhãn trên task.",
    },
    {
        "name": "comments",
        "description": "Bình luận trên task; quyền xóa phụ thuộc tác giả hoặc OWNER.",
    },
    {
        "name": "health",
        "description": "Kiểm tra tiến trình API đang phục vụ; không phải kiểm tra kết nối DB/Redis.",
    },
]

REGISTER_EXAMPLE = {
    "email": "student@example.com",
    "full_name": "Nguyen Van An",
    "password": "TaskHub-demo-2026!",
}
LOGIN_EXAMPLE = {"username": "student@example.com", "password": "TaskHub-demo-2026!"}
WORKSPACE_EXAMPLE = {"name": "TaskHub Study Team"}
TASK_EXAMPLE = {
    "title": "Hoàn thành tài liệu API",
    "description": "Kiểm tra Swagger và ReDoc cho Day 7",
    "priority": "MEDIUM",
    "assignee_id": None,
    "due_date": None,
}
