import asyncio

from agent.semantic_intent_classifier import SemanticIntentClassifier


def fallback_classifier() -> SemanticIntentClassifier:
    classifier = SemanticIntentClassifier.__new__(SemanticIntentClassifier)
    classifier.model = None
    return classifier


def test_routes_stock_monitoring_request_to_products():
    result = asyncio.run(
        fallback_classifier().classify_intent(
            "Enable stock monitoring and create a low stock alert"
        )
    )

    assert result.intent == "stock_monitoring"
    assert result.confidence > 0.3


def test_routes_price_monitoring_request_to_products():
    result = asyncio.run(
        fallback_classifier().classify_intent(
            "Monitor product price and set a price alert"
        )
    )

    assert result.intent == "price_monitoring"
    assert result.confidence > 0.3


def test_unclear_request_stays_general():
    result = asyncio.run(
        fallback_classifier().classify_intent("Can you help me with something?")
    )

    assert result.intent == "general_chat"
