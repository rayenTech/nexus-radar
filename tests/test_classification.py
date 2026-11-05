from app.classification import classify_content, extract_keywords, relevance_score


def test_classifies_security_content():
    assert classify_content("Ransomware detection in a SOC", "Threat intelligence for incident response") == "cybersecurity"


def test_classifies_ai_content():
    assert classify_content("Large language models for autonomous agents") == "ai"


def test_classifies_network_content():
    assert classify_content("A new 6G network slicing architecture") == "ngn"


def test_extracts_keywords_and_score():
    keywords = extract_keywords("Federated learning for trustworthy AI")
    assert "federated learning" in keywords
    assert relevance_score("6G network security", category="ngn") > 1
