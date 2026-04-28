from typing import Dict, Type
from .tools.stock_monitoring import StockMonitoringTool
from .tools.price_monitoring import PriceMonitoringTool

class ProductToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Type] = {
            "stock_monitoring": StockMonitoringTool,
            "price_monitoring": PriceMonitoringTool,
        }

product_tool_registry = ProductToolRegistry()
