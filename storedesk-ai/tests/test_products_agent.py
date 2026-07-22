from agent.domains.products.agent import ProductsAgent


def products_agent_without_runtime_dependencies() -> ProductsAgent:
    return ProductsAgent.__new__(ProductsAgent)


def test_builds_stock_tool_call_from_clear_request():
    agent = products_agent_without_runtime_dependencies()
    state = {
        "userMessage": "Enable quantity monitoring for selected products at 5 units",
        "userContext": {"selected_product_ids": ["product-1", "product-2"]},
    }

    tool_calls = agent._build_monitoring_fallback_tool_call(state)

    assert tool_calls is not None
    function = tool_calls[0]["function"]
    assert function["name"] == "stock_monitoring"
    assert function["arguments"]["productIds"] == ["product-1", "product-2"]
    assert function["arguments"]["bulkStockMonitoring"] == {
        "isApplyToAllProducts": False,
        "isQuantityEnabled": True,
        "quantityThreshold": 5,
    }


def test_builds_disable_price_tool_call_for_all_products():
    agent = products_agent_without_runtime_dependencies()
    state = {
        "userMessage": "Disable price monitoring for all products",
        "userContext": {"selected_product_ids": []},
    }

    tool_calls = agent._build_monitoring_fallback_tool_call(state)

    assert tool_calls is not None
    arguments = tool_calls[0]["function"]["arguments"]
    assert arguments["productIds"] == []
    assert arguments["bulkPriceMonitoring"] == {
        "isApplyToAllProducts": True,
        "isPriceEnabled": False,
        "priceThresholdPercentage": 0.0,
    }


def test_bulk_tool_call_requires_confirmation():
    agent = products_agent_without_runtime_dependencies()
    tool_calls = [{
        "function": {
            "name": "stock_monitoring",
            "arguments": {
                "productIds": [],
                "bulkStockMonitoring": {
                    "isApplyToAllProducts": True,
                    "isQuantityEnabled": False,
                    "quantityThreshold": 0,
                },
            },
        },
    }]

    result = agent._process_tool_calls(
        {"userMessage": "Disable stock monitoring for all products"},
        tool_calls,
    )

    assert result["requiresConfirmation"] is True
    assert result["clarificationQuestion"] == (
        "Are you sure you want to disable stock monitoring for all products?"
    )


def test_bulk_all_monitoring_confirmation_mentions_stock_and_price():
    agent = products_agent_without_runtime_dependencies()
    tool_calls = [
        {
            "function": {
                "name": "stock_monitoring",
                "arguments": {
                    "productIds": [],
                    "bulkStockMonitoring": {
                        "isApplyToAllProducts": True,
                        "isQuantityEnabled": False,
                        "quantityThreshold": 0,
                    },
                },
            },
        },
        {
            "function": {
                "name": "price_monitoring",
                "arguments": {
                    "productIds": [],
                    "bulkPriceMonitoring": {
                        "isApplyToAllProducts": True,
                        "isPriceEnabled": False,
                        "priceThresholdPercentage": 0,
                    },
                },
            },
        },
    ]

    result = agent._process_tool_calls(
        {"userMessage": "disable all monitoring for all products"},
        tool_calls,
    )

    assert result["requiresConfirmation"] is True
    assert result["toolCallsMade"] == tool_calls
    assert result["clarificationQuestion"] == (
        "Are you sure you want to disable stock and price monitoring for all products?"
    )
