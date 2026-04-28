from typing import Dict, Type
from .products.agent import ProductsAgent

class DomainRegistry:
    def __init__(self):
        self.domains: Dict[str, Type] = {
            "products": ProductsAgent,
        }

domain_registry = DomainRegistry()
