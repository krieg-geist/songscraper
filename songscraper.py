#!/usr/bin/env python3

import argparse
import os
import re
import sys
import requests
from urllib.parse import urlparse

SONGSTERR_META = "https://www.songsterr.com/api/meta/{song_id}/revisions"
SONGSTERR_REVISION = "https://www.songsterr.com/api/revision/{revision_id}"
SONGSTERR_SEARCH = "https://www.songsterr.com/api/songs?size={size}&pattern={pattern}"

def extract_song_id(url: str) -> int:
    """
    Extracts the numeric song ID from a Songsterr URL.
    """
    m = re.search(r"-s(\d+)", url)
    if not m:
        raise ValueError("Could not extract song ID from URL")
    return int(m.group(1))


def get_revisions(song_id: int) -> list[dict]:
    url = SONGSTERR_META.format(song_id=song_id)
    r = requests.get(url, timeout=15)
    r.raise_for_status()

    revisions = r.json()
    if not revisions:
        raise RuntimeError("No revisions returned")

    return revisions


def get_latest_revision_id(revisions: list[dict]) -> int:
    # Highest revisionId wins
    return max(rev["revisionId"] for rev in revisions)


def search_songs(pattern: str, size: int) -> list[dict]:
    url = SONGSTERR_SEARCH.format(size=size, pattern=pattern)
    r = requests.get(url, timeout=15)
    r.raise_for_status()

    songs = r.json()
    if not songs:
        raise RuntimeError("No songs found for search")

    return songs


def prompt_song_choice(songs: list[dict]) -> int:
    if len(songs) == 1:
        return songs[0]["songId"]

    print("Search results:")
    for idx, song in enumerate(songs, start=1):
        song_id = song.get("songId", "?")
        artist = song.get("artist", "?")
        title = song.get("title", "?")
        print(f"{idx}) id={song_id} artist={artist} title={title}")

    while True:
        choice = input("Choose a song number: ").strip()
        if not choice.isdigit():
            print("Please enter a number from the list.")
            continue
        idx = int(choice)
        if 1 <= idx <= len(songs):
            return songs[idx - 1]["songId"]
        print("Please enter a valid number from the list.")


def prompt_revision_choice(revisions: list[dict]) -> int:
    if len(revisions) == 1:
        return revisions[0]["revisionId"]

    print("Available revisions:")
    for idx, rev in enumerate(revisions, start=1):
        revision_id = rev.get("revisionId", "?")
        created_at = rev.get("createdAt", "?")
        author = rev.get("author", "?")
        profile_name = author.get("profileName", "?")
        print(f"{idx}) revisionId={revision_id} createdAt={created_at} author={profile_name}")

    while True:
        choice = input("Choose a revision number (Enter for latest): ").strip()
        if choice == "":
            return get_latest_revision_id(revisions)
        if not choice.isdigit():
            print("Please enter a number from the list.")
            continue
        idx = int(choice)
        if 1 <= idx <= len(revisions):
            return revisions[idx - 1]["revisionId"]
        print("Please enter a valid number from the list.")


def sanitize_filename(s: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", s)


def download_gp_file(revision_id: int, out_dir: str):
    url = SONGSTERR_REVISION.format(revision_id=revision_id)
    r = requests.get(url, timeout=15)
    r.raise_for_status()

    data = r.json()

    source_url = data.get("source")
    if not source_url:
        raise RuntimeError("No GP export URL found in revision data")

    artist = sanitize_filename(data.get("artist", "Unknown Artist"))
    title = sanitize_filename(data.get("title", "Unknown Title"))

    ext = os.path.splitext(urlparse(source_url).path)[1]
    if not ext:
        ext = ".gp"

    filename = f"{artist} - {title}{ext}"
    out_path = os.path.join(out_dir, filename)

    print(f"Downloading: {source_url}")
    with requests.get(source_url, stream=True, timeout=30) as resp:
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    print(f"Saved as: {out_path}")


def load_urls_from_file(path: str) -> list[str]:
    if path == "-":
        lines = sys.stdin.read().splitlines()
    else:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    urls: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def is_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def build_song_ids_from_urls(urls: list[str]) -> list[int]:
    return [extract_song_id(url) for url in urls]


def prompt_search_text() -> str:
    search_text = input("Search text: ").strip()
    if not search_text:
        raise RuntimeError("Search text cannot be empty")
    return search_text


def choose_song_id(search_text: str, max_results: int) -> int:
    songs = search_songs(search_text, max_results)
    return prompt_song_choice(songs)


def resolve_song_ids(urls: list[str], interactive: bool, max_results: int) -> list[int]:
    if interactive:
        if urls:
            if all(is_url(u) for u in urls):
                return build_song_ids_from_urls(urls)
            search_text = " ".join(urls).strip()
            if not search_text:
                raise RuntimeError("Search text cannot be empty")
            return [choose_song_id(search_text, max_results)]
        return [choose_song_id(prompt_search_text(), max_results)]

    if not urls:
        raise RuntimeError("No URLs or search selection provided")
    return build_song_ids_from_urls(urls)


def main():
    parser = argparse.ArgumentParser(
        description="Download Songsterr GP files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  songsterr_dl.py https://www.songsterr.com/a/wsa/pissgrave-rusted-wind-tab-s505453\n"
            "  songsterr_dl.py -o ./tabs URL1 URL2\n"
            "  songsterr_dl.py -i viagra boys sports\n"
            "  songsterr_dl.py -i https://www.songsterr.com/a/wsa/amebix-chain-reaction-tab-s68807\n"
            "  songsterr_dl.py -f urls.txt\n"
            "  cat urls.txt | songsterr_dl.py -f -\n"
        ),
    )
    parser.add_argument("url", nargs="*", help="Songsterr tab URL(s)")
    parser.add_argument("-o", "--out", default="./output", help="Output directory")
    parser.add_argument("-f", "--file", help="Path to text file with one URL per line (use '-' for stdin)")
    parser.add_argument("-i", "--interactive", action="store_true",
                        help="Interactive mode: search by terms or choose revisions")
    parser.add_argument("--max-results", type=int, default=20,
                        help="Max search results to display with --interactive search")

    args = parser.parse_args()

    try:
        os.makedirs(args.out, exist_ok=True)

        urls = list(args.url or [])
        if args.file:
            urls.extend(load_urls_from_file(args.file))
        elif not urls and not sys.stdin.isatty() and not args.interactive:
            urls.extend(load_urls_from_file("-"))

        urls = dedupe_preserve_order(urls)

        song_ids = resolve_song_ids(urls, args.interactive, args.max_results)

        for song_id in song_ids:
            print(f"Song ID: {song_id}")

            revisions = get_revisions(song_id)
            if args.interactive:
                revision_id = prompt_revision_choice(revisions)
                print(f"Selected revision ID: {revision_id}")
            else:
                revision_id = get_latest_revision_id(revisions)
                print(f"Latest revision ID: {revision_id}")

            download_gp_file(revision_id, args.out)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
