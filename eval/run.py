"""Send eval/tickets.csv through the running API and score the routing.

    python eval/run.py pl        # or: en
    python eval/run.py pl --url http://localhost:8000
    python eval/run.py pl --tag thinking

The engine is whatever the API runs (ROUTER_ENGINE in .env). Per-ticket results go to
eval/results/<engine>-<lang>.csv, or <engine>-<tag>-<lang>.csv with --tag. Every ticket
is really forwarded, so MailHog receives one mail per row.
"""

import argparse
import csv
import statistics
import time
from collections import Counter
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("lang", choices=["pl", "en"])
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--tag", default="", help="added to the result file name, e.g. thinking")
    args = parser.parse_args()

    with (HERE / "tickets.csv").open(encoding="utf-8", newline="") as handle:
        tickets = list(csv.DictReader(handle))

    results = []
    with httpx.Client(base_url=args.url, timeout=400) as client:
        for ticket in tickets:
            started = time.perf_counter()
            response = client.post(
                "/api/v1/route",
                json={"email": "eval@example.com", "message": ticket[args.lang]},
            )
            seconds = time.perf_counter() - started
            body = response.json() if response.status_code == 200 else {}
            results.append(
                {
                    "id": ticket["id"],
                    "expected": ticket["department"],
                    "got": body.get("department", f"HTTP {response.status_code}"),
                    "probability": body.get("probability"),
                    "seconds": round(seconds, 3),
                    "engine": body.get("engine", ""),
                }
            )
            mark = "ok  " if results[-1]["got"] == ticket["department"] else "MISS"
            print(f"{mark} {ticket['id']} {results[-1]['got']:16} {seconds:6.2f}s", flush=True)

    engine = next((row["engine"] for row in results if row["engine"]), "unknown")
    name = f"{engine}-{args.tag}" if args.tag else engine
    out = HERE / "results" / f"{name}-{args.lang}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    hits = sum(row["got"] == row["expected"] for row in results)
    print(f"\n{name} / {args.lang}: {hits}/{len(results)} correct, "
          f"median {statistics.median(row['seconds'] for row in results):.2f}s -> {out}")
    per_department = Counter(row["expected"] for row in results if row["got"] == row["expected"])
    for department in sorted({row["expected"] for row in results}):
        print(f"  {department:16} {per_department[department]}/"
              f"{sum(row['expected'] == department for row in results)}")


if __name__ == "__main__":
    main()
