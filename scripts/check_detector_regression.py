from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.detector import get_detector  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a small regression suite for the garbage detector.")
    parser.add_argument(
        "--case",
        action="append",
        help="Case in the form image_path=expected_label. Repeat for multiple cases.",
    )
    args = parser.parse_args()

    cases = args.case or [
        r"E:\人工智能\garbage_ai_system\uploads\fd85dc5319734da5acdf7207dff06b9c.jpg=厨余垃圾",
        r"E:\人工智能\garbage_ai_system\uploads\75816909d2e34af9bb1356b29490cf75.jpg=可回收垃圾",
        r"E:\人工智能\garbage_ai_system\uploads\34afd600501c47b5b22fc860a59d104f.jpg=可回收垃圾",
    ]

    detector = get_detector()
    failures = 0

    for case in cases:
        if "=" not in case:
            raise SystemExit(f"Invalid case: {case}")
        image_path_raw, expected = case.split("=", 1)
        image_path = Path(image_path_raw)
        result = detector.predict(image_path)
        ok = result.summary_label == expected
        status = "OK" if ok else "FAIL"
        print(
            f"[{status}] {image_path.name} expected={expected} "
            f"actual={result.summary_label} category={result.summary_category}"
        )
        if not ok:
            failures += 1

    if failures:
        raise SystemExit(f"{failures} regression case(s) failed.")


if __name__ == "__main__":
    main()
