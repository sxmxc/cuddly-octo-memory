# Admin UI

The admin UI is a Vue + Vite + Vuetify application that lets users manage mock endpoints.

## Key screens
- **Login**: Dedicated sign-in screen for dashboard users, with a concise studio introduction above the form, explicit remember-me behavior, and bootstrap-password guidance for fresh installs.
- **Catalog + settings**: Browse the live catalog, search/filter routes, and edit endpoint identity/runtime behavior without competing against the schema canvas.
- **Schema studio**: Dedicated request/response builder route with draggable Vuetify `v-chip` palette pills, a nested tree canvas, a left-rail inspector, import/copy actions, and a preview-focused right rail.
- **Preview**: Call the public mock route with the configured method and path parameters to inspect the live response payload.
- **Security**: Change the signed-in user's password and, for superusers, create/edit/delete other dashboard users.

## API contract
The frontend communicates with the backend via the admin API under `/api/admin`.
- `POST /api/admin/auth/login`
- `GET /api/admin/auth/me`
- `POST /api/admin/auth/logout`
- `POST /api/admin/account/change-password`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/{id}`
- `DELETE /api/admin/users/{id}`
- `GET /api/admin/endpoints`
- `GET /api/admin/endpoints/{id}`
- `POST /api/admin/endpoints`
- `PUT /api/admin/endpoints/{id}`
- `DELETE /api/admin/endpoints/{id}`
- `POST /api/admin/endpoints/preview-response`

## UX notes
- Logged-out users should only see the sign-in journey; catalog/editor/preview/security controls should stay hidden until authentication succeeds.
- Active sessions live in browser `sessionStorage`; remember-me additionally copies a bearer session token to `localStorage` so reloads and restarts can restore the session without persisting the raw password.
- New bootstrap or reset passwords must be rotated through the dedicated security screen before endpoint CRUD or user-management routes unlock.
- The settings page and schema studio are intentionally separate so endpoint metadata/behavior edits do not crowd the schema authoring flow.
- The fixed top bar should own the full top edge of the admin app; desktop scrolling should happen inside the main content shell so the scrollbar starts below the header instead of beside it.
- Navigating between major admin surfaces should reset the main content shell back to the top, so routes like the schema studio do not inherit a half-scrolled workspace from the previous page.
- The endpoint catalog/settings workspace should keep the left rail and top-level shell mounted while switching between browse/create/edit records, leaving the visible transition scoped to the right-hand record pane.
- On desktop, the endpoint catalog rail should act like a bounded navigator with its own vertical scroll region and client-side pagination so long catalogs do not push the main editor down the page.
- The desktop endpoint workspace should let the catalog card fill the full left rail, pin that rail within the main content shell, and leave the right-hand settings pane on the main content scroll while the catalog list keeps its own internal scroll region.
- Endpoint list cards should stay compact and scannable: clear method badge, strong route name, one-line route/category metadata, and a balanced horizontal live-state/action cluster with enough breathing room to stay easy to scan.
- The desktop schema studio should keep the left palette/root-shape/inspector cards intact, pin that full rail within the 3-column workspace, and let the whole rail scroll as one unit without making the canvas or preview move.
- Duplicating an endpoint should open the create flow with a prefilled copy, auto-adjust the name/slug/path, and default the duplicate to disabled so the user can review it before publishing.
- The schema studio is builder-first: users drag Vuetify chip pills into a tree workspace, edit node settings in the left inspector rail, and use import/copy actions only as advanced helpers.
- Response nodes can be static, true-random, or mocking-random per field; request nodes stay schema-only and intentionally omit mock controls.
- The response inspector exposes a semantic value-type selector for generated and mocking fields, so IDs, names, first names, emails, prices, and long-text fields can be authored explicitly instead of relying only on field-name guesses.
- The response builder uses the authenticated preview API for live sample payloads and only shows the manual regenerate action when no `seed_key` is set; request mode reuses the right rail as a live schema preview so the studio keeps a stable three-panel rhythm.
- Canvas selection should always drive the inspector directly; nested node clicks must update the active inspector target instead of bubbling back up to parent containers.
- Preview requests hit the public mock endpoint directly so runtime behavior matches the backend dispatcher.
- Validation runs both in the browser for basic field checks and in the backend when saving.
- Use skeleton states during session restore and initial catalog/editor loads to keep state transitions visually stable.
- Prefer Vuetify components wherever possible to keep styling, states, and interaction affordances consistent across the admin journey.
