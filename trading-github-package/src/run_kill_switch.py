import json

from env_loader import load_local_env
from live_kill_switch import LiveKillSwitch
from main import load_config


def main() -> None:
    load_local_env()
    config = load_config()
    result = LiveKillSwitch(config).execute()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
