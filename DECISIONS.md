# DECISIONS

## 2026-03-14: Project bootstrap decisions
- **Tech stack**: FastAPI + SQLModel + Alembic for backend; the frontend started on React + Vite before later moving to Vue + Vuetify.
- **Persistence**: Postgres is the single source of truth for endpoint definitions.
- **OpenAPI**: Live generation on each request from DB-backed endpoint definitions.
- **Admin auth**: Basic username/password for v1.
- **Data format**: Use JSON Schema for request/response schemas; responses will be generated from templates.

## 2026-03-14: Local Docker bootstrap reliability
- **Startup scripts**: Invoke container startup scripts through `sh` so bind-mounted checkouts do not depend on host executable bits.
- **Postgres image**: Use the Debian-based Postgres image for local development to avoid Alpine locale bootstrap warnings.
- **Health checks/auth**: Probe the configured app database and initialize Postgres with password-based local and host auth to avoid misleading readiness failures and init warnings.
- **Frontend dev server**: Keep Vite host validation enabled by default, but make allowed hostnames and Docker proxy targets configurable through environment variables.

## 2026-03-14: Admin editor and preview strategy
- **Schema editing**: Use simple JSON textareas for request schema, response schema, and example template fields in v1 rather than introducing a heavier schema-builder abstraction.
- **Preview behavior**: Run previews against the public mock route so editor feedback stays aligned with backend path matching, response shaping, and enable/disable behavior.
- **Example templates**: Treat `example_template` as arbitrary JSON across models and schemas so endpoints can return arrays or objects without special-casing.

## 2026-03-14: Frontend auth and theme UX
- **Auth journey**: Split the frontend into a dedicated logged-out sign-in route and protected editor routes so catalog/editor UI only appears when the user is authenticated.
- **Credential persistence**: Keep active admin sessions in `sessionStorage` by default and only copy credentials to `localStorage` when the user explicitly opts into remember-me behavior.
- **Loading states**: Use skeleton screens for session restore, catalog loading, and editor/preview hydration so transitions stay calm and informative.
- **Theming**: Persist an explicit light/dark theme toggle on the client rather than relying only on system defaults.

## 2026-03-14: Unified schema builder and mock generation
- **Response contract**: Replace `example_template` and `response_mode` with a single `response_schema` contract that stores generation and fixed-value behavior in `x-mock` extensions, while `x-builder.order` preserves drag/drop property order.
- **Authoring UX**: Replace raw JSON textareas with a tree-based drag-and-drop schema builder that uses a palette, nested workspace, inspector, and live generated preview.
- **Preview flow**: Add an authenticated `POST /api/admin/endpoints/preview-response` route so the editor can request generated samples without depending on public route calls for every keystroke.
- **OpenAPI publishing**: Strip internal builder/generator extensions from public OpenAPI output so the published spec remains clean JSON Schema.

## 2026-03-14: Backend bootstrap and migration path
- **Startup bootstrap**: Run `alembic upgrade head` during API startup and seeding instead of `SQLModel.create_all()`.
- **Migration strategy**: Keep Alembic config and revisions under `apps/api/migrations/` so they are available inside the API Docker build context and can migrate legacy endpoint rows in-place.

## 2026-03-15: Frontend pivot to Vue + Vuetify
- **Frontend stack**: Replace the React admin app with Vue 3 + Vuetify so the project can lean on a coherent component system instead of custom one-off styling.
- **Schema journey**: Split endpoint settings and schema editing into separate routes so the schema builder has a dedicated full-page canvas, inspector, and preview surface.
- **Vuetify-first UI**: Prefer Vuetify components wherever possible, including draggable `v-chip` palette pills, cards, tabs, alerts, skeletons, and form controls.
- **`@vuetify/v0` usage**: Use `createStorage` and `createTheme` from `@vuetify/v0` to manage the persisted light/dark theme toggle alongside Vuetify's runtime theme.
- **MCP setup**: Commit a repo-level Vuetify MCP config and frontend package scripts so AI-assisted contributors can connect to the official Vuetify MCP server without re-discovering the setup.

## 2026-03-15: Admin endpoint duplication workflow
- **Duplicate UX**: Launch duplication into the existing create-route form rather than immediately persisting a second record, so operators can review and tweak the copy before it exists in the catalog.
- **Safety defaults**: Auto-adjust the duplicated endpoint's name, slug, and path, and default the copy to disabled so a quick duplicate cannot accidentally shadow an existing public route.

## 2026-03-15: Admin catalog rail behavior
- **Rail ergonomics**: Treat the endpoint catalog as a bounded navigation rail on desktop, with its own vertical scroll area, rather than letting long lists extend the whole page.
- **Pagination scope**: Keep catalog pagination client-side after filtering so the rail stays lightweight while the backend remains focused on endpoint CRUD and runtime concerns.

## 2026-03-15: GitHub repository rename to Mockingbird
- **Canonical repo slug**: Treat `sxmxc/mockingbird` as the source-of-truth GitHub repository and update local git remotes plus deploy/docs references accordingly.
- **Published image names**: Because runtime image names follow `ghcr.io/<owner>/<repo>-<image>`, the documented GHCR targets now resolve to `ghcr.io/sxmxc/mockingbird-api` and `ghcr.io/sxmxc/mockingbird-admin-web`.

## 2026-03-15: CI smoke-test env bootstrap
- **Workflow bootstrap**: Have the Docker smoke test create `.env` from `.env.example` before running Compose so CI behaves like a clean developer checkout without depending on ignored local files.

## 2026-03-15: Mockingbird public surface and brand
- **Product name**: Present the system publicly as Mockingbird, including a shared mascot SVG used as the primary logo/favicon in the admin shell and public API landing page.
- **Public homepage**: Add a branded landing page at `/` and `/api` plus a live `/api/reference.json` feed so the public API has a human-friendly homepage that stays aligned with the DB-backed catalog.
- **Generator modes**: Extend response generation to support three authoring modes per node: fixed/static, true random, and mocking-random.
- **Docker/frontend isolation**: Keep the frontend container's dependency tree isolated in Docker-managed volumes and refresh it automatically from `package-lock.json` changes instead of depending on host `node_modules`.

## 2026-03-15: Public hero artwork and semantic mock value types
- **Landing hero direction**: Treat the top of the public site as a full-viewport hero and keep the copy editorial and minimal rather than explaining the reveal mechanic in-product.
- **Artwork workflow**: Prefer explicit `hero-top.*` and `hero-bottom.*` assets from `apps/api/static/landing/` so the public hero can fade between two fixed frames, while keeping a single tall `hero.*` asset as a fallback.
- **Hero motion**: Use the hero scroll progress to drive an eased crossfade between top and bottom artwork frames rather than vertically sliding the same image through the viewport.
- **Mock semantics**: Store an explicit `x-mock.type` for generated and mocking fields, using human-friendly value types such as `id`, `name`, `first_name`, `email`, and `price`, while still accepting legacy `x-mock.generator` aliases.
- **Legacy compatibility**: Normalize stored response schemas before runtime sample generation so older rows using short `text` generators on quote/message-style fields can inherit the newer `long_text` behavior without requiring an immediate manual reseed.

## 2026-03-15: Backend session lifecycle stability
- **Session management**: Use a yielded FastAPI session dependency backed by a shared `session_scope()` context manager so every request reliably returns its SQLAlchemy connection to the pool.
- **Direct callers**: Non-request code such as OpenAPI generation should use the shared context manager rather than reaching through the dependency function.

## 2026-03-15: Public quick reference UX
- **Reference layout**: Present the public endpoint catalog as a compact paginated table rather than large cards so the homepage can scan like a real API directory.
- **Examples and theming**: Keep example payloads behind an explicit modal action and persist a lightweight client-side light/dark mode toggle for the public surface.
- **Styling framework**: Use Bulma for the public homepage controls and table/modal primitives, while keeping custom CSS only for the branded hero artwork, theming, and sticky-table behavior.
- **Bulma discipline**: Favor near-stock Bulma table, modal, tag, button, and form treatments instead of layering bespoke chrome over those components.

## 2026-03-15: Public request/response examples for body routes
- **Reference payload contract**: Extend `/api/reference.json` with generated `sample_request` values for `POST` / `PUT` / `PATCH` endpoints, while keeping read-only routes response-only.
- **Landing-page modal**: Reuse the existing example modal and render request and response sections together for body-based routes so public users can see both the JSON to send and the mock payload they should expect back.

## 2026-03-15: CI/CD image and workflow strategy
- **Workflow split**: Keep a fast CI workflow for backend tests, frontend lint/test/build, and Docker Compose smoke coverage, and a separate image workflow for runtime-image validation and registry publishing.
- **Docker targets**: Preserve hot-reload local development through `dev` image targets in Compose, but publish dedicated `runtime` targets so release images do not ship Vite dev servers or `uvicorn --reload`.
- **Registry/release model**: Publish API and admin images to GHCR as multi-arch `linux/amd64` and `linux/arm64` manifests. Treat `vX.Y.Z` git tags as official releases that emit semver tags plus `latest`, while default-branch builds emit branch, `edge`, and `sha-*` tags.
- **Artifacts and provenance**: Upload per-image metadata artifacts (image name, version, digest, tags, build metadata/manifest) and attach provenance/SBOM data so CI/CD outputs are inspectable and easier to trust.
- **Standalone deploy example**: Keep a separate GHCR-backed Compose example for environments without a local checkout, and default that example to `edge` for convenience while recommending explicit release tags for real deployments.

## 2026-03-15: Runtime and dependency refresh
- **Workflow runtime**: Move GitHub Actions onto the current Node 24 JavaScript-action runtime path, upgrade the action majors accordingly, and explicitly opt workflows into `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` so the repo catches compatibility regressions before GitHub flips the default.
- **Supported runtimes**: Standardize the project on Node 24 and Python 3.12 across Dockerfiles, CI, and local version files so contributors are less likely to drift onto stale or mismatched runtimes.
- **Security baseline**: Upgrade the backend to the current FastAPI/Pydantic/SQLModel line and the frontend to Vite 8 so the repo clears the audited Starlette/Black and Vite/esbuild advisories.
- **Frontend linting**: Move the admin app to ESLint flat config so the repo can run ESLint 10 with the current Vue parser/plugin line and stop printing deprecated-package notices during `npm ci`.
- **Transitive override**: Override `js-beautify`'s `glob` dependency to a current non-deprecated major because that package is only used through frontend test tooling and the older line was still emitting install-time deprecation warnings.

## 2026-03-15: Feature-branch and PR-driven release workflow
- **Working branch policy**: Do feature work on named `feature/*` or other task-specific working branches rather than committing directly to `main`.
- **Release note source**: Treat detailed pull requests as the canonical changelog input so automated releases can summarize shipped work from merged PR metadata instead of relying on direct commits to the default branch.
- **Merge discipline**: Keep `main` as the integration/release branch and prefer changes to land through reviewable PRs that describe user-facing impact, risk, and verification.

## 2026-03-15: GitHub wiki documentation strategy
- **Wiki role**: Use the GitHub wiki as a curated user/developer handbook for setup, admin usage, API behavior, deployment, and troubleshooting.
- **Canonical source**: Keep `README.md` and `docs/` in the main repository as the canonical documentation source, and derive the wiki content from those repo docs instead of maintaining a competing source of truth.
- **Content boundaries**: Exclude internal planning, agent workflow instructions, backlog management, and architecture decision logs from the wiki so the public handbook stays practical and audience-focused.

## 2026-03-15: Admin security hardening and account management
- **Admin identity model**: Replace the shared env-backed Basic Auth credential pair with DB-backed dashboard users plus bearer session tokens so multiple users can sign in without storing the raw password in the browser.
- **Bootstrap flow**: Create a one-time bootstrap superuser during DB init, generate its password when `ADMIN_BOOTSTRAP_PASSWORD` is unset, and require that bootstrap/reset password to be rotated before the rest of the admin API unlocks.
- **User management**: Add a dedicated security surface and admin API for password rotation plus superuser-controlled user creation, editing, disabling, and deletion.
- **Route separation**: Reserve `/api/admin` and other system-owned public paths such as `/api` and `/api/reference.json` so DB-defined public mock endpoints cannot collide with or impersonate private admin routes.

*> Future decisions should append a dated entry with context and rationale.*
