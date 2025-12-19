#!/usr/bin/env python3
"""
Extract and check MKV files for specific Format profile values using mediainfo.
Recursively scans directories for .mkv files and reports matches.

Identifies high-level HEVC/H.265 format profiles that:
- Are not fully compatible with older media players (e.g., old FireTVs)
- May require transcoding on media servers, increasing CPU/GPU usage

OPTIMIZED: Uses multiprocessing for parallel execution (much faster than bash)

Usage: 
  ./mediainfo_format_profile.py <folder> [-v] [-j N]
  ./mediainfo_format_profile.py --test
"""

import argparse
import os
import signal
import subprocess
import sys
import unittest
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import List, Optional, Tuple
from unittest.mock import MagicMock, patch

# Format profiles to match (case-sensitive)
TARGET_PROFILES = [
    "Main 10@L5.1@High",
    "Main 10@L5@High",
    "Main 10@L5.2@High",
    "High 10@L5",
]


def check_mediainfo() -> None:
    """Check if mediainfo command is available."""
    try:
        subprocess.run(
            ["mediainfo", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: mediainfo command not found. Please install MediaInfo.", file=sys.stderr)
        sys.exit(1)


def init_worker():
    """Initializer for worker processes to ignore SIGINT.
    This ensures that when Ctrl+C is pressed, only the main process handles 
    the KeyboardInterrupt, preventing traceback spam from workers.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def get_format_profile(file_path: str) -> Optional[str]:
    """Extract Format profile from MKV file using mediainfo."""
    try:
        result = subprocess.run(
            ["mediainfo", "--Inform=Video;%Format_Profile%", file_path],
            capture_output=True,
            text=True,
            timeout=30,  # Prevent hanging on corrupted files
        )
        if result.returncode == 0:
            profile = result.stdout.strip()
            return profile if profile else None
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        pass
    return None


def process_file(args: Tuple[str, bool]) -> Optional[Tuple[str, str]]:
    """Process a single MKV file and return match info if found.
    
    Args:
        args: Tuple of (file_path, verbose_flag)
    
    Returns:
        Tuple of (file_path, profile) if match found, None otherwise
    """
    file_path, verbose = args
    profile = get_format_profile(file_path)
    
    if profile is None:
        if verbose:
            print(f"SKIP: {file_path} (no video track or cannot read)", flush=True)
        return None
    
    if verbose:
        print(f"Checking: {file_path}", flush=True)
        print(f"    Profile: '{profile}'", flush=True)
    
    if profile in TARGET_PROFILES:
        return (file_path, profile)
    
    return None


def scan_directory(directory: str, verbose: bool = False, num_jobs: int = None) -> None:
    """Scan directory recursively for MKV files and process them in parallel.
    
    Args:
        directory: Directory to scan
        verbose: Show all profiles found
        num_jobs: Number of parallel jobs (default: CPU count)
    """
    directory_path = Path(directory)
    
    if not directory_path.is_dir():
        print(f"Error: '{directory}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)
    
    if not os.access(directory_path, os.R_OK):
        print(f"Error: Cannot read directory: '{directory}'", file=sys.stderr)
        sys.exit(1)
    
    print(f"Scanning directory (recursively): {directory}")
    if num_jobs is None:
        num_jobs = cpu_count()
    print(f"Using {num_jobs} parallel jobs")
    if verbose:
        print("Verbose mode: showing all profiles")
    print()
    
    # Find all MKV files
    try:
        mkv_files = list(directory_path.rglob("*.mkv"))
    except KeyboardInterrupt:
        print("\nScan interrupted during file listing. Exiting...")
        sys.exit(130)

    file_count = len(mkv_files)
    
    if file_count == 0:
        print("No MKV files found in directory.")
        return
    
    # Process files in parallel
    try:
        # We use map_async with a timeout to allow the main thread to remain responsive 
        # to KeyboardInterrupt (Ctrl+C). Standard pool.map blocks signals.
        with Pool(processes=num_jobs, initializer=init_worker) as pool:
            async_result = pool.map_async(process_file, [(str(f), verbose) for f in mkv_files])
            
            # 999999 seconds is ~11 days; effectively infinite wait but allows signal handling
            results = async_result.get(timeout=999999)
            
    except KeyboardInterrupt:
        print("\nScan interrupted by user (Ctrl+C). Exiting...")
        sys.exit(130)
    
    # Filter out None results (non-matches)
    matches = [r for r in results if r is not None]
    match_count = len(matches)
    
    # Display matches
    for file_path, profile in matches:
        print(f"MATCH: {file_path}")
        print(f"    Format profile: {profile}")
    
    # Summary
    print()
    print("Scan complete:")
    print(f"  Files scanned: {file_count}")
    print(f"  Matches found: {match_count}")
    
    if match_count == 0:
        print("  No matching MKV files found.")
        print("  Tip: Use --verbose to see all profiles found")


# --- Test Suite ---

class TestMediaScanner(unittest.TestCase):
    """Unit tests for scanner functionality."""

    @patch("subprocess.run")
    def test_get_format_profile_success(self, mock_run):
        """Test extraction of a valid profile."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Main 10@L5.1@High\n"
        mock_run.return_value = mock_result

        profile = get_format_profile("dummy.mkv")
        self.assertEqual(profile, "Main 10@L5.1@High")

    @patch("subprocess.run")
    def test_get_format_profile_failure(self, mock_run):
        """Test handling of mediainfo failure."""
        mock_run.side_effect = subprocess.SubprocessError("Error")
        profile = get_format_profile("broken.mkv")
        self.assertIsNone(profile)

    @patch("subprocess.run")
    def test_process_file_match(self, mock_run):
        """Test that process_file identifies a target profile."""
        # Mock mediainfo to return a matching profile
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = TARGET_PROFILES[0]
        mock_run.return_value = mock_result

        result = process_file(("video.mkv", False))
        self.assertIsNotNone(result)
        self.assertEqual(result, ("video.mkv", TARGET_PROFILES[0]))

    @patch("subprocess.run")
    def test_process_file_no_match(self, mock_run):
        """Test that process_file ignores non-matching profiles."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Main@L4@Main" # Safe profile
        mock_run.return_value = mock_result

        result = process_file(("video.mkv", False))
        self.assertIsNone(result)


def run_tests():
    """Run the test suite."""
    print("Running internal tests...")
    # Create a test suite and run it
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMediaScanner)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check MKV files for specific Format profile values that may require transcoding",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/videos
  %(prog)s /path/to/videos --verbose
  %(prog)s /path/to/videos -j 8
  %(prog)s --test
        """,
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Directory to scan recursively for MKV files",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show all profiles found (even non-matches)",
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=None,
        help=f"Number of parallel jobs (default: CPU count = {cpu_count()})",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run internal unit tests and exit",
    )
    
    args = parser.parse_args()

    if args.test:
        run_tests()
    
    if not args.folder:
        parser.print_help()
        sys.exit(1)
    
    # Check prerequisites
    check_mediainfo()
    
    # Scan directory
    scan_directory(args.folder, args.verbose, args.jobs)


if __name__ == "__main__":
    main()