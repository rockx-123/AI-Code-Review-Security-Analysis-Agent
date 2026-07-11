---
title: Code Smells and Design Anti-Patterns
category: code-smell
---

# Structural Smells

**Long method:** a function/method that does too much to hold in your head at once. Prefer
extracting cohesive chunks into well-named helper functions — the extraction itself often makes
a bug visible that was hiding in a wall of code.

**Large class / God object:** a class that owns too many responsibilities (state and behavior
that don't belong together). Symptoms: an enormous constructor, many unrelated public methods,
and the class name being vague ("Manager", "Helper", "Utils") because it does everything.

**Long parameter list:** more than ~4 parameters usually signals that several of them belong
together as an object, or that the function itself is doing more than one job.

**Deep nesting:** several levels of nested `if`/`for`/`try` make control flow hard to trace.
Guard clauses (early returns) that handle edge cases first usually flatten this dramatically.

# Duplication

Copy-pasted logic across functions or files is a maintenance and correctness risk — a fix
applied to one copy but not the others reintroduces the bug. Extract shared logic into a single
function or module; if two blocks look almost identical, the difference is usually a parameter,
not a reason to keep them separate.

# Complexity

**Cyclomatic complexity** counts the number of independent paths through a function
(each `if`, loop, and boolean operator adds a path). High complexity correlates with defect
rates and makes full test coverage impractical. Prefer decomposing into smaller functions, each
with a small number of paths, and consider replacing complex conditionals with polymorphism or a
lookup table when the branches map onto distinct types/cases.

# Coupling and Cohesion

**Feature envy:** a method that uses another object's data more than its own — it usually
belongs on the other object.

**Inappropriate intimacy:** two classes reaching into each other's internals, so a change to one
routinely breaks the other. Prefer well-defined interfaces over direct field access across class
boundaries.

**Low cohesion:** a class or module whose methods don't share a common purpose, so it changes for
many unrelated reasons. Split by responsibility.

# Naming and Readability

Non-descriptive identifiers (`data`, `tmp`, `x1`) force a reader to trace usage to understand
intent. Magic numbers and strings (`if status == 3`) should be named constants
(`if status == STATUS_APPROVED`) so intent is visible at the call site without cross-referencing.

# Error-Handling Smells

**Bare `except:` / swallowed exceptions (Python):** catching everything, including
`KeyboardInterrupt` and `SystemExit`, and often doing nothing with it, hides real failures.
Catch specific exception types and handle or log them meaningfully.

**Empty catch blocks (Java):** `catch (Exception e) {}` silently discards failure information.
At minimum, log the exception; ideally, handle it or rethrow a more specific exception with
context.

# Why This Matters for Review

Code-quality findings are distinct from security findings (see the OWASP knowledge base) — a
long method isn't a vulnerability, but it does make vulnerabilities easier to introduce and
harder to spot in review, which is why both categories are surfaced together in this platform.
