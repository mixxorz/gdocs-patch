# Hosted MCP Server Design

## Goal

Add an optional Model Context Protocol interface for `gdocs-patch`. It exposes the existing document read, edit, write, and XHTML syntax-help operations through a hosted Streamable HTTP server.

The server is for a trusted, single-account deployment. The operator supplies one set of Google credentials, and every authenticated MCP client acts through that Google account.

CLI-only users must not install MCP dependencies or see MCP advertised by `gdocs-patch --help`.

## Scope

The first version provides:

- a hosted Streamable HTTP MCP endpoint;
- static bearer-token authentication for MCP clients;
- the existing Google credential-loading behavior;
- `read_document`, `edit_document`, `write_document`, and `syntax_help` tools; and
- a separate `gdocs-patch-mcp` executable.

It does not provide:

- stdio or legacy HTTP+SSE transports;
- multi-user Google OAuth or per-user Google credentials;
- Google OAuth login or callback routes;
- operation previews, approval tokens, or automatic mutation retries;
- server-managed TLS;
- application-level document/session state; or
- MCP tools for Google authentication.

## Packaging and interface isolation

The existing `gdocs-patch` distribution gains an `mcp` optional extra containing `fastmcp==3.4.4` and its server runtime dependencies. None of those packages belongs in the base dependency list. The exact pin follows FastMCP's production versioning guidance and prevents minor releases from introducing protocol-facing breaking changes.

The distribution exposes two executables:

- `gdocs-patch`, whose existing commands and help remain unchanged; and
- `gdocs-patch-mcp`, which starts the optional server.

Python package entry points cannot be conditional on extras, so a CLI-only installation will still contain the `gdocs-patch-mcp` launcher. The launcher must not import the MCP SDK at module import time. When invoked without the extra, it exits without a traceback and explains that MCP support requires installing `gdocs-patch[mcp]`.

MCP modules are not imported by `gdocs_patch.cli`, `gdocs_patch.__init__`, or any existing command module. As a result, normal CLI startup and use do not import MCP code, and `gdocs-patch --help` does not mention the server.

## Server startup and transport

The server starts with:

```console
GDOCS_PATCH_MCP_TOKEN="secret" \
  gdocs-patch-mcp --host 127.0.0.1 --port 8000
```

It exposes a modern Streamable HTTP endpoint at `/mcp`. The defaults are host `127.0.0.1` and port `8000`. Deployments must explicitly pass `--host 0.0.0.0` or another non-loopback address when network exposure is intended.

`GDOCS_PATCH_MCP_TOKEN` is required and must be non-empty. The token is accepted only through the environment, not through a command-line option, so it is absent from the process argument list. Operators should inject the value through deployment secret management rather than writing a literal token in a shell command.

The built-in server does not configure TLS. Any deployment reachable beyond localhost must place it behind an HTTPS reverse proxy or ingress.

## Authentication

Every request to `/mcp` must contain:

```http
Authorization: Bearer <GDOCS_PATCH_MCP_TOKEN value>
```

Missing, malformed, or incorrect credentials receive `401 Unauthorized` before MCP request handling. Token comparison is timing-safe. Authentication failures never echo the configured token.

The MCP bearer token authenticates callers to this server; it is separate from the credentials used to call Google.

Google credentials continue to come from `load_credentials()`:

1. `GDOCS_PATCH_BEARER_TOKEN`, when present; otherwise
2. the existing saved credentials at `~/.config/gdocs-patch/credentials.json`.

The server adds no browser login flow or OAuth endpoints. Operators provision Google credentials before starting or invoking the server, using the existing CLI login or deployment secret management.

## Architecture

The MCP implementation is a thin transport adapter over `gdocs_patch.commands`. It does not invoke the CLI as a subprocess and does not add a generic service or command framework.

Each document tool:

1. receives and validates typed MCP arguments;
2. loads Google credentials and constructs a `GoogleDocsClient` for that invocation;
3. translates MCP-specific input values, such as edit objects, into the existing command types;
4. calls the corresponding command function directly; and
5. returns its result or translates a failure into an MCP tool error.

Constructing a client per invocation avoids sharing the Google API transport across concurrent requests. The server retains no application-level document or pending-operation state.

The syntax tool calls `describe_syntax()` directly and requires no Google credentials.

## Tool interface

Tool names are scoped by the MCP server, so they do not repeat `google` or `gdocs_patch`.

All public fields use `snake_case`, matching the Python APIs from which the MCP schemas are generated. This deliberately differs from the CLI's camel-case JSON boundary, avoiding aliases and manual schema translation in the MCP adapter.

### `read_document`

Arguments:

```text
document_id: string
offset: integer = 1
limit: integer | null = null
```

`offset` is one-based and must be at least 1. When supplied, `limit` must be positive. Both values retain the CLI's canonical-XHTML line pagination semantics.

The tool returns canonical XHTML as text and is marked read-only.

Data flow:

```text
MCP arguments
    → GoogleDocsClient
    → read_document
    → canonical XHTML text
```

### `edit_document`

Arguments:

```text
document_id: string
edits:
  - old_text: string
    new_text: string
allow_bullet_normalization: boolean = false
```

`edits` must be non-empty, and each `old_text` must be non-empty. The wrapper translates each input object into the existing `XhtmlEdit` type.

The operation preserves the CLI command's behavior: all matches are resolved against one fetched canonical XHTML snapshot; each old value must match exactly once; matched ranges cannot overlap; and the compiled update uses the fetched revision ID. It applies the mutation immediately and is marked mutating/destructive.

A successful call returns concise text identifying the number of replaced blocks.

### `write_document`

Arguments:

```text
document_id: string
content: string
allow_bullet_normalization: boolean = false
```

`content` is the complete target XHTML document. The tool fetches the current Google document, compiles the target against it, and immediately applies any resulting requests. It is marked mutating/destructive.

A successful call returns concise success text rather than the raw Google batch response.

### `syntax_help`

Arguments:

```text
topic: paragraphs | lists | tables | equations | sections | null = null
reference: boolean = false
```

With no topic, the tool returns the existing syntax introduction. With a topic, it returns that topic's guide or detailed reference. It is marked read-only and makes no Google API call.

## Mutation and concurrency semantics

The MCP layer does not add a preview/apply protocol. `edit_document` and `write_document` mutate the document during the tool call.

There are no automatic retries. The compiler includes the fetched source revision in `writeControl.requiredRevisionId`, so concurrent mutations fail rather than applying requests calculated for stale UTF-16 indices. A caller must read the new document state and explicitly issue a new mutation.

Concurrent reads are independent. Concurrent writes may race; revision enforcement determines which update is accepted safely.

## Error handling and logging

Expected failures become MCP tool errors while preserving their useful existing messages. These include:

- unavailable or invalid Google credentials;
- malformed or invalid XHTML;
- absent, duplicate, overlapping, empty, or ineffective exact edits;
- unsupported compiler transformations;
- stale source revisions; and
- Google API failures.

Expected failures are not returned as successful tool text. Unexpected failures are logged server-side and returned as a generic internal tool error. Logs must not include the MCP bearer token, complete tool arguments, document XHTML, or Google credential values.

The server does not retry tool calls after errors.

## Documentation

The README gains a separate MCP server section that does not alter the CLI command documentation. It covers:

- installation with `uv tool install 'gdocs-patch[mcp]'`;
- the missing-extra launcher behavior;
- Google credential provisioning;
- `GDOCS_PATCH_MCP_TOKEN`;
- host and port options;
- the `/mcp` endpoint and bearer header;
- all four tool names and argument schemas;
- immediate mutation behavior and revision conflicts; and
- the requirement for HTTPS when exposed beyond localhost.

## Verification policy

No new automated tests are added for the MCP adapter. Tool registration, generated schemas, argument dispatch, and Streamable HTTP behavior are owned by the MCP framework, and thin tests around them would primarily restate framework behavior.

The existing project test and static-analysis suite still runs to detect regressions in the CLI and shared command layer.

Implementation is manually smoke-checked in both installation modes:

1. A base installation runs `gdocs-patch` normally and receives useful missing-extra guidance from `gdocs-patch-mcp`.
2. An installation with the `mcp` extra starts the server.
3. Missing and incorrect MCP bearer tokens receive `401`.
4. A valid MCP client can list and invoke exactly the four designed tools.
5. Representative read, syntax-help, edit, and write calls use the existing command behavior.

## Success criteria

The feature is complete when:

- installing base `gdocs-patch` installs no MCP dependency;
- the existing CLI behavior and help are unchanged;
- installing `gdocs-patch[mcp]` makes the hosted server runnable through `gdocs-patch-mcp`;
- the server requires static bearer authentication and serves Streamable HTTP at `/mcp`;
- it exposes only `read_document`, `edit_document`, `write_document`, and `syntax_help`;
- document operations reuse the existing command functions and Google credential loader;
- expected failures appear as MCP tool errors without leaking secrets; and
- the documented manual smoke checks pass.
