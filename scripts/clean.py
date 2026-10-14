"""
scripts/clean.py — Delete a failed/partial experiment from LangSmith.

Only experiments attached to the chosen persona set's dataset are touched, so
cleaning a held-out run can never delete the dev-set experiment of the same
version (and vice versa). The dataset itself and its personas are kept.

Usage:
    python scripts/clean.py v5-directed                     # dev set
    python scripts/clean.py v4-turn-aware --personas heldout
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: F401,E402  (loads .env with override=True)
from langsmith import Client  # noqa: E402

DATASETS = {
    "dev": "ai-mock-interview-coach-evals",
    "heldout": "ai-mock-interview-coach-evals-heldout",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete experiments by name prefix within one dataset.")
    parser.add_argument("prefix", help="Experiment name prefix, e.g. v5-directed")
    parser.add_argument("--personas", choices=sorted(DATASETS), default="dev")
    args = parser.parse_args()

    client = Client()
    dataset_name = DATASETS[args.personas]
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception:
        print(f"Dataset '{dataset_name}' not found — nothing to clean.")
        return

    deleted = []
    for exp in client.list_projects(reference_dataset_id=dataset.id):
        if exp.name.startswith(args.prefix):
            print(f"Deleting experiment {exp.name} ({exp.id}) from {dataset_name}")
            client.delete_project(project_id=str(exp.id))
            deleted.append(exp.name)

    if not deleted:
        print(f"No experiments starting with '{args.prefix}' in {dataset_name} — nothing to wipe.")
    else:
        print(f"Wiped {len(deleted)} experiment(s): {deleted}")


if __name__ == "__main__":
    main()
