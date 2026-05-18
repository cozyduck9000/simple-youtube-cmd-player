import subprocess
import threading
import time
from yt_dlp import YoutubeDL


# =========================
# GLOBAL STATE
# =========================
QUEUE = []
RECOMMENDED = []

CURRENT_PROCESS = None

AUTOPLAY = True
ENGINE_RUNNING = True


# =========================
# LOGGER
# =========================
class NoLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


# =========================
# FORMAT DURATION
# =========================
def format_duration(seconds):

    if not seconds:
        return "??:??"

    seconds = int(seconds)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"

    return f"{m}:{s:02d}"


# =========================
# SEARCH YOUTUBE
# =========================
def search_youtube(query, max_results=10):

    with YoutubeDL({
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "cachedir": False,
        "logger": NoLogger(),
    }) as ydl:

        info = ydl.extract_info(
            f"ytsearch{max_results}:{query}",
            download=False
        )

    results = []

    for e in info.get("entries", []) or []:

        if not e:
            continue

        vid = e.get("id")
        title = e.get("title")
        duration = e.get("duration")

        if vid and title:

            results.append({
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "duration": format_duration(duration)
            })

    return results


# =========================
# STREAM URL
# =========================
def get_stream(url):

    with YoutubeDL({
        "quiet": True,
        "skip_download": True,
        "format": "best[height<=720]/best",
        "cachedir": False,
        "logger": NoLogger(),
    }) as ydl:

        info = ydl.extract_info(url, download=False)

    return info.get("url")


# =========================
# VLC
# =========================
def stop_vlc():

    global CURRENT_PROCESS

    if CURRENT_PROCESS and CURRENT_PROCESS.poll() is None:
        CURRENT_PROCESS.terminate()


def play_vlc(url):

    global CURRENT_PROCESS

    CURRENT_PROCESS = subprocess.Popen(
        ["vlc", "--play-and-exit", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def is_vlc_running():

    global CURRENT_PROCESS

    return CURRENT_PROCESS and CURRENT_PROCESS.poll() is None


# =========================
# PLAY VIDEO
# =========================
def play_video(url, title="Unknown"):

    print(f"\n🎬 Playing: {title}")

    stream = get_stream(url)

    if not stream:
        print("❌ Stream failed")
        return

    play_vlc(stream)

    threading.Thread(
        target=load_recommendations,
        args=(url,),
        daemon=True
    ).start()


# =========================
# RECOMMENDATIONS
# =========================
def get_recommendations(url, limit=10):

    with YoutubeDL({
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "logger": NoLogger(),
    }) as ydl:

        info = ydl.extract_info(url, download=False)

    title = info.get("title", "")
    uploader = info.get("uploader", "")
    current_id = info.get("id")

    query = f"{uploader} {title}"

    with YoutubeDL({
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "logger": NoLogger(),
    }) as ydl:

        search = ydl.extract_info(
            f"ytsearch{limit+5}:{query}",
            download=False
        )

    results = []

    for e in search.get("entries", []):

        if not e:
            continue

        vid = e.get("id")
        t = e.get("title")

        if vid == current_id:
            continue

        if vid and t:

            results.append({
                "title": t,
                "url": f"https://www.youtube.com/watch?v={vid}"
            })

    return results[:limit]


def load_recommendations(url):

    global RECOMMENDED

    RECOMMENDED = get_recommendations(url)


# =========================
# QUEUE
# =========================
def add_to_queue(v):

    QUEUE.append(v)

    print(f"\n➕ Added to queue: {v['title']}")


def show_queue():

    if not QUEUE:
        print("\nQueue empty")
        return

    print("\n📺 UP NEXT:\n")

    for i, v in enumerate(QUEUE, 1):
        print(f"{i}. {v['title']}")


# =========================
# NEXT
# =========================
def get_next():

    if QUEUE:
        return QUEUE.pop(0)

    if RECOMMENDED:
        return RECOMMENDED.pop(0)

    return None


# =========================
# AUTOPLAY ENGINE
# =========================
def autoplay_engine():

    global AUTOPLAY

    while ENGINE_RUNNING:

        time.sleep(1)

        if not AUTOPLAY:
            continue

        if is_vlc_running():
            continue

        nxt = get_next()

        if nxt:
            play_video(nxt["url"], nxt["title"])
        else:
            AUTOPLAY = False


# =========================
# SEARCH HANDLER
# =========================
def handle_video_selection(video):

    if is_vlc_running():

        print("\n1. Play now")
        print("2. Add to queue")

        choice = input("\nSelect: ").strip()

        if choice == "1":

            stop_vlc()

            play_video(video["url"], video["title"])

        elif choice == "2":

            add_to_queue(video)

        else:
            print("Invalid")

    else:

        play_video(video["url"], video["title"])


# =========================
# MAIN
# =========================
def main():

    threading.Thread(
        target=autoplay_engine,
        daemon=True
    ).start()

    while True:

        print("\n=== VLC QUEUE PLAYER ===")
        print("1. Search Videos")
        print("2. Show Queue")
        print("3. Recommended")
        print("4. Toggle Autoplay")
        print("5. Exit")

        c = input("\nSelect: ").strip()

        # =====================
        # SEARCH
        # =====================
        if c == "1":

            q = input("\nSearch: ")

            results = search_youtube(q)

            if not results:
                print("No results")
                continue

            print()

            for i, v in enumerate(results, 1):
                print(f"{i}. {v['title']} [{v['duration']}]")

            try:

                pick = int(input("\nSelect: "))

                video = results[pick - 1]

                handle_video_selection(video)

            except:
                print("Invalid")

        # =====================
        # QUEUE
        # =====================
        elif c == "2":

            show_queue()

        # =====================
        # RECOMMENDED
        # =====================
        elif c == "3":

            if not RECOMMENDED:
                print("No recommendations yet")
                continue

            print()

            for i, v in enumerate(RECOMMENDED, 1):
                print(f"{i}. {v['title']}")

            try:

                pick = int(input("\nAdd to queue: "))

                add_to_queue(RECOMMENDED[pick - 1])

            except:
                print("Invalid")

        # =====================
        # AUTOPLAY
        # =====================
        elif c == "4":

            global AUTOPLAY

            AUTOPLAY = not AUTOPLAY

            print("Autoplay:", AUTOPLAY)

        # =====================
        # EXIT
        # =====================
        elif c == "5":

            break

        else:
            print("Invalid")


if __name__ == "__main__":
    main()
