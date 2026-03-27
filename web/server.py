from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    web_root = root
    handler = lambda *args, **kwargs: SimpleHTTPRequestHandler(*args, directory=str(web_root), **kwargs)
    server = ThreadingHTTPServer(("127.0.0.1", 8787), handler)
    print("Dashboard running at http://127.0.0.1:8787/web/")
    server.serve_forever()


if __name__ == "__main__":
    main()
