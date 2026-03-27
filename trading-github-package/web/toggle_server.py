import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / 'config' / 'settings.json'
SERVER_VERSION = 'toggle-server-risk-settings-v2'


class ToggleHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _reply_json(self, status_code: int, obj: dict):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self._set_cors()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _set_cors(self):
        self.send_header('Access-Control-Allow-Origin', 'http://127.0.0.1:8787')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors()
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/health':
            return self._reply_json(200, {'ok': True, 'version': SERVER_VERSION, 'config_path': str(CONFIG_PATH)})
        return super().do_GET()

    def do_POST(self):
        path_to_key = {
            '/api/toggle-live': 'enable_live_execution',
            '/api/toggle-auto-test': 'enable_auto_test_entries',
            '/api/toggle-auto-live': 'enable_auto_live_entries',
        }

        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8') if length else '{}'
        data = json.loads(raw or '{}')
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))

        if self.path == '/api/save-risk-settings':
            account_total = float(data.get('accountTotal', 0) or 0)
            base_equity = float(data.get('baseEquity', 0) or 0)
            risk_pct = float(data.get('riskPct', 0) or 0)
            if risk_pct <= 0 or risk_pct > 20:
                return self._reply_json(400, {'ok': False, 'error': '无法设置：单笔风险必须在 0~20% 之间'})
            if base_equity <= 0 or account_total <= 0 or base_equity > account_total:
                return self._reply_json(400, {'ok': False, 'error': '无法设置：账户基准超过账户总金额'})
            config.setdefault('account', {})['base_equity'] = base_equity
            risk_cfg = config.setdefault('risk', {})
            risk_cfg['risk_per_trade_pct'] = risk_pct
            risk_cfg['max_risk_per_trade_pct'] = risk_pct
            CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
            return self._reply_json(200, {'ok': True, 'base_equity': base_equity, 'risk_per_trade_pct': risk_pct, 'max_risk_per_trade_pct': risk_pct})

        config_key = path_to_key.get(self.path)
        if not config_key:
            self.send_error(404)
            return

        enabled = bool(data.get('enabled', False))
        exec_cfg = config.setdefault('execution', {})
        exec_cfg[config_key] = enabled
        CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
        return self._reply_json(200, {'ok': True, config_key: enabled})


def main() -> None:
    server = ThreadingHTTPServer(('127.0.0.1', 8788), ToggleHandler)
    print('Toggle server running at http://127.0.0.1:8788')
    server.serve_forever()


if __name__ == '__main__':
    main()
