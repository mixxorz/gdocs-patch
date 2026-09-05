# Workspace migration and gsheets-patch

Status: complete. Implementation, local verification, independent review, live
smoke check, and remote CI passed. Draft PR #21 remains open and unmerged.

## Goal

Introduce gsheets-patch as a sibling of gdocs-patch, with room for a future
gslides-patch. Frontload product and technical decisions so a later unattended
implementation run has a clear scope, acceptance criteria, and stopping rules.

The user has authorized implementation, local commits, feature-branch pushes,
and a draft PR within the guardrails below. Do not use Superpowers for this work.

## Decisions so far

- Each product has its own MCP server. No combined server is needed.
- Sheets MCP mirrors Docs: Streamable HTTP with static bearer-token
  authentication. No stdio transport in this scope.
- Expose 13 Sheets REST methods as individual MCP tools and CLI operations:
  get, getByDataFilter, batchUpdate, and all ten values methods.
- Exclude spreadsheets.create, sheets.copyTo, and developerMetadata.get/search
  from both surfaces.
  Native batchUpdate JSON remains unrestricted, including metadata request types;
  the exclusion concerns dedicated endpoints, not request-body validation.
- CLI and MCP share the API forwarding implementation and equivalent API coverage.
- Add a schema CLI command and MCP tool for on-demand native method and
  batch-request schema documentation. Keep large nested schemas out of normal
  tool definitions. This is a documentation surface, not an API mutation method
  or runtime validation layer. A later dogfood follow-up adds a shared skill
  guide: 13 API tools plus schema and skill (15 MCP tools total).
- Drop the redundant spreadsheets prefix from CLI commands. Spreadsheet-level
  methods live at the root; values methods live under the values command group.
- gsheets-patch exists to make spreadsheet work efficient and reliable for
  agents, not to reproduce gdocs-patch's architecture or editing workflow.
- Build a thin wrapper around the selected Sheets v4 REST methods, preserving
  native parameters and request/response JSON rather than inventing editing
  operations.
- No compiler, XHTML dialect, or local read/edit/write representation is required.
- Do not implement local Sheets semantic validation: Google validates ranges,
  field masks, request combinations, and values. Do not add confirmation gates,
  read-before-write checks, or client-side safety policies that change API behavior.
- Protocol-level parsing and required tool arguments are unavoidable interface
  mechanics, not a reason to duplicate Google's nested request schemas.
- Explicit user constraint for this pass: do not add speculative validation,
  defensive fallbacks, or fail-safe code because an API input might be invalid.
  This applies to implementers and reviewers. Invalid Sheets inputs go to Google;
  surface its response rather than intercepting, sanitizing, or repairing them.
- Native request bodies should pass through without coercion or normalization.
  Surface Google's error details rather than replacing them with generic errors.
- gslides-patch is a future product, not an implementation target yet.
- The unattended delivery goal is as fleshed out a Sheets product as feasible,
  not just a workspace migration, scaffold, or deliberately minimal demo.
  Prioritize a reliable end-to-end product, then broaden supported operations.
  This ambition does not imply full API parity.

## Validation boundary and review instructions

This is a thin API wrapper, not a safety layer. Pass this constraint explicitly
to every implementation and review agent.

Do not add:

- A1/range parsers or checks for bounds, dimensions, cell types, allowed enum
  values, field masks, batch request kinds, or body-schema conformity.
- Read-before-write checks, existence/permission probes, stale-read checks,
  destructive-operation confirmations, or extra user-consent gates for API calls.
- Client-side spreadsheet size limits, truncation, input normalization, automatic
  correction, fallback requests, or speculative recovery paths.
- Tests for hypothetical invalid Sheets inputs that force us to implement local
  checks. Representative Google error forwarding is sufficient.

Keep only the mechanics inherent in exposing the interface: argument/JSON parsing,
reading requested files, native request execution, and reporting actual failures.
Do not add validation beyond what the selected CLI/MCP/Google libraries already
require. Report library-imposed constraints honestly instead of adding another
validation layer or a framework to circumvent them.

Authentication, MCP bearer-token verification, credential confidentiality, and
release package/version checks are existing agreed requirements, not optional
Sheets-input validation. Retain those narrowly; do not use them to justify new
API safety policies. Test-resource cleanup belongs to manual verification, not
production preflight code.

Reviewers should flag incorrect forwarding, missing features, unnecessary code,
credential exposure, and violated contracts. They must not request defensive code
solely because 'X could be invalid.' Treat such suggestions as out of scope unless
they demonstrate a breach of an already agreed requirement.

## Primary implementation metric: minimal maintained code

User priority: the simplest feature-complete implementation, with lines of code
kept as low as possible across production code and tests. This is the primary
implementation metric within the agreed functionality and correctness floor.

- Prefer direct code and existing library capabilities over custom infrastructure,
  speculative abstractions, elaborate class hierarchies, and duplicated schemas.
- Follow-up user preference: readability takes precedence over shaving lines.
  Forward actual named arguments, never **locals(). Avoid fragmented chains of
  private helpers; keep only useful shared operations with descriptive names.
  Explain API groupings and non-obvious choices in comments.
- Share endpoint plumbing and behavior across CLI/MCP without building a generic
  framework. A small operation table is appropriate if it genuinely reduces the
  code and knowledge needed to add or understand an operation.
- Keep tests focused on distinct adapter risks. The 30–40 new Sheets case target
  and 50-case review threshold are accepted maintenance guardrails, not targets
  to fill. Fewer meaningful tests are better than redundant coverage.
- Do not reduce line counts by dropping approved features, weakening error
  behavior, removing useful tests/comments, cramming statements together, or
  hiding complexity in code generation or metaprogramming.
- During review, actively delete unnecessary layers and duplicated test setup.
- Report maintained Python physical line counts separately for Sheets production
  code and tests, with new/changed shared tooling and CI code accounted for
  separately. Include comments and blank lines consistently; do not game the
  metric. Existing Docs code moved unchanged is migration, not newly added code.
- No hard LOC ceiling is imposed; justify substantial code growth by the concrete
  approved behavior or distinct failure mode it supports.

## Repository direction

Approved layout: packages/<project>/src/<module>/, with package-local tests and
pyproject.toml files, a root uv workspace, and one root lockfile.

- One uv workspace with independently installable product packages.
- One root lockfile and shared development tooling.
- Independent package versions and releases, with no required lockstep versioning.
- Sheets starts at 0.1.0, supports Python 3.10+, and keeps MCP dependencies in an
  optional [mcp] extra.
- Future release tags are package-qualified, e.g. gdocs-patch/0.2.1 and
  gsheets-patch/0.1.0. Existing tags remain untouched.
- Preserve the existing gdocs-patch package name, Python imports, commands,
  optional MCP extra, and user-facing behavior.
- Keep product-specific API integration and tests within their respective
  packages. Sheets does not need a parallel hierarchy of hand-written API models.
- Do not create a generic patch engine or shared package speculatively.
- Separate the structural migration from the initial Sheets implementation.

```text
/
├── pyproject.toml                 # Workspace and development configuration
├── uv.lock
├── packages/
│   ├── gdocs-patch/
│   │   ├── pyproject.toml
│   │   ├── README.md
│   │   ├── src/gdocs_patch/
│   │   └── tests/
│   └── gsheets-patch/
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/gsheets_patch/
│       └── tests/
├── codemods/
├── docs/
└── .github/
```

Add the Slides package only when its development starts. The exact location of
existing product-specific documentation, evals, and experiments remains to be
decided during migration planning; unrelated user files must not be moved.

## Decision summary and execution defaults

Product decisions have been frontloaded. The minor implementation defaults below
complete the proposed execution plan; they do not broaden the approved scope.

1. **Unattended scope — decided:** workspace migration plus a complete thin
   Sheets product: the 13 API operations, schema discovery, CLI, MCP, auth,
   documentation, tests, and CI/release migration described below. Preserve Docs
   compatibility and correct forwarding rather than add new editing abstractions.
2. **API coverage — decided:** three spreadsheet-level methods (get,
   getByDataFilter, batchUpdate) and ten values methods, including native
   batchUpdate bodies for advanced operations. Exclude spreadsheets.create,
   sheets.copyTo, and dedicated developerMetadata endpoints. No bespoke
   formatting/structure helpers or Drive API support in the initial scope.
3. **Agent interface — I/O decided:** native Google JSON bodies and responses;
   snake_case MCP arguments and kebab-case CLI flags for native parameters. See
   the input/output contract below. On-demand API documentation is exposed via
   a schema CLI command/MCP tool. Use the surface mapping and schema defaults below.
4. **Transport defaults:** use a 60-second network-operation timeout and zero
   automatic Sheets API retries, including writes after ambiguous failures.
   Normal OAuth token refresh remains supported separately. Do not introduce
   Sheets semantic validation or preflight safety checks.
5. **Product surfaces — coverage decided:** CLI and MCP, each exposing the same
   13 selected REST methods. CLI omits the spreadsheets prefix and groups values
   methods under values. MCP mirrors Docs with Streamable HTTP and static
   bearer-token authentication; no stdio transport. See the surface mapping below.
6. **Authentication — decided:** mirror gdocs-patch's authentication UX and
   behavior, with the read/write spreadsheets OAuth scope and these names:
   - Default client secret: ~/.config/gsheets-patch/client_secret.json.
   - Support --client-secrets override on auth login.
   - Credentials: ~/.config/gsheets-patch/credentials.json.
   - Google bearer token override: GSHEETS_PATCH_BEARER_TOKEN.
   - MCP server bearer token: GSHEETS_PATCH_MCP_TOKEN.
   For this run, reuse ~/.config/gdocs-patch/client_secret.json; the user has
   enabled Sheets API for that app and authorized Sheets consent and saving
   credentials in ~/.config. Leave Docs credentials untouched.
7. **Package policy — approved:** packages/<project>/src/<module>/ in a root uv
   workspace; Python 3.10+; Sheets 0.1.0; optional [mcp] extra; independent
   versions; future package-qualified release tags such as gdocs-patch/0.2.1 and
   gsheets-patch/0.1.0. Existing tags remain untouched. Release implementation
   should clearly reject unqualified tags for new workspace releases.
8. **Validation access — authorized and read verified:** user supplied disposable
   spreadsheet 1HrUw4hclx2npR2yfzRrsDa4iENfh1OUwa5GPzOl_-PY for the proposed
   live tests. Sheets OAuth login succeeded with separate credentials saved at
   ~/.config/gsheets-patch/credentials.json. A read-only metadata request returned
   HTTP 200: title 'gsheets-patch scratch doc', tab Sheet1 (sheetId 0), 1000 rows
   by 26 columns. The later manual smoke check verified writes, formatting, and
   readback through CLI/HTTP MCP, then deleted only its two temporary tabs.
9. **Delivery permissions — decided:** local commits, pushing only
   feat/gsheets-patch, and opening a draft PR targeting main are authorized.
   Do not modify, push, delete, or force-update any other GitHub branch. No
   force-push is needed on the feature branch either. Do not merge, publish,
   create/push tags, or change external settings without additional permission.
10. **Completion target:** all selected operations and schema lookup usable from
    both surfaces, Docs compatibility preserved, installed distributions verified,
    required local checks and remote PR CI passing, and the authorized Wagtail
    inventory live scenario exercised and cleaned up. Deliver an unmerged draft
    PR with exact verification evidence. Report partial completion or blockers
    honestly; do not equate mocked tests with live coverage or actual publishing.

## Surface and schema defaults

| Native method | CLI | MCP tool |
| --- | --- | --- |
| spreadsheets.get | get | get_spreadsheet |
| spreadsheets.getByDataFilter | get-by-data-filter | get_spreadsheet_by_data_filter |
| spreadsheets.batchUpdate | batch-update | batch_update_spreadsheet |
| spreadsheets.values.get | values get | get_values |
| spreadsheets.values.batchGet | values batch-get | batch_get_values |
| spreadsheets.values.batchGetByDataFilter | values batch-get-by-data-filter | batch_get_values_by_data_filter |
| spreadsheets.values.update | values update | update_values |
| spreadsheets.values.batchUpdate | values batch-update | batch_update_values |
| spreadsheets.values.batchUpdateByDataFilter | values batch-update-by-data-filter | batch_update_values_by_data_filter |
| spreadsheets.values.append | values append | append_values |
| spreadsheets.values.clear | values clear | clear_values |
| spreadsheets.values.batchClear | values batch-clear | batch_clear_values |
| spreadsheets.values.batchClearByDataFilter | values batch-clear-by-data-filter | batch_clear_values_by_data_filter |

- All API commands accept the spreadsheet ID as the first positional argument;
  single-range methods accept range next. Native query options become flags;
  repeated list options such as --ranges accumulate without comma splitting.
- schema with no argument lists supported API methods and available schema names.
  schema <name> looks up a fully qualified method or native schema name, e.g.
  spreadsheets.batchUpdate, Request, or RepeatCellRequest. The MCP schema tool
  accepts an optional name argument with matching behavior.
- Use the installed Google client's bundled discovery document offline. Return
  native schema definitions with references intact; follow references through
  subsequent lookups rather than recursively expanding enormous schemas.
- Schema documentation need not hide native batch-request capabilities. Its
  method index describes the 13 exposed API operations, not excluded endpoints.
- Auth management stays on the CLI; it must not become a remotely callable MCP
  login or credential-reading tool.

## Input/output contract

- MCP exposes explicit snake_case path/query arguments and a native JSON object
  body. Body keys retain Google's camelCase names; omitted options stay omitted.
- CLI uses positional path arguments and kebab-case flags for query parameters.
- CLI accepts inline JSON via --body, file JSON via --body @path, and stdin JSON
  via --body -. Parse JSON without adding Sheets semantic validation.
- Successful responses retain Google's JSON structure, without a custom success
  envelope, synthesized fields, table conversion, or silent truncation.
- CLI pretty-prints JSON to stdout; diagnostics/errors go to stderr and failures
  return a nonzero exit status.
- MCP returns structured JSON with a JSON text representation for compatibility.
- Expose native fields selection for partial responses where supported.
- Preserve Google's error payload and HTTP status. CLI emits JSON errors on
  stderr; MCP marks failed tool calls as errors. For API failures use a thin error
  envelope containing http_status and the unmodified Google payload, including
  non-JSON response text when necessary. Local failures use
  {"error": {"type": "input|auth|transport", "message": "..."}} with one concrete
  type value. Do not expose credential values, authorization headers, or OAuth
  callback codes in diagnostics.

## Testing strategy

Test our adapter contracts, not Google's spreadsheet engine. The automated suite
is entirely offline and requires no credentials. Live acceptance is a one-off
manual implementation-time smoke check, not a committed live integration suite.

Accepted test budget: target 30–40 new collected Sheets test cases, with a review
threshold of 50. Count parameterized cases, not just test
functions. This is a maintenance guardrail, not an incentive to hide scenarios in
loops or giant tests. Existing Docs cases do not count against it; report new
workspace/release checks separately. Above the threshold, first remove redundant
coverage and justify any remaining cases by distinct risk. Prefer one focused
regression case per real behavior over exhaustive input combinations.

### Offline request/response contracts

Exercise the real Google client with a fake HTTP transport at the external
boundary. Use independently specified expected requests/responses rather than
computing expectations from the same operation registry as the implementation.

- Cover routing for all 13 operations: HTTP method, URL/path encoding, query
  parameters (including repeated ranges), and JSON bodies.
- Cover omission versus explicit false/zero, Unicode, quoted tab names, and
  native body preservation, including unknown nested fields.
- Verify native responses and useful Google errors survive the wrapper.
- Test the agreed timeout/retry policy, particularly ambiguous write failures.
- Do not implement an in-memory Sheets emulator or test Google's formula,
  formatting, range-validation, or batch atomicity implementation.

### CLI and MCP contracts

- Cover all 13 operation mappings once at the shared API boundary. Use a small
  representative set of CLI and MCP round trips for distinct adapter behavior,
  rather than repeat all 13 HTTP cases through both surfaces. Check public
  operation discovery separately so missing or excluded tools are caught.
- Test inline/file/stdin JSON, stdout/stderr separation, exit codes, and local
  input failures through the CLI.
- Test MCP tool discovery, structured/text output agreement, and error results
  through an MCP client rather than only calling handler functions directly.
- Verify the excluded endpoints are not exposed. Avoid duplicating framework
  tests or adding snapshot assertions for every generated schema detail.
- Test our credential selection/storage and refresh/error handling at external
  boundaries, with temporary project-local credential files and no real browser.
  Do not retest Google's OAuth implementation.

### Packaging and migration regression

- Run the existing Docs suite unchanged in behavior after the workspace move.
- Run pytest, Ruff lint/format, Fixit, Pyright, and pre-commit.
- Build/check distributions and smoke-test installed CLI/MCP entry points in
  project-local environments isolated from workspace source imports.
- Retain the supported Python CI matrix and verify installation with/without
  the optional MCP dependency.

### One-off manual live acceptance check

User authorized the proposed live testing and supplied existing disposable
spreadsheet 1HrUw4hclx2npR2yfzRrsDa4iENfh1OUwa5GPzOl_-PY. Separate Sheets OAuth
login succeeded and metadata read returned HTTP 200. The one-off manual smoke
check subsequently passed reads/writes/formatting through CLI and actual HTTP MCP;
its two temporary tabs were deleted and original tab metadata matched afterward.
Spreadsheet creation is not part of this product's surface.

- Reproduce the Wagtail inventory workflow with a small fixed example dataset:
  create two uniquely named test tabs, write page types and fields, format/freeze
  headers, add filters, then read back values and relevant properties.
- Delete only tabs created by the test; record their IDs immediately and report
  any cleanup failure so leftover resources can be removed safely.
- Do not add a live integration suite to pytest or CI. Perform this as a manual
  smoke check during implementation. Never use arbitrary existing spreadsheet
  tabs or rely on the live check for exhaustive endpoint coverage.
- Report live evidence separately from offline contract-test evidence.

## Original repository baseline

- gdocs-patch is currently version 0.2.0, with source and tests at repo root.
- Python 3.10+ is supported; CI tests Python 3.10 through 3.14.
- Packaging uses uv_build; FastMCP is an optional dependency.
- CI runs pytest, Ruff lint and format, Fixit, Pyright, pre-commit, package
  builds, metadata validation, and installed-wheel smoke tests.
- Release automation currently assumes one root package and an unqualified
  version tag. Workspace migration must account for this before release.
- Preserve ordinary mutable, hand-written, explicitly typed model classes,
  keyword-only constructors, snake_case attributes, and intentional UNSET /
  proto-default semantics as applicable.

## CI and release migration

- Current tests.yml runs on pushes to main and pull requests targeting main;
  pushing a feature branch alone does not trigger it. User approved a draft PR
  to exercise CI without broadening push triggers or creating duplicate CI runs.
- Keep one root quality job for Ruff lint/format, Fixit, Pyright, pre-commit, and
  lockfile consistency. Configure tools to cover both packages explicitly.
- Test both packages on Python 3.10 through 3.14. Prefer a package-by-Python
  matrix for clear failure attribution; do not add changed-path skipping yet.
- Build each package independently, validate wheel/sdist metadata, and smoke-test
  installed CLI/MCP entry points away from source imports. Verify base installs
  do not implicitly require MCP or the sibling package.
- Do not put Google OAuth credentials or live Sheets tests into CI. Run the
  authorized live test locally against the designated scratch spreadsheet.
- Adapt release.yml to parse an allowlisted package/version tag, validate against
  that member's metadata, preserve canonical-version/prerelease/main-ancestry
  checks, and build/publish only the selected package's artifacts.
- Test release selection/validation offline and exercise package builds in PR CI;
  do not create releases or upload artifacts to PyPI as a test.
- Sheets PyPI Trusted Publishing setup is an external prerequisite to publishing.
  Document it and report any required account configuration; do not change PyPI
  or GitHub environment settings without permission.
- After an authorized push/PR, inspect CI results and fix failures on the same
  branch. Report passing checks and any verification not exercised, especially
  the actual publishing step. Keep the PR unmerged.

## Implementation outline

Implement in reviewable local commits, keeping the migration distinct from Sheets
functionality. Per the user's follow-up, run implementation subagents sequentially,
then review afterward. Keep planning decisions in the main agent and include the
minimal LOC/no-speculative-validation constraints in every assignment.

### Phase 1: Workspace migration — complete

- [x] Baseline: 198 Docs tests and all quality tools passed after installing the
      optional MCP extra in the new worktree.
- [x] Moved Docs source/tests into the approved workspace layout; source files
      were moved unchanged. Updated fixture imports, build metadata, shared
      quality tooling, and package docs/license paths.
- [x] Verified Docs tests and isolated distributions after migration.
- [x] Committed migration separately: 91582c8.

### Phases 2–3: Sheets foundation and surface — complete

- [x] Implemented all 13 API operations plus offline schema lookup in CLI/MCP.
- [x] Mirrored Docs auth UX with separate Sheets credentials and static MCP token.
- [x] Kept native JSON, 60-second network timeout, no API retries, and no custom
      Sheets validation/preflight layer.
- [x] Added 37 offline Sheets cases covering distinct adapter/auth/schema risks.
- [x] Independent review found a missing native query option and OAuth-denial
      error reporting; both fixed. Follow-up review reported no blockers.
- [x] Live manual check: two inventory tabs, 21 cells, bold/frozen headers,
      filters and column sizing, exact CLI readbacks, actual authenticated HTTP
      MCP read/write, 14-tool discovery, and HTTP 401 without a bearer token.
      Cleanup deleted only the two created tabs and preserved original tabs.
- [x] Committed Sheets implementation separately: 9bff603.

### Phase 4: CI, verification, and handoff

- [x] CI tests both packages on Python 3.10–3.14 and builds each independently.
      Release selection accepts package-qualified tags and builds one member.
- [x] Updated development/release guides and documented PyPI Trusted Publishing.
- [x] Local pytest: 241 passed (198 Docs, 37 Sheets, 6 release-tooling cases).
- [x] Ruff lint/format, Fixit, Pyright, pre-commit, and lockfile checks passed.
- [x] Both package sdists/wheels passed metadata and isolated CLI/MCP checks,
      including wheels rebuilt from sdists. No sibling-package dependency.
- [x] LOC review reduced initial Sheets production code from 1,240 to 819
      physical lines. Tests: 586 lines. Shared Python release tooling/tests: 66
      lines. Smoke shell: 35 lines. CI workflows: 169 lines (69 fewer than baseline).
- [x] Pushed only feat/gsheets-patch and opened draft PR #21:
      https://github.com/mixxorz/gdocs-patch/pull/21
- [x] Remote CI passed all 13 jobs: quality/release-tooling checks, ten package
      test jobs on Python 3.10–3.14, and two isolated distribution builds.
      Code verification: https://github.com/mixxorz/gdocs-patch/actions/runs/33974319979
      (e3c44f5). Subsequent changes only finalize this report.

Actual PyPI publication was intentionally not exercised. A Sheets Trusted
Publisher must be configured before the first release. No release, tag push,
merge, other remote branch change, or permanent live integration suite was made.

## Follow-up: readability review

- Replaced all 13 MCP **locals() calls with explicit named arguments.
- Reduced CLI helpers from six to three, with descriptive names; inlined the
  one-use schema loader and camel-case helper. No private helper functions remain
  in Sheets production modules; actual shared adapters are retained.
- Grouped CLI setup into spreadsheet operations, value reads, body-based batch
  operations, single-range writes, and local commands, with explanatory comments.
- Replaced nested input ternaries with ordinary branches and clarified native
  parameter translation and the no-retry decision.
- No API behavior, validation policy, or tests added. Existing 241 tests and all
  required local checks passed. A one-off comparison confirmed unchanged parser
  namespaces and complete explicit argument forwarding for all 13 MCP tools.
- Independent review found no blockers. Sheets production is now 904 physical
  LOC; tests remain 586 LOC and 37 cases. The increase is deliberate explicitness
  and documentation, not new functionality.

## Follow-up: agent skill guide

- Added `gsheets-patch skill` and a read-only MCP `skill` tool, both returning the
  same plain Markdown without Google credentials or a network request.
- The guide explains method-first schema discovery, choosing/batching native
  operations, JSON file inputs, and a worked inventory-tab example with formatting.
  It documents native semantics and the OAuth-refresh exception to no API retries.
- Added one offline cross-interface guide test and updated tool discovery to 15
  tools. Current suite: 242 total cases (198 Docs, 38 Sheets, 6 release tooling).
- Updated installed-package smoke checks and package docs. The two example JSON
  bodies were parsed and built with the real SDK offline, without API execution.
- Also replaced the unnecessary two-flag CLI loop with explicit add_argument
  calls as requested. No new validation or editing abstractions were introduced.
- Sheets production is 1,033 physical LOC, including the 110-line guide module;
  tests are 612 LOC. Independent review found no blockers.

## Unattended execution guardrails

- Start only after the scope and implementation plan are approved.
- User requires a dedicated worktree. Work in .worktrees/gsheets-patch on branch
  feat/gsheets-patch. This plan lives in that worktree at
  docs/plans/gsheets-patch.md; the original checkout is not the implementation
  workspace. Local commits, pushes only to feat/gsheets-patch, and a draft PR
  targeting main are authorized. Never modify any other GitHub branch. Use
  explicit branch refspecs; no broad pushes, force-pushes, or tag pushes. No
  merge or publication is authorized.
- Leave existing unrelated untracked files and worktrees untouched.
- Do not install global tools or write outside the project without permission.
- Do not change cloud configuration, credentials, or real documents/spreadsheets
  without explicit authorization.
- If a missing product or safety decision blocks a phase, record the blocker;
  continue only with independent, already-approved work. Do not invent a risky
  default to claim completion.
- Preserve compatibility rather than broadening the migration into unrelated
  refactoring.
- Use notifications only for a genuine input blocker or final completion of a
  long-running task, not routine progress.
