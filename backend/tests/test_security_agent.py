"""Milestone 2, Task 4: validating security detection accuracy against known-vulnerable and
known-clean sample code, for both supported languages."""
from app.agents.security_java import analyze_java_security
from app.agents.security_python import analyze_python_security


def _rule_ids(findings):
    return {f.rule_id for f in findings}


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

def test_python_clean_code_has_no_security_findings():
    code = """
import os

def get_user(user_id, db_session):
    return db_session.query("SELECT * FROM users WHERE id = %s", (user_id,))

def read_api_key():
    return os.environ.get("API_KEY")
"""
    assert analyze_python_security(code) == []


def test_python_sql_injection_inline():
    code = """
def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
"""
    findings = analyze_python_security(code)
    assert "sql-injection" in _rule_ids(findings)
    finding = next(f for f in findings if f.rule_id == "sql-injection")
    assert finding.severity == "critical"
    assert finding.cwe_id == "CWE-89"


def test_python_sql_injection_tainted_variable():
    code = """
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
"""
    findings = analyze_python_security(code)
    assert "sql-injection" in _rule_ids(findings)


def test_python_parameterized_query_not_flagged():
    code = """
def get_user(user_id, db_session):
    return db_session.execute("SELECT * FROM users WHERE id = %s", (user_id,))
"""
    findings = analyze_python_security(code)
    assert "sql-injection" not in _rule_ids(findings)


def test_python_hardcoded_secret_by_name():
    code = 'db_password = "SuperSecretPass123"\n'
    findings = analyze_python_security(code)
    assert "hardcoded-secret" in _rule_ids(findings)


def test_python_hardcoded_secret_by_prefix_is_critical():
    fake_key = "sk_live_" + "NOTAREALKEYUSEDONLYFORUNITTESTS"  # split so it never appears whole in source
    code = f'api_key = "{fake_key}"\n'
    findings = analyze_python_security(code)
    matches = [f for f in findings if f.rule_id == "hardcoded-secret"]
    assert len(matches) == 1  # not double-counted by both the name and prefix checks
    assert matches[0].severity == "critical"


def test_python_placeholder_secret_not_flagged():
    code = 'api_key = "changeme"\n'
    assert analyze_python_security(code) == []


def test_python_weak_hash_md5():
    code = """
import hashlib

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()
"""
    findings = analyze_python_security(code)
    assert "weak-password-hash" in _rule_ids(findings)


def test_python_xss_same_line():
    code = """
def render_profile(name):
    return render_template_string(f"<div>Welcome {name}</div>")
"""
    findings = analyze_python_security(code)
    assert "reflected-xss" in _rule_ids(findings)


def test_python_xss_tainted_variable():
    code = """
def render_profile(name):
    html = f"<div>Welcome {name}</div>"
    return render_template_string(html)
"""
    findings = analyze_python_security(code)
    assert "reflected-xss" in _rule_ids(findings)


def test_python_csrf_exempt():
    code = """
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def my_view(request):
    return HttpResponse("ok")
"""
    findings = analyze_python_security(code)
    assert "csrf-protection-disabled" in _rule_ids(findings)


def test_python_missing_object_authorization():
    code = """
@app.route("/documents/<doc_id>")
def get_document(doc_id):
    return db.query.get(doc_id)
"""
    findings = analyze_python_security(code)
    assert "missing-object-authorization" in _rule_ids(findings)


def test_python_object_authorization_present_not_flagged():
    code = """
@app.route("/documents/<doc_id>")
@login_required
def get_document(doc_id):
    if current_user.id != db.query.get(doc_id).owner_id:
        abort(403)
    return db.query.get(doc_id)
"""
    findings = analyze_python_security(code)
    assert "missing-object-authorization" not in _rule_ids(findings)


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------

def test_java_clean_code_has_no_security_findings():
    code = """
public class Calculator {
    public static int add(int a, int b) {
        return a + b;
    }
}
"""
    assert analyze_java_security(code) == []


def test_java_sql_injection():
    code = """
public class Users {
    public User getUser(String userId, Connection conn) throws Exception {
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE id = " + userId;
        ResultSet rs = stmt.executeQuery(query);
        return null;
    }
}
"""
    findings = analyze_java_security(code)
    assert "sql-injection" in _rule_ids(findings)


def test_java_hardcoded_secret_prefix_not_double_counted():
    fake_key = "sk_live_" + "NOTAREALKEYUSEDONLYFORUNITTESTS"  # split so it never appears whole in source
    code = f"""
public class Config {{
    private String apiKey = "{fake_key}";
}}
"""
    findings = analyze_java_security(code)
    matches = [f for f in findings if f.rule_id == "hardcoded-secret"]
    assert len(matches) == 1
    assert matches[0].severity == "critical"


def test_java_weak_hash_md5():
    code = """
public class Hasher {
    public void hash() throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
    }
}
"""
    findings = analyze_java_security(code)
    assert "weak-password-hash" in _rule_ids(findings)


def test_java_xss_tainted_variable():
    code = """
public class Profile {
    public void render(HttpServletResponse response, HttpServletRequest request) throws Exception {
        String param = request.getParameter("name");
        response.getWriter().println(param);
    }
}
"""
    findings = analyze_java_security(code)
    assert "reflected-xss" in _rule_ids(findings)


def test_java_csrf_disabled():
    code = """
public class SecurityConfig {
    public void configure(HttpSecurity http) throws Exception {
        http.csrf().disable();
    }
}
"""
    findings = analyze_java_security(code)
    assert "csrf-protection-disabled" in _rule_ids(findings)
