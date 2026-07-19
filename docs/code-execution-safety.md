# Code Execution — Safety Notes

This feature runs submitted Python/Java code and shows its actual output, in addition to the
syntax validation from Milestone 1. Read this before enabling it, especially before any public
deployment (Render, Railway, etc.) — **`ENABLE_CODE_EXECUTION` defaults to `false` on purpose.**

## What's protected

| Protection | How |
|---|---|
| Runaway processes (infinite loops) | Hard wall-clock timeout (`EXECUTION_TIMEOUT_SECONDS`, default 5s) via `subprocess.run(timeout=...)` |
| Memory exhaustion | `RLIMIT_AS` caps the process's address space to 256 MB (POSIX only) |
| CPU exhaustion | `RLIMIT_CPU` caps CPU time to 5 seconds (POSIX only) |
| Fork bombs | `RLIMIT_NPROC` caps the process count the child can spawn |
| Runaway output | stdout/stderr truncated at `EXECUTION_MAX_OUTPUT_CHARS` (default 4000) |
| Secret leakage via `os.environ` | The child process gets a stripped environment (`PATH`, `HOME` only) — your `.env` values (API keys, etc.) are never passed through |
| Syntax bypass | The `/api/execution/run` endpoint re-validates syntax server-side before ever executing, regardless of what the client claims |

All four protections above were verified with actual test runs (infinite loop, memory bomb,
runtime error, normal output) during development — this isn't just a paper claim.

## What's NOT protected — read this part carefully

- **No network isolation.** Executed code can make outbound HTTP requests, hit internal
  services, or otherwise use the network exactly as the host server can. A plain
  `subprocess.run()` has no concept of network namespaces.
- **No filesystem isolation.** The code runs in a fresh temp directory that's deleted
  afterward, but it is **not** chrooted or containerized — with enough cleverness, code could
  still read/write outside that temp directory (e.g. anything the host OS user can access).
- **No true process isolation.** rlimits reduce the blast radius of accidents (a runaway loop,
  a memory leak) but do not stop a determined, malicious payload the way a container or VM
  boundary would.
- **Java execution has no equivalent rlimit layer** — Java processes aren't covered by the
  same `resource` module hooks as the Python path in the same way (the JVM manages its own
  memory), so a Java submission is comparatively less contained. The timeout still applies.

**In short: this is appropriate for a personal project, local development, or a demo where you
trust who's submitting code. It is not appropriate to expose on a public, unauthenticated
deployment without a real sandbox (Docker container per execution, gVisor, Firecracker, or a
managed code-execution API) in front of it.**

## Recommended path if you do want this publicly, safely

1. Keep `ENABLE_CODE_EXECUTION=false` on any public deployment for now.
2. If you want it public later, the standard approach is running each execution inside a
   short-lived, resource-capped Docker container (or a managed service built for this, e.g.
   Judge0, Piston) instead of a bare `subprocess.run()` — that gets you real filesystem and
   process isolation, not just rlimits.
3. Rate-limit the endpoint per IP/session regardless of sandboxing, so even legitimate use
   can't be abused to exhaust server resources.

## How to enable it for local/trusted use

```bash
# backend/.env
ENABLE_CODE_EXECUTION=true
EXECUTION_TIMEOUT_SECONDS=5
EXECUTION_MAX_OUTPUT_CHARS=4000
```
Restart the backend. The "Run code" button will start working in the UI; it stays hidden/blocked
with a clear message otherwise.
