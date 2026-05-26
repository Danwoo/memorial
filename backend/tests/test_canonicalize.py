"""엔티티 canonicalization 단위 테스트 — 동의어 병합 정책 검증."""

from app.repositories.mindmap._aliases import canonicalize_entity_name


class TestExactAliases:
    """정확 일치 alias map."""

    def test_korean_to_canonical(self):
        assert canonicalize_entity_name("리액트") == "React"
        assert canonicalize_entity_name("타입스크립트") == "TypeScript"
        assert canonicalize_entity_name("파이썬") == "Python"
        assert canonicalize_entity_name("랭체인") == "LangChain"

    def test_abbreviation_to_canonical(self):
        assert canonicalize_entity_name("TS") == "TypeScript"
        assert canonicalize_entity_name("JS") == "JavaScript"
        assert canonicalize_entity_name("MS") == "Microsoft"

    def test_variant_spelling_to_canonical(self):
        assert canonicalize_entity_name("ReactJS") == "React"
        assert canonicalize_entity_name("React.js") == "React"
        assert canonicalize_entity_name("Reactjs") == "React"


class TestCaseInsensitive:
    """대소문자 무시 화이트리스트."""

    def test_lowercase_canonicalized(self):
        assert canonicalize_entity_name("react") == "React"
        assert canonicalize_entity_name("typescript") == "TypeScript"

    def test_uppercase_canonicalized(self):
        assert canonicalize_entity_name("REACT") == "React"
        assert canonicalize_entity_name("PYTHON") == "Python"


class TestPassthrough:
    """화이트리스트에 없는 이름은 그대로 반환."""

    def test_unknown_entity_unchanged(self):
        assert canonicalize_entity_name("MyCustomEntity") == "MyCustomEntity"
        assert canonicalize_entity_name("어떤한국어이름") == "어떤한국어이름"

    def test_whitespace_stripped(self):
        assert canonicalize_entity_name("  React  ") == "React"

    def test_empty_string_returned_as_is(self):
        assert canonicalize_entity_name("") == ""
        assert canonicalize_entity_name("   ") == ""
