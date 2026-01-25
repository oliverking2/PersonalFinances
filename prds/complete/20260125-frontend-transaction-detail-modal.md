# PRD: Transaction Detail Modal

**Status**: Complete
**Author**: Claude
**Created**: 2026-01-25
**Updated**: 2026-01-25

---

## Overview

Add a "More details" button to transaction rows that opens a modal displaying all transaction fields. This provides users with a way to view complete transaction information without cluttering the main list view.

## Problem Statement

Transaction rows currently show limited information (merchant/description, amount, account, tags). Users need a way to view additional details like value date, full description, and category without navigating away from the transaction list.

## Goals

- Allow users to view complete transaction details in a modal
- Enable tag management from within the detail modal
- Maintain consistency with existing modal patterns in the codebase

## Non-Goals

- Transaction editing (amount, date, etc.) - transactions are read-only from bank sync
- Bulk detail view - modal shows one transaction at a time

---

## User Stories

1. **As a** user viewing transactions, **I want to** click a details button to see full transaction information, **so that** I can view all available data about a transaction.
2. **As a** user viewing transaction details, **I want to** add or remove tags from within the modal, **so that** I don't have to close the modal to categorize the transaction.

---

## Proposed Solution

### High-Level Design

- Add an eye icon button to `TransactionRow.vue` that appears on hover
- Create `TransactionDetailModal.vue` following the existing modal pattern
- Wire the modal into `transactions.vue` with event handlers for tag operations

### UI/UX

**Button placement:** Eye icon between tags and amount, visible on row hover (same pattern as add-tag button).

**Modal layout:**

- Header: Merchant name/description as title, category badge if present
- Details table: Booking date, value date (if different), amount, account, full description
- Tags section: Existing tags with remove buttons, add tag button if no tag set

---

## Technical Considerations

### Files Created

| File                                                              | Purpose         |
|-------------------------------------------------------------------|-----------------|
| `frontend/app/components/transactions/TransactionDetailModal.vue` | Modal component |

### Files Modified

| File                                                           | Changes                                    |
|----------------------------------------------------------------|--------------------------------------------|
| `frontend/app/components/transactions/TransactionRow.vue`      | Added details button, `open-detail` emit   |
| `frontend/app/components/transactions/TransactionDayGroup.vue` | Pass-through `open-detail` event           |
| `frontend/app/pages/transactions.vue`                          | Modal state, handlers, component rendering |

---

## Implementation Plan

### Phase 1: Modal Component

- [x] Create TransactionDetailModal with Teleport, fade transition, backdrop
- [x] Display all transaction fields in key-value table layout
- [x] Include tag management using existing TagsTagChip and TagsTagSelector

### Phase 2: Integration

- [x] Add eye icon button to TransactionRow
- [x] Wire event through TransactionDayGroup
- [x] Add modal state and handlers to transactions.vue

---

## Testing Strategy

- [x] Manual testing: Click details button opens modal
- [x] Manual testing: All fields display correctly
- [x] Manual testing: Tag add/remove works from modal
- [x] Manual testing: Backdrop click and X button close modal
- [x] TypeScript/linting: `make check` passes

---

## References

- Pattern reference: `frontend/app/components/accounts/AccountSettingsModal.vue`
