# Frontend Roadmap

Rebuild the Streamlit UI in Vue 3 + Nuxt 4 + Tailwind CSS.

## Reference: What Streamlit Had

The old Streamlit app provided:

| Page        | Features                                                                                                                          |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Dashboard   | Welcome screen, navigation                                                                                                        |
| Accounts    | List active accounts, status badges (🟢 READY / 🔴 EXPIRED), details modal                                                        |
| Connections | List requisitions, status badges, create new connection (bank selector + name), authorize button, delete, OAuth callback handling |

---

## Milestone 1: Project Foundation

Get the basics working before building features.

- [ ] **1.1 Dev environment** - `npm run dev` starts without errors
- [ ] **1.2 Login page** - Create `pages/login.vue` with email/password form (no auth logic yet)
- [ ] **1.3 Layouts** - Create `layouts/default.vue` with header + sidebar navigation
- [ ] **1.4 Pages setup** - Create pages: `pages/index.vue` (dashboard), `pages/accounts.vue`, `pages/connections.vue`
- [ ] **1.5 Navigation** - Sidebar links using `<NuxtLink>`, highlight active page
- [ ] **1.6 Auth state** - Create `composables/useAuth.ts` to track logged-in status
- [ ] **1.7 Route protection** - Redirect to `/login` if not authenticated
- [ ] **1.8 API composable** - Create `composables/useApi.ts` for backend calls (`http://localhost:8000`)

**Learning focus:** File-based routing, layouts, `<NuxtLink>`, composables, `ref`/reactive state

---

## Milestone 2: Accounts Page

Start with the simpler read-only page.

- [ ] **2.1 Fetch accounts** - Call `GET /api/accounts` on page load
- [ ] **2.2 Display list** - Show accounts in a table or card grid
- [ ] **2.3 Status badge** - Component showing READY (green) or EXPIRED (red)
- [ ] **2.4 Loading state** - Show spinner while fetching
- [ ] **2.5 Empty state** - Message when no accounts exist
- [ ] **2.6 Error handling** - Display error message if API fails
- [ ] **2.7 Details modal** - Click account to show full details in modal/dialog

**Learning focus:** `useFetch`/`useAsyncData`, reactive state, conditional rendering, components, props

---

## Milestone 3: Connections Page (Read)

Similar to accounts but with more statuses.

- [ ] **3.1 Fetch connections** - Call `GET /api/connections` on page load
- [ ] **3.2 Display list** - Show connections in table/cards
- [ ] **3.3 Status badges** - Map requisition statuses to colours:
  - 🔵 Created (CR), Selecting (SA), Granting (GA)
  - 🟠 Consent (GC), Authenticating (UA)
  - 🟢 Linked (LN)
  - 🔴 Rejected (RJ), Expired (EX)
- [ ] **3.4 Details modal** - Show connection details (ID, status, dates, auth link)
- [ ] **3.5 Loading/empty/error states** - Consistent with accounts page

**Learning focus:** Component reuse, props for dynamic styling, status mapping

---

## Milestone 4: Connections Page (Write)

Add mutation functionality.

- [ ] **4.1 Delete connection** - Button that calls `DELETE /api/connections/:id`
- [ ] **4.2 Confirmation dialog** - "Are you sure?" before delete
- [ ] **4.3 Refetch after delete** - Update list after successful deletion
- [ ] **4.4 Create connection modal** - Form with:
  - Bank selector dropdown (fetch from `GET /api/institutions`)
  - Friendly name text input
- [ ] **4.5 Submit create** - `POST /api/connections` with selected bank + name
- [ ] **4.6 Redirect to bank** - After create, redirect to GoCardless auth URL
- [ ] **4.7 Authorize button** - For CR/EX status, button to re-trigger auth redirect

**Learning focus:** Forms, `v-model`, form validation, mutations, `$fetch`, `navigateTo`

---

## Milestone 5: OAuth Callback

Handle the return from GoCardless bank authorization.

- [ ] **5.1 Callback page** - Create `pages/callback.vue`
- [ ] **5.2 Extract query params** - Get `ref` (requisition ID) from URL
- [ ] **5.3 Process callback** - Call backend endpoint to finalize connection
- [ ] **5.4 Success redirect** - Navigate to connections page with success message
- [ ] **5.5 Error handling** - Show error if callback fails

**Learning focus:** Route query params, `useRoute`, programmatic navigation

---

## Milestone 6: Dashboard

Build the landing page last (needs data from other pages).

- [ ] **6.1 Account summary** - Count of active accounts, total balance
- [ ] **6.2 Connection status** - Count by status (linked, expired, pending)
- [ ] **6.3 Quick actions** - Links to add connection, view accounts
- [ ] **6.4 Recent activity** - (Optional) Latest transactions preview

**Learning focus:** Aggregating data, dashboard patterns

---

## Milestone 7: Polish

Improve UX and consistency.

- [ ] **7.1 Consistent styling** - Tailwind design system (colours, spacing, typography)
- [ ] **7.2 Toast notifications** - Success/error feedback for actions
- [ ] **7.3 Responsive design** - Works on mobile
- [ ] **7.4 Loading skeletons** - Replace spinners with skeleton loaders
- [ ] **7.5 Keyboard navigation** - Escape closes modals, Enter submits forms

**Learning focus:** UX patterns, Tailwind utilities, accessibility basics

---

## Backend API Endpoints Needed

The frontend assumes these endpoints exist (check `backend/` if missing):

| Method | Endpoint                    | Purpose                                  |
| ------ | --------------------------- | ---------------------------------------- |
| GET    | `/api/accounts`             | List active bank accounts                |
| GET    | `/api/accounts/:id`         | Get single account details               |
| GET    | `/api/connections`          | List requisition links                   |
| GET    | `/api/connections/:id`      | Get single connection details            |
| POST   | `/api/connections`          | Create new connection (returns auth URL) |
| DELETE | `/api/connections/:id`      | Delete connection                        |
| GET    | `/api/institutions`         | List available banks from GoCardless     |
| POST   | `/api/connections/callback` | Process OAuth callback                   |

---

## Tips

1. **Work vertically** - Finish one milestone before starting the next
2. **Commit often** - Small commits for each checkbox
3. **Check the docs** - Vue/Nuxt docs are excellent, use them
4. **Keep components small** - If a component does too much, split it
5. **Run `make check`** - Before considering any milestone complete
