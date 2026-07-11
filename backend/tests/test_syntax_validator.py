from app.services.syntax_validator import PythonSyntaxValidator, get_validator


def test_python_valid_code():
    result = PythonSyntaxValidator().validate("def add(a, b):\n    return a + b\n")
    assert result.is_valid
    assert result.errors == []


def test_python_invalid_code_reports_line():
    result = PythonSyntaxValidator().validate("def add(a, b)\n    return a + b\n")
    assert not result.is_valid
    assert result.errors
    assert result.errors[0].line is not None


def test_python_empty_body_syntax_error():
    result = PythonSyntaxValidator().validate("def add(a, b):\n")
    assert not result.is_valid


def test_get_validator_unsupported_language_raises():
    import pytest

    with pytest.raises(ValueError):
        get_validator("ruby")


def test_java_heuristic_balanced_braces_valid(monkeypatch):
    from app.services.syntax_validator import JavaSyntaxValidator

    validator = JavaSyntaxValidator()
    monkeypatch.setattr(JavaSyntaxValidator, "_JAVAC", None)
    code = (
        "public class Hello {\n"
        "    public static void main(String[] args) {\n"
        '        System.out.println("hi");\n'
        "    }\n"
        "}\n"
    )
    result = validator.validate(code)
    assert result.is_valid


def test_java_heuristic_unbalanced_braces_invalid(monkeypatch):
    from app.services.syntax_validator import JavaSyntaxValidator

    validator = JavaSyntaxValidator()
    monkeypatch.setattr(JavaSyntaxValidator, "_JAVAC", None)
    code = "public class Hello {\n    public static void main(String[] args) {\n"
    result = validator.validate(code)
    assert not result.is_valid


def test_java_heuristic_missing_class_declaration(monkeypatch):
    from app.services.syntax_validator import JavaSyntaxValidator

    validator = JavaSyntaxValidator()
    monkeypatch.setattr(JavaSyntaxValidator, "_JAVAC", None)
    code = "int x = 5;\n"
    result = validator.validate(code)
    assert not result.is_valid
