from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from services.search_service import SearchService
from ui.main_window import MainWindow
from models.track import Track

def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tidal-inspired track search frontend")
    parser.add_argument("--test", action="store_true", help="Run a headless search test")
    args = parser.parse_args()

    if args.test:
        service = SearchService()
        results: list[Track] = service.search("Tracks", "Do They Know It's Christmas?")
        print(f"Retrieved {len(results)} track(s) in test mode")
        if results:
            first = results[0]
            artists = ", ".join(first.artists)
            print(f"Sample: {first.title} by {artists}")
    else:
        main()
