"""
Closed-Won Activation Pipeline — Main Entry Point

Usage:
    python main.py                    # Run with default demo deal
    python main.py deal.json          # Run with a specific deal file
    python main.py --serve            # Start FastAPI webhook server
"""
import json
import sys
import os


def run_pipeline(deal: dict) -> dict:
    """Run the full activation pipeline on a deal record."""
    raise NotImplementedError


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--serve':
        # Start webhook server
        raise NotImplementedError("FastAPI server not yet implemented")
    elif len(sys.argv) > 1:
        # Load deal from file
        with open(sys.argv[1]) as f:
            deal = json.load(f)
        result = run_pipeline(deal)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python main.py [deal.json | --serve]")


if __name__ == "__main__":
    main()
