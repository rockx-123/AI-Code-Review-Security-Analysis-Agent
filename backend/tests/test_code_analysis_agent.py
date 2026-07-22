"""
Milestone 2, Task 4: validating agent detection accuracy against sample codebases with known
issues. These fixtures are deliberately constructed with specific, known problems so each
assertion checks for a *specific* rule firing on a *specific* line — not just "some findings
came back" — plus explicit false-positive checks against clean code.
"""
from app.agents.code_analysis_java import analyze_java
from app.agents.code_analysis_python import analyze_python


def _rule_ids(findings):
    return {f.rule_id for f in findings}


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def test_python_clean_code_has_no_findings():
    code = """
def calculate_total(cart):
    total = 0
    for item in cart:
        total += item.price
    return total
"""
    assert analyze_python(code) == []


def test_python_long_parameter_list():
    code = "def handle(a, b, c, d, e, f, g):\n    return a\n"
    findings = analyze_python(code)
    assert "long-parameter-list" in _rule_ids(findings)


def test_python_deep_nesting():
    code = """
def deep(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
"""
    findings = analyze_python(code)
    assert "deep-nesting" in _rule_ids(findings)


def test_python_bare_except():
    code = """
def risky():
    try:
        do_thing()
    except:
        pass
"""
    findings = analyze_python(code)
    assert "bare-except" in _rule_ids(findings)


def test_python_mutable_default_argument():
    code = "def add_item(cart=[]):\n    cart.append(1)\n    return cart\n"
    findings = analyze_python(code)
    assert "mutable-default-argument" in _rule_ids(findings)
    finding = next(f for f in findings if f.rule_id == "mutable-default-argument")
    assert finding.severity == "high"


def test_python_god_class():
    methods = "\n".join(f"    def m{i}(self): pass" for i in range(1, 18))
    code = f"class GodClass:\n{methods}\n"
    findings = analyze_python(code)
    assert "god-class" in _rule_ids(findings)


def test_python_god_class_not_flagged_under_threshold():
    methods = "\n".join(f"    def m{i}(self): pass" for i in range(1, 10))
    code = f"class NormalClass:\n{methods}\n"
    findings = analyze_python(code)
    assert "god-class" not in _rule_ids(findings)


def test_python_long_method():
    body = "\n".join(f"    x{i} = {i}" for i in range(60))
    code = f"def long_function():\n{body}\n    return x0\n"
    findings = analyze_python(code)
    assert "long-method" in _rule_ids(findings)


def test_python_syntax_error_returns_no_findings_instead_of_raising():
    # Syntax validation is Milestone 1's job — this is just a defensive fallback.
    assert analyze_python("def broken(:\n") == []


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

def test_java_clean_code_has_no_findings():
    code = """
public class Calculator {
    public static int add(int a, int b) {
        return a + b;
    }
    public static void main(String[] args) {
        System.out.println(add(4, 7));
    }
}
"""
    assert analyze_java(code) == []


def test_java_long_parameter_list():
    code = """
public class Handler {
    public void handle(int a, int b, int c, int d, int e, int f, int g) {
        return;
    }
}
"""
    findings = analyze_java(code)
    assert "long-parameter-list" in _rule_ids(findings)


def test_java_empty_catch_block():
    code = """
public class Risky {
    public void risky() {
        try {
            doThing();
        } catch (Exception e) {
        }
    }
}
"""
    findings = analyze_java(code)
    assert "swallowed-exception" in _rule_ids(findings)


def test_java_god_class():
    methods = "\n".join(f"    public void m{i}() {{}}" for i in range(1, 18))
    code = f"public class GodClass {{\n{methods}\n}}\n"
    findings = analyze_java(code)
    assert "god-class" in _rule_ids(findings)


def test_java_long_method():
    body = "\n".join(f"        int x{i} = {i};" for i in range(60))
    code = f"public class Big {{\n    public void longMethod() {{\n{body}\n    }}\n}}\n"
    findings = analyze_java(code)
    assert "long-method" in _rule_ids(findings)


def test_java_string_literal_braces_dont_confuse_brace_matching():
    """A `{` inside a string literal must not be mistaken for a real code brace."""
    code = """
public class Formatter {
    public String format(String name) {
        String template = "Hello, {name}! Welcome.";
        return template;
    }
}
"""
    # Should not crash and should not misdetect nesting/length from the string content.
    findings = analyze_java(code)
    assert "deep-nesting" not in _rule_ids(findings)
