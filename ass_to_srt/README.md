# MKV ASS/SSA to SRT Subtitle Converter
A robust, safe Bash script that recursively scans MKV files, detects embedded **ASS/SSA** subtitles, and converts them to **SRT** format.

This tool is designed to improve subtitle compatibility for media servers like **Jellyfin**, **Plex**, and **Emby**, which often require transcoding when playing ASS/SSA formats on certain clients (TVs, Roku, etc.).

## 🚀 Features
* **Recursive Scanning:** Processes entire directory trees or single files.
* **Format Specific:** Only extracts `ASS` and `SSA` subtitles (ignores existing SRTs or PGS images).
* **Forced Subtitle Support:** Automatically detects the "Forced" flag in the stream and correctly names the output (e.g., `Movie.en.forced.srt`).
* **Strict Metadata Safety:** **No guessing.** If a subtitle stream lacks a Language tag, it is skipped to prevent mislabeling.
* **Smart Skipping:** Skips files that already have an external `.srt` file to avoid duplicates.
* **Zero-Config Docker Support:** If `ffmpeg` is not installed on the host, it automatically uses the `linuxserver/ffmpeg` Docker container.
* **Silent by Default:** Runs quietly for cron jobs, printing only when a file is successfully converted. Use `-v` for detailed stream debugging.

## 📋 Prerequisites
You need **one** of the following installed:
1.  **FFmpeg & FFprobe** (Recommended)
    * Ubuntu/Debian: `sudo apt install ffmpeg`
    * MacOS: `brew install ffmpeg`
2.  **Docker**
    * If `ffmpeg` is missing, the script will automatically attempt to use the `linuxserver/ffmpeg` Docker container.

## 📥 Installation

1.  Download the script.
2.  Make it executable:
```bash
chmod +x ass-to-srt.sh
```

## 🛠 Usage

```bash
./ass_to_srt.sh -i <input_path> [options]
```

| **Flag**    | **Description**                                                                                                              |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `-i <path>` | **Required.** Input file (`video.mkv`) or directory (`/mnt/media`).                                                          |
| `-l <days>` | **Optional.** Only process files modified in the last X days. Useful for cron jobs.                                          |
| `-v`        | **Verbose Mode.** Shows every file scanned, detailed stream metadata (codec, lang, forced status), and reasons for skipping. |
| `-h`        | Show help message.                                                                                                           |
### Examples
**1. Process a specific movie:**
```bash
./ass_to_srt.sh -i "/mnt/media/Movies/Akira (1988).mkv"
```

**2. Scan an entire TV Show library:**
```bash
./ass_to_srt.sh -i "/mnt/media/Anime"
```

**3. Run via Cron (Recent files only):** To keep your library updated without re-scanning everything, use `-l` to check only files modified in the last 2 days:

```bash
# Run every night at 3 AM
0 3 * * * /home/user/scripts/ass_to_srt.sh -i /mnt/media -l 2
```

**4. Debugging/Verbose Output:** See exactly which streams are being detected or skipped:

```bash
./ass_to_srt.sh -i /mnt/downloads -v
```

## 📝 Output Naming & Behavior

The script strictly adheres to the metadata found inside the MKV file.

**Scenario A: Standard Subtitle**
- Input: `Movie.mkv` (Contains English ASS track)
- Output: `Movie.en.srt`

**Scenario B: Forced Subtitle**
- Input: `Movie.mkv` (Contains Spanish ASS track with **Forced Display** flag set)
- Output: `Movie.es.forced.srt`

_Note: Media servers like Plex/Jellyfin automatically detect the `.forced.` tag and enable these subtitles by default._

## 🌍 Language Configuration

To prevent cluttering your folders with unwanted languages, the script uses a strict allowlist. It maps **ISO 639-2 (3-letter codes)** to file extensions.

Default configuration: | MKV Tag | Output Extension | | :--- | :--- | | `spa` | `.es` | | `eng` | `.en` | | `fre` / `fra` | `.fr` |

**To add more languages:** Open the script and edit the `LANGUAGE_MAP` array at the top:

```bash
declare -A LANGUAGE_MAP=(
    ["spa"]=".es"
    ["eng"]=".en"
    ["ger"]=".de"  # Added German
    ["ita"]=".it"  # Added Italian
)
```
## ⚠️ Important Notes
- **Missing Metadata:** If your MKV file has a subtitle stream but **no Language tag** is set, this script will **SKIP** it. This is a safety feature to prevent overwriting files with the wrong language. Run with `-v` to see if streams are being skipped due to missing tags.
## 📄 License
MIT License. Feel free to modify and distribute.
