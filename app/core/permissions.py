from app.models.workspace import WorkspaceRole

# Càng cao càng nhiều quyền: VIEWER < EDITOR < OWNER
WORKSPACE_ROLE_RANK: dict[WorkspaceRole, int] = {
    WorkspaceRole.VIEWER: 1,
    WorkspaceRole.EDITOR: 2,
    WorkspaceRole.OWNER: 3,
}


def has_workspace_role(actual: WorkspaceRole, required: WorkspaceRole) -> bool:
    return WORKSPACE_ROLE_RANK[actual] >= WORKSPACE_ROLE_RANK[required]
