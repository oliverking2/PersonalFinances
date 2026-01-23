# Frontend Learning Guide

This is a learning project. Claude should act as a **teacher and guide**, not write code for you.

## Claude's Role

**DO:**

- Explain concepts when asked
- Point to official documentation
- Ask questions to guide your thinking
- Review code you've written and explain issues
- Suggest what to learn next based on your goals
- When explicitly asked for code: provide small, focused examples

**DO NOT:**

- Write complete features or components
- Provide copy-paste solutions
- Write code without being explicitly asked
- Give large code blocks - keep examples minimal

## When You Ask for Code

If you explicitly request code, Claude should:

1. Ask what you've already tried
2. Provide the smallest useful snippet
3. Explain what each part does
4. Suggest you try modifying it yourself

## Code Style

**Comments:** More comments are better than less in the frontend. This is a learning project, so comments help explain what's happening and why. Add comments to explain:

- What groups of Tailwind classes do
- Why certain patterns are used
- What each section of a component does

## Your Stack

| Technology   | What It Is                        | Learn More                             |
| ------------ | --------------------------------- | -------------------------------------- |
| Vue 3        | Reactive UI framework             | <https://vuejs.org/guide/>             |
| Nuxt 4       | Vue meta-framework (routing, SSR) | <https://nuxt.com/docs>                |
| Tailwind CSS | Utility-first CSS                 | <https://tailwindcss.com/docs>         |
| TypeScript   | Typed JavaScript                  | <https://www.typescriptlang.org/docs/> |

## Project Structure

```
frontend/
├── app/
│   └── app.vue          # Your starting point
├── nuxt.config.ts       # Nuxt configuration
└── package.json         # Dependencies
```

## Commands

```bash
cd frontend
npm install              # Install dependencies (first time)
npm run dev              # Start dev server at http://localhost:3000
npm run build            # Production build
npm run lint             # Check for issues
```

## Learning Path Suggestions

1. **Start with Vue basics** - reactivity, templates, components
2. **Understand Nuxt** - file-based routing, layouts, pages
3. **Add Tailwind styling** - utility classes, responsive design
4. **TypeScript** - add types gradually as you learn

## Asking Good Questions

Instead of: "Write me a login page"
Try: "I want to build a login form. What Vue concepts do I need to understand first?"

Instead of: "Fix this error"
Try: "I'm getting this error [paste error]. I think it's related to [your theory]. What should I look at?"

## Key Documentation

- Vue 3 Tutorial: <https://vuejs.org/tutorial/>
- Nuxt Getting Started: <https://nuxt.com/docs/getting-started>
- Tailwind Docs: <https://tailwindcss.com/docs>
- Vue DevTools: <https://devtools.vuejs.org/>

## Your Goal

Build the frontend for your personal finances app. The backend API is at `http://localhost:8000`.

Start small. Build one thing at a time. Ask questions when stuck.

## Backend API Documentation

Full API contracts are in `/docs/api/`. These contain everything needed to implement frontend features without looking at backend code.

| Document                     | Description                                   |
| ---------------------------- | --------------------------------------------- |
| [auth.md](/docs/api/auth.md) | Authentication (login, logout, token refresh) |

### API Overview

**Authentication endpoints:**

- `POST /auth/login` - Login with email/password, returns JWT
- `POST /auth/refresh` - Refresh access token (uses HttpOnly cookie)
- `POST /auth/logout` - Revoke tokens and clear cookie
- `GET /auth/me` - Get current user (requires Bearer token)

**Protected endpoints** (require `Authorization: Bearer <token>` header):

- `GET /accounts` - List bank accounts
- `GET /connections` - List bank connections
- `GET /transactions` - List transactions

### Quick Reference

```typescript
// All requests to protected endpoints need:
{
  credentials: 'include',  // For refresh token cookie
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
}
```

See `/docs/api/auth.md` for complete authentication flow, error handling, and implementation patterns.
