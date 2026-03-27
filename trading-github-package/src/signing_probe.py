import importlib.util
import json
from typing import Dict


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def signing_readiness() -> Dict[str, object]:
    modules = {
        "hyperliquid": module_available("hyperliquid"),
        "eth_account": module_available("eth_account"),
        "msgpack": module_available("msgpack"),
        "ecdsa": module_available("ecdsa"),
        "web3": module_available("web3"),
    }
    ready = all(modules.values())
    return {
        "ready": ready,
        "modules": modules,
        "note": "ready=True 仅表示本地签名依赖已安装，不代表真实发单已启用",
    }


if __name__ == "__main__":
    print(json.dumps(signing_readiness(), ensure_ascii=False, indent=2))
