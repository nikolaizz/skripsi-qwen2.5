"""
Pipeline lokal untuk menguji alur deskripsi → terjemahan → TTS → playback
menggunakan kamera dan speaker laptop (Windows).

Jalankan dari root repo:

    python testing-pipeline/run_pipeline_windows.py

Opsional:
    --loop        : jalankan berulang
    --delay 2.5   : jeda antar-run saat loop (detik)

Dependensi utama:
- opencv-python
- requests
- argostranslate + pasangan bahasa en->id
- piper-tts (beserta model .onnx yang sudah ada)
"""

import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Pastikan modul menggunakan direktori yang sama dengan pipeline utama
os.chdir(PROJECT_ROOT)

from datetime import datetime

from generateText import generate_text_from_camera  # type: ignore
from generateTTS import load_voice, tts_from_text  # type: ignore
from latencyLogger import log_latency  # type: ignore
from translateText import translate_text_to_indonesian, persist_translated_text  # type: ignore

try:
    import winsound
except ImportError:
    winsound = None


def play_wav_windows(file_path: str) -> None:
    """
    Putar file WAV menggunakan winsound (tersedia bawaan Windows).
    """
    if not os.path.exists(file_path):
        print(f"[ERROR] File audio tidak ditemukan: {file_path}")
        return

    if winsound is None:
        print("[WARN] winsound tidak tersedia. Audio tidak diputar.")
        return

    print(f"[INFO] Memutar audio di speaker laptop: {file_path}")
    winsound.PlaySound(file_path, winsound.SND_FILENAME)


class LocalPipeline:
    """
    Pipeline tanpa GPIO, cocok untuk uji coba di laptop.
    """

    def __init__(self):
        self.voice = None

    def run_once(self) -> bool:
        """
        Jalankan pipeline satu kali. Return True bila sukses utuh.
        """
        print("\n================= PIPELINE WINDOWS DIMULAI =================")
        start_time = datetime.now()

        text, txt_path, timings = generate_text_from_camera(return_timings=True)
        if not text:
            print("[PIPELINE] Gagal mendapatkan teks dari model visi.")
            print("================= PIPELINE WINDOWS GAGAL =================\n")
            return False

        translation_start = datetime.now()
        spoken_text, translated = translate_text_to_indonesian(text)
        translation_end = datetime.now()
        translation_duration = (translation_end - translation_start).total_seconds()
        if translated:
            print("[PIPELINE] Teks berhasil diterjemahkan ke Bahasa Indonesia.")
            persist_translated_text(txt_path, spoken_text)
        else:
            print("[PIPELINE] Memakai teks asli (en) karena terjemahan belum siap.")

        if self.voice is None:
            self.voice = load_voice()

        tts_start = datetime.now()
        wav_path = tts_from_text(spoken_text, voice=self.voice)
        tts_end = datetime.now()
        tts_duration = (tts_end - tts_start).total_seconds()
        if not wav_path:
            print("[PIPELINE] Tahap TTS gagal.")
            print("================= PIPELINE WINDOWS GAGAL =================\n")
            return False

        speech_start_time = tts_end
        stage_durations = {
            "capture": timings.get("capture_seconds"),
            "vision_generate": timings.get("vision_seconds"),
            "translation": translation_duration,
            "tts": tts_duration,
        }
        log_latency(start_time, speech_start_time, context=wav_path or "", stage_durations=stage_durations)
        play_wav_windows(wav_path)
        print("================= PIPELINE WINDOWS SELESAI =================\n")
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Uji pipeline deskripsi visual di Windows.")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Jalankan pipeline berulang hingga dihentikan (Ctrl+C).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Jeda antar eksekusi saat --loop aktif (detik).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    pipeline = LocalPipeline()

    try:
        while True:
            pipeline.run_once()
            if not args.loop:
                break
            time.sleep(max(args.delay, 0.5))
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh pengguna.")


if __name__ == "__main__":
    main()

