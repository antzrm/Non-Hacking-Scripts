# MKV ASS/SSA to SRT Subtitle Converter

A robust Bash script that recursively scans MKV files, detects embedded **ASS/SSA** subtitles, and converts them to **SRT** format.

This tool is designed to improve subtitle compatibility for media servers like **Jellyfin**, **Plex**, and **Emby**, which often require transcoding when playing ASS/SSA formats on certain clients (TVs, Roku, etc.).

## 🚀 Features

* **Recursive Scanning:** Processes entire directory trees or single files.
* **Format Specific:** Only extracts `ASS` and `SSA` subtitles (ignores existing SRTs or PGS images).
* **Strict Language Filtering:** Automatically identifies and maps specific languages (Default: **Spanish**, **English**, **French**).
* **Smart Skipping:** Skips files that already have an external `.srt` file to avoid duplicates.
* **Zero-Config Docker Support:** If `ffmpeg` is not installed on the host, it automatically uses the `linuxserver/ffmpeg` Docker container.
* **Quiet by Default:** Runs silently in cron jobs or scripts, only outputting text when a file is actually converted. Use `-v` for full logs.

## 📋 Prerequisites

You need **one** of the following installed:

1.  **FFmpeg & FFprobe** (Recommended)
    * Ubuntu/Debian: `sudo apt install ffmpeg`
    * MacOS: `brew install ffmpeg`
2.  **Docker**
    * If `ffmpeg` is missing, the script will automatically attempt to use Docker.

## 📥 Installation

1.  Download the script:
2.  Make it executable:
    ```bash
    chmod +x ass-to-srt.sh
    ```

## 🛠 Usage

```bash
./ass_to_srt.sh -i <input_path> [options]

Options
Flag	Description
-i <path>	Required. Input file (video.mkv) or directory (/mnt/media).
-l <days>	Optional. Only process files modified in the last X days. Useful for cron jobs.
-v	Verbose Mode. Shows every file scanned and detailed progress.
-h	Show help message.

#### Examples
1. Process a specific movie:
./ass_to_srt.sh -i "/mnt/media/Movies/Akira (1988).mkv"

# 2. Scan an entire TV Show library:
./ass_to_srt.sh -i "/mnt/media/Anime"

# 3. Run via Cron (Recent files only): To keep your library updated without re-scanning everything, use the -l flag to check only files added in the last 2 days:
# Run every night at 3 AM
0 3 * * * /home/user/scripts/ass_to_srt.sh -i /mnt/media -l 2

# 4. Debugging/Verbose Output: See exactly which stream is being extracted:
./ass_to_srt.sh -i /mnt/downloads -v
```

🌍 Language Support

By default, the script only extracts specific languages to prevent clutter. It maps ISO-639 codes to file extensions:
	
| MKV Tag | Output Extension |
|--------|-------------|
| `spa` | .es.srt |
| `eng` | .en.srt |
| `fre` / `fra` | .fr.srt |


To add more languages (e.g., German, Italian), edit the LANGUAGE_MAP array at the top of the script.

📝 Output Naming

If the input is Movie.mkv and it contains an English ASS track:

    Output: Movie.en.srt

Jellyfin/Plex will automatically detect this as an External subtitle track.

📄 License

MIT License. Feel free to modify and distribute.