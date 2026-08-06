# Design — UNION-BANK-: Design System & UX Principles

|Field|Value|
|---|---|
|Version|v0.1|
|Last Updated|2026-08-06|
|Owner|Lead Designer|
|Status|Approved|

---

## 1. Design Principles

1. **Trust through clarity** — banking UI must be unambiguous about amounts, statuses, and confirmations.
2. **Calm density** — dashboards show real data without noise.
3. **Safety rails** — every destructive action requires explicit confirmation.
4. **Consistent states** — loading/error/empty handled everywhere, identically.
5. **Accessibility by default** — AA contrast, keyboard-first forms.

## 2. Brand & Visual Identity

- **Tone:** institutional, trustworthy, modern. Banking blue + neutral grays.
- **Imagery:** no stock photos; iconography + charts only.
- **Name:** "Union Bank Management System" — professional demo brand.

## 3. Color System

|Token|Hex|Usage|Contrast|
|---|---|---|---|
|bg-canvas|#F5F7FA|App background|—|
|bg-surface|#FFFFFF|Cards, forms|—|
|text-primary|#111827|Body|≥ 7:1|
|text-muted|#6B7280|Secondary|≥ 4.5:1|
|brand|#1D4ED8|Primary actions|≥ 4.5:1|
|success|#047857|Deposits/credits|≥ 4.5:1|
|danger|#B91C1C|Errors/debits|≥ 4.5:1|
|warning|#B45309|Lockout/limits|≥ 4.5:1|
|border|#D1D5DB|Dividers|—|

## 4. Typography Scale

|Token|Font|Size|Weight|LH|Usage|
|---|---|---|---|---|---|
|display|Inter|28px|700|1.2|Dashboard hero|
|title|Inter|20px|600|1.3|Screen titles|
|body|Inter|16px|400|1.5|Copy, forms|
|amount|JetBrains Mono|24px|600|1.3|Money figures|
|caption|Inter|13px|400|1.4|Meta, timestamps|

## 5. Spacing & Grid

- Base 4px; scale 4/8/12/16/24/32/48.
- Dashboard grid: accounts cards 3-col desktop, 1-col mobile.
- Max content width 1120px.

## 6. Component Library

### 6.1 Account Card

|State|Style|
|---|---|
|Default|Balance mono, account number, status chip|
|Loading|Skeleton|
|Error|Card-level retry|

```
┌──────────────────────────┐
│ Checking ···· 1234   ACTIVE│
│ Balance                    │
│ $12,480.00                 │
│ [Transfer] [History]       │
└──────────────────────────┘
```

### 6.2 Buttons / Inputs / Toasts

- Primary (brand), secondary (outline), danger (destructive, confirm dialog).
- Inputs: 1px border, brand focus ring; error + helper text.
- Toasts: success green / error red / warning amber; 5s auto-dismiss.

### 6.3 Transfer Form

- Amount field (mono, currency prefix), from/to selectors, CSRF handled silently by client.
- Submit shows processing state; result toast + history refresh.

### 6.4 Charts (Admin)

- Line/bar charts for stats; loading skeletons; empty state with CTA.

## 7. Iconography & Imagery

- Lucide-style stroke icons 20px; banking glyphs (transfer, lock, shield, eye).
- No stock photography.

## 8. Accessibility

- WCAG 2.1 AA; keyboard nav through all forms; focus visible.
- aria-live on toasts and lockout countdown.
- prefers-reduced-motion: disable transitions.

## 9. Responsive Behavior

|Breakpoint|Layout|
|---|---|
|< 640px|1-col stack; bottom sticky actions|
|640–1024px|2-col cards|
|> 1024px|3-col + side nav|

## 10. Motion

|Token|Value|
|---|---|
|Duration|150–200 ms|
|Easing|cubic-bezier(0.2,0,0,1)|
|Animated|toasts, card hover, modal|
|Never|money/status changes (instant)|

## 11. Dark Mode

- Not in v1 (light theme default). Token mapping reserved for future.

## 12. Related Documents

|Document|Relationship|
|---|---|
|[AppFlow.md](AppFlow.md)|Screens consuming components|
|[PRD.md](../product/PRD.md)|UX requirements|
|[Rules.md](../project/Rules.md)|UI conventions|
