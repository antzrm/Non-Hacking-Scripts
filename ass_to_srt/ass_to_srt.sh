#!/bin/bash

# Extract ASS/SSA subtitles from MKV files (recursively) and convert them to SRT
# BEHAVIOR: 
# - Normal mode: Silent scanning. Prints ONLY when a file is actually converted.
# - Verbose (-v): Prints files found, detailed stream metadata, and specific reasons for skipping.
# - Forced Subs: Detects forced flag and names output as *.lang.forced.srt
# - SAFETY: No guessing. If language metadata is missing, the stream is skipped.

set -u # Exit on undefined variables

# ============================================================================
# Configuration
# ============================================================================

# Language mapping: ISO 639-2 (3 letters) to File Extension
declare -A LANGUAGE_MAP=(
    ["spa"]=".es"
    ["eng"]=".en"
    ["fre"]=".fr"
    ["fra"]=".fr"
)

# ============================================================================
# Functions
# ============================================================================

function check_dependencies() {
    local missing_tools=()
    if ! command -v ffprobe &> /dev/null; then missing_tools+=("ffprobe"); fi
    if ! command -v ffmpeg &> /dev/null && ! command -v docker &> /dev/null; then missing_tools+=("ffmpeg or docker"); fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        echo "Error: Missing required tools: ${missing_tools[*]}" >&2
        exit 1
    fi
}

function cleanup() {
    echo -e "\nInterrupted. Exiting..."
    exit 1
}
trap cleanup SIGINT

function show_help() {
    cat << EOF
Usage: $0 -i <path> [-l <days>] [-v] [-h]
Options:
    -i <path>    Input path (file or directory)
    -l <days>    Only process files newer than X days
    -v           Verbose mode (Show all files scanned and debug metadata)
    -h           Show this help message
EOF
    exit 0
}

function convert_subtitle() {
    local video_path="$1"
    local sub_index="$2"
    local output_path="$3"
    
    if command -v ffmpeg &> /dev/null; then
        ffmpeg -i "$video_path" -map "0:${sub_index}" -c:s text "$output_path" -y -loglevel error -nostats < /dev/null
    elif command -v docker &> /dev/null; then
        local abs_video_path abs_output_path
        abs_video_path=$(realpath "$video_path")
        abs_output_path=$(realpath "$output_path")
        sudo docker run --rm -v /:/config linuxserver/ffmpeg \
            -i "/config${abs_video_path}" \
            -map "0:${sub_index}" \
            -c:s text \
            "/config${abs_output_path}"
    else
        return 1
    fi
}

function process_video_file() {
    local video_file="$1"
    local verbose_flag="${2:-}"
    local base_name
    
    base_name="${video_file%.mkv}"
    
    # 1. Get ONLY Index and Codec first (This is safe, these always exist)
    local stream_list
    if ! stream_list=$(ffprobe -v error -select_streams s -show_entries stream=index,codec_name -of csv=p=0 "$video_file" 2>/dev/null); then
        [[ -n "$verbose_flag" ]] && echo "Warning: Failed to probe $video_file" >&2
        return 1
    fi

    if [[ -z "$stream_list" ]]; then
         [[ -n "$verbose_flag" ]] && echo "  [SKIP] No subtitle streams found"
         return 0
    fi

    # 2. Iterate through found streams
    while IFS=, read -r idx codec; do
        idx=$(echo "$idx" | xargs)
        codec=$(echo "$codec" | xargs)

        # Check Codec (Only process ASS/SSA)
        if [[ "$codec" != "ass" && "$codec" != "ssa" ]]; then
            continue
        fi

        # 3. SAFER QUERY: Get Language and Forced flag INDIVIDUALLY for this specific index.
        # This prevents column shifting if the language tag is missing.
        local lang
        local is_forced
        
        # Get Language Tag (Returns empty string if missing)
        lang=$(ffprobe -v error -select_streams "$idx" -show_entries stream_tags=language -of default=noprint_wrappers=1:nokey=1 "$video_file" 2>/dev/null)
        lang=$(echo "$lang" | xargs) # Trim whitespace

        # Get Forced Disposition (Returns 0 or 1)
        is_forced=$(ffprobe -v error -select_streams "$idx" -show_entries stream_disposition=forced -of default=noprint_wrappers=1:nokey=1 "$video_file" 2>/dev/null)
        is_forced=$(echo "$is_forced" | xargs)

        # DEBUG OUTPUT: Show exactly what we found
        if [[ -n "$verbose_flag" ]]; then
            echo "      [DEBUG] Stream #$idx: Codec='$codec', Lang='$lang', Forced='$is_forced'"
        fi

        # 4. Validate Language
        if [[ -z "$lang" ]]; then
            if [[ -n "$verbose_flag" ]]; then
                echo "      [SKIP] Stream #$idx: Metadata 'Language' is empty/undefined. Skipping."
            fi
            continue
        fi

        # 5. Check Language Map
        if [[ -n "${LANGUAGE_MAP[$lang]:-}" ]]; then
            local lang_ext="${LANGUAGE_MAP[$lang]}"
            
            # Naming logic: .lang.forced.srt
            local suffix="${lang_ext}.srt"
            local type_label=""
            
            if [[ "$is_forced" == "1" ]]; then
                suffix="${lang_ext}.forced.srt"
                type_label=" (FORCED)"
            fi
            
            local output_file="${base_name}${suffix}"

            # Check if SRT exists
            if [[ -f "$output_file" ]]; then
                [[ -n "$verbose_flag" ]] && echo "      [SKIP] $output_file already exists"
                continue
            fi

            # PRINTING LOGIC:
            if [[ -z "$verbose_flag" ]]; then
                echo "Converting: $(basename "$video_file") ($lang)${type_label} -> $(basename "$output_file")"
            else
                echo "      [EXTRACT] Stream #$idx ($lang)${type_label} -> $output_file"
            fi

            if convert_subtitle "$video_file" "$idx" "$output_file"; then
                 [[ -n "$verbose_flag" ]] && echo "      [OK] Success"
            else
                 echo "      [ERROR] Conversion failed for stream $idx" >&2
            fi

        else
            if [[ -n "$verbose_flag" ]]; then
                echo "      [SKIP] Stream #$idx: Language '$lang' not in filter list"
            fi
        fi

    done <<< "$stream_list"
}

function convert_subtitles() {
    local input_path="$1"
    local days_filter="${2:-}"
    local verbose_flag="${3:-}"
    
    input_path=$(realpath -e "$input_path" 2>/dev/null || echo "$input_path")
    
    local found_files=()
    
    if [[ -f "$input_path" && "$input_path" == *.mkv ]]; then
        found_files+=("$input_path")
    elif [[ -d "$input_path" ]]; then
        local find_args=("find" "$input_path" "-type" "f" "-name" "*.mkv")
        if [[ -n "$days_filter" ]]; then
             find_args+=("-newermt" "${days_filter} days ago")
        fi
        
        while IFS= read -r -d '' f; do
            found_files+=("$f")
        done < <("${find_args[@]}" -print0)
    else
        echo "Error: Invalid input: $input_path" >&2
        return 1
    fi

    local total=${#found_files[@]}
    if [[ $total -eq 0 ]]; then
        echo "No MKV files found matching criteria."
        return 0
    fi

    if [[ -n "$verbose_flag" ]]; then
        echo "Found $total MKV file(s). Processing..."
    fi

    local current=0
    for file in "${found_files[@]}"; do
        ((current++))
        
        if [[ -n "$verbose_flag" ]]; then
            echo "[$current/$total] Processing: $file"
        fi
        
        process_video_file "$file" "$verbose_flag"
    done
}

function main() {
    local input_path=""
    local days_filter=""
    local verbose_flag=""
    
    while getopts "i:l:vh" opt; do
        case "$opt" in
            i) input_path="$OPTARG" ;;
            l) days_filter="$OPTARG" ;;
            v) verbose_flag="1" ;;
            h) show_help ;;
            *) show_help ;;
        esac
    done
    
    if [[ -z "$input_path" ]]; then
        echo "Error: Input path (-i) is required" >&2
        show_help
    fi
    
    check_dependencies
    convert_subtitles "$input_path" "$days_filter" "$verbose_flag"
}

main "$@"
