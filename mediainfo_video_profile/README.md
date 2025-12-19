# MediaInfo Format Profile Checker

A Python script that recursively scans directories for MKV files and checks their video format profiles using MediaInfo. Designed to identify HEVC/H.265 format profiles that are **not fully compatible** with older media players (such as old FireTVs).

## Purpose

The main goal of this script is to identify video files with specific high-level format profiles that:
- **Cause playback issues** on older or less capable media players (e.g., old FireTVs)
- **Require transcoding** on media servers (like Jellyfin, Plex, Emby), which increases CPU/GPU usage and server load

Once identified, you may consider replacing those videos with versions encoded with "lower" (more compatible) format profiles that:
- Work better on older devices without transcoding
- Reduce server load by allowing direct playback/streaming
- Improve overall media server performance

## Overview

This script:
- Recursively scans directories for `.mkv` files
- Extracts video format profile information using `mediainfo`
- Matches against predefined target profiles (incompatible profiles)
- Uses multiprocessing for fast parallel execution
- Reports all matching files with their format profiles for replacement consideration

## Features

- **Fast Parallel Processing**: Uses multiprocessing to check multiple files simultaneously
- **Recursive Scanning**: Automatically scans subdirectories
- **Verbose Mode**: Option to see all profiles found (even non-matches)
- **Customizable Jobs**: Control the number of parallel workers
- **Timeout Protection**: Prevents hanging on corrupted or problematic files
- **Summary Statistics**: Shows total files scanned and matches found

## Requirements

### Required Tools

- **Python 3.6+** - The script is written in Python 3
- **MediaInfo** - Command-line tool for extracting media metadata

### Installation

#### Install MediaInfo

```bash
# Ubuntu/Debian
sudo apt-get install mediainfo

# Arch Linux
sudo pacman -S mediainfo

# macOS
brew install mediainfo

# Verify installation
mediainfo --version
```

#### Python Dependencies

No external Python packages required! The script uses only the standard library:
- `argparse` - Command-line argument parsing
- `multiprocessing` - Parallel execution
- `subprocess` - Running mediainfo commands
- `pathlib` - Path handling

## Usage

### Basic Syntax

```bash
./mediainfo_format_profile.py <folder> [options]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `<folder>` | **Required.** Directory to scan recursively for MKV files |

### Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show all profiles found (even non-matches) |
| `-j N, --jobs N` | Number of parallel jobs (default: CPU count) |
| `-h, --help` | Show help message |

### Examples

#### Basic scan
```bash
./mediainfo_format_profile.py /path/to/videos
```

#### Verbose mode (show all profiles)
```bash
./mediainfo_format_profile.py /path/to/videos --verbose
```

#### Custom number of parallel jobs
```bash
./mediainfo_format_profile.py /path/to/videos -j 8
```

#### Combine options
```bash
./mediainfo_format_profile.py ~/Movies --verbose -j 4
```

## Target Format Profiles

The script checks for the following format profiles (case-sensitive):

- `Main 10@L5.1@High`
- `Main 10@L5@High`
- `Main 10@L5.2@High`
- `High 10@L5`

**Why these profiles?** These high-level HEVC/H.265 format profiles have two main issues:

1. **Device Compatibility**: They are **not fully compatible** with older media players, particularly older FireTV devices. Files with these profiles may experience playback issues, stuttering, or fail to play entirely on such devices.

2. **Server Transcoding**: When streaming to incompatible devices, media servers (Jellyfin, Plex, Emby, etc.) must **transcode** these files in real-time. This process:
   - Consumes significant CPU/GPU resources
   - Increases server load and power consumption
   - May cause buffering or playback issues if the server is underpowered
   - Limits the number of simultaneous streams the server can handle

**Solution:** Once identified, these files might be re-encoded with "lower" format profiles (e.g., `Main 10@L4@High` or `Main@L4@High`) for:
- Better compatibility with older players (direct playback)
- Reduced server load (no transcoding needed)
- Improved overall media server performance

The script can be easily modified to check for different profiles by editing the `TARGET_PROFILES` list in the script.

## Output Format

### Normal Mode

Only shows matching files:

```
Scanning directory (recursively): /path/to/videos
Using 8 parallel jobs

MATCH: /path/to/videos/movie1.mkv
    Format profile: Main 10@L5.1@High
MATCH: /path/to/videos/subdir/movie2.mkv
    Format profile: Main 10@L5@High

Scan complete:
  Files scanned: 150
  Matches found: 2
```

### Verbose Mode

Shows all files checked and their profiles:

```
Scanning directory (recursively): /path/to/videos
Using 8 parallel jobs
Verbose mode: showing all profiles

Checking: /path/to/videos/movie1.mkv
    Profile: 'Main 10@L5.1@High'
Checking: /path/to/videos/movie2.mkv
    Profile: 'High@L4@Main'
SKIP: /path/to/videos/movie3.mkv (no video track or cannot read)
MATCH: /path/to/videos/movie1.mkv
    Format profile: Main 10@L5.1@High

Scan complete:
  Files scanned: 150
  Matches found: 1
```

## Performance

The script uses Python's `multiprocessing` module to process files in parallel, making it significantly faster than sequential processing, especially when scanning large directories with many files.

- **Default**: Uses all available CPU cores
- **Custom**: Specify exact number of jobs with `-j` option
- **Timeout**: Each file has a 30-second timeout to prevent hanging on corrupted files

### Performance Tips

- Use more jobs (up to CPU count) for faster processing on large directories
- Use fewer jobs if you want to reduce system load
- Verbose mode adds slight overhead due to additional output

## Use Case / Workflow

**Typical workflow:**
1. Run the script on your video library to identify incompatible files
2. Review the list of matching files (those with incompatible profiles)
3. Re-encode those files with lower format profiles for better compatibility
4. Replace the original files with the re-encoded versions
5. Verify playback works on your target devices (e.g., old FireTVs)
6. Monitor server load - transcoding should no longer be needed for these files

**Example scenarios:**

**Scenario 1: Device Compatibility**
- You have a large video library with mixed format profiles
- Some files won't play on your old FireTV device
- Use this script to quickly identify which files have the problematic profiles
- Re-encode only those specific files instead of re-encoding everything

**Scenario 2: Server Performance**
- Your media server (Jellyfin/Plex/Emby) is experiencing high CPU/GPU usage
- You notice many files are being transcoded during playback
- Use this script to identify files that require transcoding
- Re-encode with lower profiles to enable direct playback and reduce server load
- This allows your server to handle more simultaneous streams

## How It Works

1. **Directory Validation**: Checks if the provided path is a valid, readable directory
2. **File Discovery**: Recursively finds all `.mkv` files using `pathlib.Path.rglob()`
3. **Parallel Processing**: Uses multiprocessing pool to process files concurrently
4. **Profile Extraction**: For each file, runs `mediainfo` to extract the format profile
5. **Matching**: Compares extracted profile against target profiles list
6. **Reporting**: Displays matches and provides summary statistics

## Error Handling

- **Missing MediaInfo**: Exits with error if `mediainfo` command is not found
- **Invalid Directory**: Validates directory exists and is readable
- **Corrupted Files**: Uses timeout to prevent hanging on problematic files
- **No Video Track**: Skips files without video tracks (shown in verbose mode)

## Customization

### Changing Target Profiles

Edit the `TARGET_PROFILES` list in the script:

```python
TARGET_PROFILES = [
    "Main 10@L5.1@High",
    "Main 10@L5@High",
    "Main 10@L5.2@High",
    "High 10@L5",
    "Your Custom Profile Here",  # Add your own
]
```

### Adjusting Timeout

Modify the timeout value in the `get_format_profile()` function:

```python
timeout=30,  # Change this value (in seconds)
```

## Limitations

- Only processes MKV files (`.mkv` extension)
- Only checks video format profiles (not audio or other tracks)
- Requires MediaInfo to be installed and accessible in PATH
- Case-sensitive profile matching
- 30-second timeout per file (may skip very large or slow-to-read files)

## Troubleshooting

### "mediainfo command not found"
- Install MediaInfo (see Installation section)
- Ensure MediaInfo is in your PATH
- Verify with: `mediainfo --version`

### "is not a valid directory"
- Check that the path exists
- Ensure you have read permissions
- Use absolute paths if relative paths don't work

### No matches found
- Use `--verbose` to see all profiles found
- Verify your files actually have the target profiles
- Check that files are valid MKV files with video tracks

### Script hangs or is slow
- Reduce number of jobs with `-j` option
- Check for corrupted files that might be causing timeouts
- Use verbose mode to see which files are being processed

### Testing Issues
If you suspect the script is not identifying profiles correctly, run `./mediainfo_format_profile.py --test` to ensure the internal logic is working correctly with your system's python version.

### Permission errors
- Ensure you have read access to the directory and files
- Check file permissions: `ls -l /path/to/files`

## License

This script is provided as-is for personal use.
