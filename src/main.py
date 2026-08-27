from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from src.pipeline import ContentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Content Factory V1")
    parser.add_argument("--demo", action="store_true", help="Run the deterministic demo pipeline")
    parser.add_argument("--idea", type=str, default=None, help="Run a custom idea through the pipeline")
    args = parser.parse_args()

    if not args.demo and not args.idea:
        parser.print_help()
        return

    idea = args.idea or "شركة تقنية رفضت فرصة صغيرة ثم تحولت القصة إلى درس بمليارات الدولارات"
    result = ContentPipeline().run(idea)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
