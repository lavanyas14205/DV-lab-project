"""Demo launcher: start the dashboard and open the browser on one page.

Usage:
    python demo.py              # opens the AI Footprint page
    python demo.py q4           # opens /q4 (any page path works)

Unlike `python app.py`, this turns Flask debug/reloader off so the app
cannot restart or show an error overlay in the middle of a presentation.
"""
import sys
import threading
import webbrowser

from app import app

PORT = 8050
DEFAULT_PAGE = ""


def main() -> None:
    page = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PAGE).strip("/")
    url = f"http://127.0.0.1:{PORT}/{page}"
    # Give the server a moment to start before the browser requests the page.
    threading.Timer(1.5, webbrowser.open, args=(url,)).start()
    print(f"Demo running at {url}  (Ctrl+C to stop)")
    app.run(debug=False, port=PORT)


if __name__ == "__main__":
    main()
