# Change Discipline

## Before Writing Code

1. Read the code you're modifying first
2. Look for existing patterns and match them
3. Check `ROADMAP.md` and `prds/` for context

## Avoid Over-Engineering

- Only make requested changes
- Don't add features, refactoring, or "improvements" beyond scope
- Don't add error handling for impossible scenarios
- Don't create abstractions for one-time operations
- Three similar lines > premature abstraction
- If something is unused, delete it completely (no `_var` renames or `# removed` comments)

## Breaking Changes

1. Propose non-breaking alternative first
2. Explain trade-offs
3. Get explicit approval before proceeding

## Security

Watch for: command injection, XSS, SQL injection, path traversal. Fix immediately if noticed.

## After Changes

1. Run `make check` in backend/
2. Update `README.md` if behaviour changed
3. Update `ROADMAP.md` if feature completed

## When Uncertain

Ask a targeted question instead of guessing.
