---
title: OWASP Top 10 — Web Application Security Risks (2021)
category: owasp
---

# A01: Broken Access Control

Broken access control means users can act outside their intended permissions — viewing or
modifying another user's data, escalating to admin, or reaching functionality that should be
restricted. It is typically caused by missing or improperly enforced server-side checks; the
client-side UI hiding a button is not access control.

**Common causes:** trusting a client-supplied role/ID, missing per-object authorization
checks (e.g. `/orders/{id}` returning any order regardless of owner), CORS misconfiguration,
force-browsing to authenticated pages as an unauthenticated user, and elevation of privilege by
modifying a JWT or session token that isn't properly verified server-side.

**Prevention:** deny by default; enforce ownership/role checks on every request server-side, not
just at the UI; use a single, centralized access-control mechanism rather than scattering checks
across handlers; log access-control failures and alert on repeated failures from one actor.

# A02: Cryptographic Failures

Failures related to cryptography that lead to exposure of sensitive data — previously called
"Sensitive Data Exposure." This covers both storing data that shouldn't be stored, and storing or
transmitting it without adequate protection.

**Common causes:** transmitting data in clear text (HTTP, unencrypted email/SMTP), using old or
weak cryptographic algorithms/protocols, using default or weak keys, missing proper key
management/rotation, and not enforcing encryption via directives such as HSTS.

**Prevention:** classify data and encrypt sensitive data at rest and in transit; use up-to-date,
vetted algorithms and libraries rather than custom cryptography; disable caching for sensitive
responses; store passwords using a strong, salted, memory-hard hashing algorithm (e.g. Argon2,
bcrypt) — never reversible encryption.

# A03: Injection

An application is vulnerable to injection when untrusted data is sent to an interpreter as part
of a command or query, and that data can alter the interpreter's execution — SQL injection,
NoSQL injection, OS command injection, and Cross-Site Scripting (XSS, treated here as a form of
injection into the browser) are all in this family.

**SQL injection example (vulnerable):**
```python
query = "SELECT * FROM users WHERE username = '" + username + "'"
cursor.execute(query)
```
An attacker supplying `' OR '1'='1` as `username` changes the query's meaning entirely.

**Prevention:** use parameterized queries / prepared statements or a well-vetted ORM so user
input is always treated as data, never as part of the command structure; validate and allow-list
input where possible; escape special characters when parameterization isn't available; apply the
principle of least privilege to the database account the application uses.

**Cross-Site Scripting (XSS):** occurs when untrusted data is rendered into a page without
proper output encoding, letting an attacker execute script in another user's browser session
(session theft, defacement, redirection to malicious sites). Prevention: context-aware output
encoding (HTML body, HTML attribute, JS, URL contexts each need different encoding), and
templating engines that auto-escape by default rather than manual string concatenation into HTML.

# A04: Insecure Design

A broad category about missing or ineffective control design, distinct from an implementation
bug — the flaw exists even in a "correct" implementation of a bad design. Example: a password
reset flow that doesn't rate-limit reset attempts is insecure by design, regardless of how well
the rate-limit-free code is written.

**Prevention:** threat model early; use secure design patterns and reference architectures;
write abuse cases alongside use cases; segment logic/tiers so a failure in one layer doesn't
compromise the rest.

# A05: Security Misconfiguration

Missing hardening, unnecessary features enabled, default accounts/passwords left active,
overly detailed error messages that leak stack traces or internal state, and missing security
headers all fall here.

**Prevention:** a repeatable, automated hardening process; minimal platform without unnecessary
features/samples/documentation exposed; a segmented application architecture; review and update
configurations as part of the deployment pipeline, not as a one-off.

# A07: Identification and Authentication Failures

Weaknesses in confirming a user's identity — permitting credential stuffing/brute force,
weak or default passwords, weak session management (session IDs exposed in the URL, not
rotated after login, not invalidated on logout), and missing or poorly implemented
multi-factor authentication.

**Prevention:** implement multi-factor authentication where possible; never ship with default
credentials; enforce strong password policy and check new passwords against known-breached
password lists; use a server-side, secure session manager that generates a new random session ID
after login.

# A08: Software and Data Integrity Failures

Code and infrastructure that doesn't protect against integrity violations — relying on plugins,
libraries, or modules from untrusted sources, insecure deserialization, or CI/CD pipelines
without adequate access control that let unverified code enter the deployment process.

**Prevention:** verify software and data integrity with digital signatures; ensure CI/CD
pipelines have proper access control and configuration; never deserialize data from untrusted
sources without integrity checks.
