"""
Multi-Affiliate Network Support
================================
Supports: Amazon Associates, ShareASale, Impact, Commission Junction (CJ)
Each network has different link formats and tracking parameters.
"""

import os
import re
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class AffiliateNetwork(Enum):
    AMAZON = "amazon"
    SHAREASALE = "shareasale"
    IMPACT = "impact"
    CJ = "cj"
    AWIN = "awin"
    RAKUTEN = "rakuten"
    CLICKBANK = "clickbank"


@dataclass
class AffiliateConfig:
    """Configuration for a single affiliate network."""
    network: AffiliateNetwork
    tracking_id: str
    base_url: str = ""
    extra_params: Dict[str, str] = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class AffiliateLinkBuilder:
    """Builds affiliate links for multiple networks."""
    
    # Network configurations with default link formats
    NETWORK_CONFIGS = {
        AffiliateNetwork.AMAZON: {
            "base_url": "https://www.amazon.com/dp/",
            "param_name": "tag",
            "link_format": "{base_url}{product_id}?{param_name}={tracking_id}",
        },
        AffiliateNetwork.SHAREASALE: {
            "base_url": "https://www.shareasale.com/r.cfm",
            "param_name": "u",
            "link_format": "{base_url}?{param_name}={tracking_id}&m={merchant_id}&urllink={product_url}",
        },
        AffiliateNetwork.IMPACT: {
            "base_url": "https://click.linksynergy.com/deeplink",
            "param_name": "id",
            "link_format": "{base_url}?{param_name}={tracking_id}&mid={merchant_id}&murl={product_url}",
        },
        AffiliateNetwork.CJ: {
            "base_url": "https://www.dpbolvw.net/click-",
            "param_name": "id",
            "link_format": "{base_url}{tracking_id}-{advertiser_id}/{product_url}",
        },
        AffiliateNetwork.AWIN: {
            "base_url": "https://www.awin1.com/cread.php",
            "param_name": "awinmid",
            "link_format": "{base_url}?{param_name}={merchant_id}&awinaffid={tracking_id}&ued={product_url}",
        },
        AffiliateNetwork.RAKUTEN: {
            "base_url": "https://click.linksynergy.com/link",
            "param_name": "id",
            "link_format": "{base_url}?{param_name}={tracking_id}&mid={merchant_id}&murl={product_url}",
        },
        AffiliateNetwork.CLICKBANK: {
            "base_url": "https://{vendor}.{tracking_id}.hop.clickbank.net",
            "param_name": "tracking_id",
            "link_format": "https://{vendor}.{tracking_id}.hop.clickbank.net/?tid={tracking_id}",
        },
    }
    
    def __init__(self):
        self.configs: Dict[AffiliateNetwork, AffiliateConfig] = {}
        self._load_from_env()
    
    def _load_from_env(self):
        """Load affiliate configs from environment variables."""
        # Amazon
        amazon_tag = os.getenv("AMAZON_AFFILIATE_TAG") or os.getenv("AMAZON_TAG")
        if amazon_tag:
            self.configs[AffiliateNetwork.AMAZON] = AffiliateConfig(
                network=AffiliateNetwork.AMAZON,
                tracking_id=amazon_tag
            )
        
        # ShareASale
        sas_id = os.getenv("SHAREASALE_AFFILIATE_ID")
        if sas_id:
            self.configs[AffiliateNetwork.SHAREASALE] = AffiliateConfig(
                network=AffiliateNetwork.SHAREASALE,
                tracking_id=sas_id
            )
        
        # Impact
        impact_id = os.getenv("IMPACT_AFFILIATE_ID")
        if impact_id:
            self.configs[AffiliateNetwork.IMPACT] = AffiliateConfig(
                network=AffiliateNetwork.IMPACT,
                tracking_id=impact_id
            )
        
        # CJ
        cj_pid = os.getenv("CJ_PID")
        if cj_pid:
            self.configs[AffiliateNetwork.CJ] = AffiliateConfig(
                network=AffiliateNetwork.CJ,
                tracking_id=cj_pid
            )
        
        # Awin
        awin_id = os.getenv("AWIN_AFFILIATE_ID")
        if awin_id:
            self.configs[AffiliateNetwork.AWIN] = AffiliateConfig(
                network=AffiliateNetwork.AWIN,
                tracking_id=awin_id
            )
        
        # Rakuten
        rakuten_id = os.getenv("RAKUTEN_AFFILIATE_ID")
        if rakuten_id:
            self.configs[AffiliateNetwork.RAKUTEN] = AffiliateConfig(
                network=AffiliateNetwork.RAKUTEN,
                tracking_id=rakuten_id
            )
        
        # ClickBank
        cb_id = os.getenv("CLICKBANK_AFFILIATE_ID")
        if cb_id:
            self.configs[AffiliateNetwork.CLICKBANK] = AffiliateConfig(
                network=AffiliateNetwork.CLICKBANK,
                tracking_id=cb_id
            )
    
    def add_network(self, network: AffiliateNetwork, tracking_id: str, **extra):
        """Add or update a network configuration."""
        self.configs[network] = AffiliateConfig(
            network=network,
            tracking_id=tracking_id,
            extra_params=extra
        )
    
    def build_link(self, network: AffiliateNetwork, product_id: str, 
                   product_url: str = "", **kwargs) -> Optional[str]:
        """Build an affiliate link for the given network and product."""
        if network not in self.configs:
            return None
        
        config = self.configs[network]
        net_config = self.NETWORK_CONFIGS.get(network, {})
        link_format = net_config.get("link_format", "{base_url}{product_id}?{param_name}={tracking_id}")
        
        # Prepare format variables
        fmt_vars = {
            "base_url": net_config.get("base_url", ""),
            "product_id": product_id,
            "product_url": product_url,
            "param_name": net_config.get("param_name", "tag"),
            "tracking_id": config.tracking_id,
            **config.extra_params,
            **kwargs
        }
        
        try:
            return link_format.format(**fmt_vars)
        except KeyError as e:
            print(f"Missing parameter for {network.value} link: {e}")
            return None
    
    def build_all_links(self, product_id: str, product_url: str = "", 
                        **kwargs) -> Dict[str, str]:
        """Build affiliate links for ALL configured networks."""
        links = {}
        for network in self.configs:
            link = self.build_link(network, product_id, product_url, **kwargs)
            if link:
                links[network.value] = link
        return links
    
    def get_configured_networks(self) -> list:
        """Get list of configured network names."""
        return [n.value for n in self.configs.keys()]


# Default builder instance
builder = AffiliateLinkBuilder()


def get_affiliate_link(asin: str, amazon_tag: str = None, network: str = "amazon") -> str:
    """Backward-compatible function for Amazon links."""
    if network.lower() == "amazon":
        tag = amazon_tag or os.getenv("AMAZON_AFFILIATE_TAG") or os.getenv("AMAZON_TAG", "studentdeals0a-20")
        return f"https://www.amazon.com/dp/{asin}?tag={tag}"
    
    # Try other networks
    try:
        net = AffiliateNetwork(network.lower())
        link = builder.build_link(net, asin)
        return link or ""
    except ValueError:
        return ""


def get_multi_affiliate_links(asin: str, product_url: str = "", **kwargs) -> Dict[str, str]:
    """Get affiliate links for all configured networks."""
    return builder.build_all_links(asin, product_url, **kwargs)


if __name__ == "__main__":
    # Test
    print("Configured networks:", builder.get_configured_networks())
    links = builder.build_all_links("B0863FR3S9", "https://www.amazon.com/dp/B0863FR3S9")
    for net, link in links.items():
        print(f"  {net}: {link}")