# Product Requirements Documents (PRDs)

This folder contains PRDs for features in the Personal Finances project.

## Process

1. **Create a PRD** before starting work on non-trivial features
2. **Use the template**: Copy `_template.md` and rename to `YYYYMM-feature-name.md`
3. **Review**: Share for feedback before implementation
4. **Update status**: Keep the PRD status current as work progresses

## Naming Convention

```
YYYYMM-feature-name.md
```

Examples:
- `202601-fastapi-backend.md`
- `202602-vue-frontend.md`
- `202603-vanguard-integration.md`

## Status Values

| Status      | Description                           |
|-------------|---------------------------------------|
| Draft       | Initial writing, not ready for review |
| In Review   | Ready for feedback                    |
| Approved    | Approved for implementation           |
| In Progress | Currently being implemented           |
| Complete    | Feature shipped                       |
| Abandoned   | Decided not to proceed                |

## When to Write a PRD

Write a PRD for:
- New major features
- Significant architectural changes
- External integrations
- Features spanning multiple phases

Skip PRDs for:
- Bug fixes
- Minor UI tweaks
- Refactoring without behaviour changes
- Documentation updates
