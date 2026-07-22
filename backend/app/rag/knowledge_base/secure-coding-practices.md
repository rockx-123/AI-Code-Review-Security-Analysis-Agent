---
title: Secure Coding Practices — Quick Reference
category: secure-coding
---

# Input Validation

Treat all input from outside the trust boundary as untrusted — query params, form fields,
headers, file uploads, and even data from another internal service if it crosses a trust
boundary. Prefer allow-lists (define what's valid) over deny-lists (try to enumerate what's
invalid); deny-lists are chronically incomplete because attackers only need one bypass.
Validate on the server even if the client also validates — client-side validation is a UX
convenience, not a security control, since it can always be bypassed.

# Output Encoding

Encode output based on the context it's rendered into — HTML body, HTML attribute, JavaScript,
CSS, or URL each require different escaping rules, and using the wrong one (or none) is how
XSS happens even in code that "validates input." Prefer templating engines with automatic
context-aware escaping over manual string concatenation into markup.

# Authentication and Session Management

Store passwords hashed with a memory-hard algorithm (Argon2id or bcrypt), never encrypted or
in plain text. Generate a new session identifier after successful authentication to prevent
session fixation. Set cookies with `HttpOnly`, `Secure`, and an appropriate `SameSite`
attribute. Invalidate sessions server-side on logout, not just by clearing a client cookie.
Rate-limit authentication attempts and password reset requests.

# Access Control

Enforce authorization server-side on every request that touches a protected resource — never
rely on hiding a UI element as the only control. Check object-level ownership explicitly (e.g.
"does this order belong to this user") rather than only checking "is this user logged in."
Default to deny: a missing or ambiguous authorization check should reject the request, not
allow it.

# Secrets Management

Secrets (API keys, database credentials, signing keys) belong in environment variables or a
secrets manager, never committed to source control, hardcoded in source files, or embedded in
client-side code. A secret that has been committed to git history should be treated as
compromised and rotated, even if the commit is later removed, since history can persist in
forks, caches, and local clones.

**Hardcoded secret example (vulnerable):**
```java
String apiKey = "sk_live_TESTONLY";
```
Any reviewer, CI log, or repository access exposes this immediately, and rotating it requires a
code change and redeploy rather than a config change.

# Error Handling and Logging

Fail securely: a caught exception should not leak stack traces, internal file paths, SQL text,
or credentials to the end user. Log enough detail for engineers to diagnose the issue
server-side, but return a generic message to the client. Avoid empty `catch` blocks or bare
`except:` clauses that silently swallow errors — at minimum, log what was caught.

# Data Protection

Encrypt sensitive data in transit (TLS) and at rest. Apply the principle of least privilege to
data access — a service or user should only be able to read/write the data it actually needs.
Avoid logging sensitive data (passwords, tokens, full card numbers, personal data) even at debug
level, since logs are often less protected than the primary datastore.

# Dependency Hygiene

Third-party libraries inherit their vulnerabilities into your application. Keep dependencies
up to date, monitor for known-vulnerable versions, and avoid pulling packages from
unofficial/unverified sources. Pin versions and review changes on upgrade rather than
auto-updating blindly in production.
