#!/usr/bin/env python3
"""
CLI entry point for docullim.

Usage:
    docullim [--config CONFIG_FILE] [--model MODEL] [--reset-cache] [--concurrency N] [--write] patterns...

Examples:
    docullim file1.py file2.py
    docullim "src/**/*.py"
    docullim --config docullim.json --model gpt-4 "src/**/*.py"
    docullim --reset-cache --concurrency 10 --write file1.py "src/**/*.py"
"""

import argparse
import json
import os
import sys
import multiprocessing

from docullim.config import load_config
from docullim.generator import process_file, collect_files
from docullim.cache import Cache


def process_file_worker(args):
    """
    Worker function for multiprocessing.

    Each worker creates its own cache instance in read-only mode,
    processes the file (with an option to write docstrings), then returns the result.
    """
    file_path, config, write = args
    cache = Cache()
    result = process_file(file_path, config, cache, write)
    cache.close()
    return file_path, result


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation for Python code marked with @docullim."
    )
    parser.add_argument(
        "patterns", type=str, nargs="+", help="File paths or glob patterns."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to JSON config file (default: docullim.json).",
    )
    parser.add_argument(
        "-m", "--model", type=str, help="Override model name from config."
    )
    parser.add_argument(
        "-r",
        "--reset-cache",
        action="store_true",
        help="Reset cache and generate fresh docs.",
    )
    parser.add_argument(
        "-n",
        "--concurrency",
        type=int,
        help="Max concurrent files to process (default: 5).",
    )
    parser.add_argument(
        "-w",
        "--write",
        action="store_true",
        help="Update source files with generated docstrings.",
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    if args.model:
        config["model"] = args.model

    # Set max concurrency from CLI or config (default to 5)
    max_concurrency = args.concurrency or config.get("max_concurrency", 2)

    # Determine cache location for main process
    cache_dir = os.path.join(os.getcwd(), ".docullim")
    db_path = os.path.join(cache_dir, "cache.sqlite")

    # Reset cache if requested
    if args.reset_cache and os.path.exists(db_path):
        os.remove(db_path)
        print("Cache reset: previous cache database removed.")

    # Collect files from provided patterns
    files = collect_files(args.patterns)
    if not files:
        print("No files found for the given patterns.", file=sys.stderr)
        sys.exit(1)

    # Use multiprocessing.Pool with a concurrency limit
    tasks = [(file, config, args.write) for file in files]
    all_docs = {}
    with multiprocessing.Pool(processes=max_concurrency) as pool:
        for file_path, docs in pool.imap_unordered(process_file_worker, tasks):
            if docs:
                all_docs[file_path] = docs

    print(json.dumps(all_docs, indent=2))


if __name__ == "__main__":
    main()
