# Product Requirements Documents (PRDs)

This folder contains PRDs for features in the Personal Finances project.

## Process

1. **Create a PRD** before starting work on non-trivial features
2. **Use the template**: Copy `_template.md` and rename following the naming convention
3. **Review**: Share for feedback before implementation
4. **Update status**: Keep the PRD status current as work progresses

## Naming Convention

```
YYYYMMDD-{scope}-feature-name.md
```

### Scopes

| Scope       | Description                                |
|-------------|--------------------------------------------|
| `backend`   | Python/FastAPI/Dagster changes             |
| `frontend`  | Nuxt/Vue changes                           |
| `fullstack` | Changes spanning both backend and frontend |
| `infra`     | Docker, CI/CD, deployment                  |
| `data`      | dbt models, data pipeline changes          |

### Examples

- `20260123-backend-auth-api.md` - Backend authentication API
- `20260124-frontend-dashboard.md` - Frontend dashboard page
- `20260125-fullstack-transaction-view.md` - Full-stack transaction feature
- `20260207-data-spending-aggregations.md` - dbt spending models

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
