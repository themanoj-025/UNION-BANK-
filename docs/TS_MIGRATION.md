# TypeScript Migration Plan

**Status:** Planned  
**Date:** 2026-07-16  

---

## Rationale

Both independent codebase audits flagged the absence of TypeScript as a gap
for a 2026 portfolio project. TypeScript provides:

- Type safety for API response shapes (catches field name mismatches at build time)
- Better IDE autocompletion and refactoring support
- Self-documenting interfaces for API contracts
- Catch `undefined` access errors before runtime

## Migration Strategy — Incremental (Phase A → B → C)

The migration is deliberately incremental. We do NOT convert all files at once
— each phase is self-contained and testable.

---

### Phase A: Types only (1 day)

Create `frontend/src/types/api.ts` with TypeScript interfaces for every
API response shape. These are already defined as Pydantic models in
`api/models.py` — the TS types mirror them exactly.

**Files to create:**
- `frontend/src/types/api.ts` — `ApiResponse<T>`, `ProfileData`, `BalanceData`,
  `TransactionOut`, `AccountListItem`, `SavingsGoalOut`, `LoanOut`, `TokenData`,
  `StatisticsData`, etc.
- `frontend/src/types/auth.ts` — `AuthState`, `LoginCredentials`, `RegisterData`
- `frontend/src/types/errors.ts` — `ErrorCode` enum matching `api/models.py`

**No JSX files are changed in this phase.**

**Verification:** `npx tsc --noEmit` passes.

---

### Phase B: Core infrastructure (2 days)

Rename the following files to `.ts` and add type annotations:

1. `frontend/src/api.js` → `frontend/src/api.ts`
   - Typed axios instance with `ApiResponse<T>` generic
   - Typed interceptor functions
2. `frontend/src/context/AuthContext.jsx` → `frontend/src/context/AuthContext.tsx`
   - Typed `AuthContextType` interface
   - Typed `login()`, `logout()`, `checkAuth()` methods

**Verification:** `npx tsc --noEmit` passes. App still builds and runs.

---

### Phase C: Page components (3-4 days)

Convert JSX pages one at a time, starting with the most data-critical:

1. `Dashboard.jsx` — uses `ProfileData`, `BalanceData`, `TransactionOut`
2. `Login.jsx` — uses `TokenData`, `LoginCredentials`
3. `SignUp.jsx` — uses `RegisterData`
4. `Deposit.jsx`, `Withdraw.jsx`, `Transfer.jsx` — use `TransactionRequest`
5. `Statement.jsx` — uses `TransactionOut[]`
6. `Profile.jsx` — uses `ProfileData`, `UpdateProfileRequest`
7. `SavingsGoals.jsx`, `Loans.jsx` — use `SavingsGoalOut`, `LoanOut`
8. Admin pages — use `AccountListItem`, `StatisticsData`, `LoanAdminStats`

Each conversion follows the same pattern:
- Rename `.jsx` → `.tsx`
- Add `import type { ... } from '../types/api'`
- Add type annotations to state variables and API call responses

**Verification:** Each page works in browser after conversion.

---

## Configuration changes needed

### `frontend/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

### `frontend/vite.config.js` — already configured for React

### `frontend/package.json` — `@types/react` and `@types/react-dom` already present

---

## Future considerations

- **API client generator:** Tools like `openapi-typescript` can auto-generate
  all API types from `/openapi.json` once the OpenAPI spec is complete.
- **Zod validation:** Add Zod schemas for runtime validation of API responses
  in addition to TypeScript's compile-time checks.
- **Shared types monorepo:** For a larger team, extract types into a shared
  package consumed by both frontend and backend (`@union-bank/types`).

---

## Current status

| Phase | Status | Files Done |
|-------|--------|------------|
| A: Types only | ❌ Not started | 0/3 type files |
| B: Core infra | ❌ Not started | 0/2 core files |
| C: Pages | ❌ Not started | 0/14 page files |
