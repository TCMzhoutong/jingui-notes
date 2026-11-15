"""Serve the built GitHub Pages site locally, including its repository subpath."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1] / "public"
BASEPATH = "/jingui-notes"


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path: str) -> str:
        clean = unquote(urlsplit(path).path)
        if clean == BASEPATH or clean.startswith(BASEPATH + "/"):
            clean = clean[len(BASEPATH):] or "/"
        target = Path(super().translate_path(clean))
        if not target.exists() and target.suffix == "" and target.with_suffix(".html").is_file():
            target = target.with_suffix(".html")
        return str(target)


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8080), PreviewHandler) as server:
        print("http://127.0.0.1:8080/jingui-notes/")
        server.serve_forever()
