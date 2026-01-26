"""
Configuration Loader
====================

Loads configuration for the negotiation system.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class PricingConfig:
    """Pricing configuration."""
    product_id: str = "enterprise-license"
    base_price: float = 500.0
    min_price: float = 350.0
    max_discount_percent: float = 30.0


@dataclass
class AgentConfig:
    """Agent configuration."""
    buyer_max_price: float = 450.0
    seller_min_price: float = 350.0
    seller_asking_price: float = 500.0


@dataclass  
class LimitsConfig:
    """Negotiation limits."""
    max_turns: int = 10
    timeout_seconds: int = 300


@dataclass
class Config:
    """Complete system configuration."""
    pricing: PricingConfig
    agents: AgentConfig
    limits: LimitsConfig
    
    @classmethod
    def default(cls) -> "Config":
        return cls(
            pricing=PricingConfig(),
            agents=AgentConfig(),
            limits=LimitsConfig(),
        )


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file or return defaults.
    
    Args:
        config_path: Path to YAML config file (optional)
        
    Returns:
        Config object with all settings
    """
    if config_path is None:
        return Config.default()
    
    path = Path(config_path)
    if not path.exists():
        print(f"[Config] Warning: {config_path} not found, using defaults")
        return Config.default()
    
    with open(path) as f:
        data = yaml.safe_load(f)
    
    pricing_data = data.get("pricing", {})
    agents_data = data.get("agents", {})
    limits_data = data.get("limits", {})
    
    return Config(
        pricing=PricingConfig(
            product_id=pricing_data.get("product_id", "enterprise-license"),
            base_price=pricing_data.get("base_price", 500.0),
            min_price=pricing_data.get("min_price", 350.0),
            max_discount_percent=pricing_data.get("max_discount_percent", 30.0),
        ),
        agents=AgentConfig(
            buyer_max_price=agents_data.get("buyer_max_price", 450.0),
            seller_min_price=agents_data.get("seller_min_price", 350.0),
            seller_asking_price=agents_data.get("seller_asking_price", 500.0),
        ),
        limits=LimitsConfig(
            max_turns=limits_data.get("max_turns", 10),
            timeout_seconds=limits_data.get("timeout_seconds", 300),
        ),
    )
