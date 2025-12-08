"""
Jalankan pipeline deskripsi visual secara batch menggunakan gambar lokal
di folder `testing-data/`. Cocok untuk uji akurasi tanpa perlu kamera/GPIO.

Contoh:
    python testing-pipeline/run_batch_testing_data.py
    python testing-pipeline/run_batch_testing_data.py --no-tts
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Pastikan direktori kerja sama seperti pipeline utama
os.chdir(PROJECT_ROOT)

import generateText as gen_text  # type: ignore
import generateTTS as gen_tts  # type: ignore
import latencyLogger as latency_logger  # type: ignore
from generateText import generate_text_from_image_path  # type: ignore
from generateTTS import load_voice, tts_from_text  # type: ignore
from latencyLogger import log_latency  # type: ignore
from translateText import translate_text_to_indonesian, persist_translated_text  # type: ignore

# Override folder output khusus batch testing (agar terpisah dari pipeline utama)
TEST_OUTPUT_DIR = TEST_ROOT / "outputs-test"
TEST_OUTPUT_DIR_EN = TEST_ROOT / "outputs-EN-test"
TEST_AUDIO_DIR = TEST_ROOT / "audios-test"
TEST_LATENCY_DIR = TEST_ROOT / "outputs-time-test"

for d in (TEST_OUTPUT_DIR, TEST_OUTPUT_DIR_EN, TEST_AUDIO_DIR, TEST_LATENCY_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Terapkan konfigurasi path ke modul terkait
gen_text.OUTPUT_DIR = str(TEST_OUTPUT_DIR)
gen_text.OUTPUT_DIR_EN = str(TEST_OUTPUT_DIR_EN)

gen_tts.AUDIO_FOLDER = str(TEST_AUDIO_DIR)

latency_logger.LATENCY_DIR = str(TEST_LATENCY_DIR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Uji pipeline deskripsi visual menggunakan gambar lokal."
    )
    parser.add_argument(
        "--data-dir",
        default="testing-data",
        help="Folder berisi gambar uji (default: testing-data).",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="Lewati TTS (default: TTS aktif dan simpan .wav, tanpa playback).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Batas jumlah gambar yang diproses (opsional).",
    )
    return parser.parse_args()


def list_images(folder: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    files = [p for p in folder.iterdir() if p.suffix.lower() in exts and p.is_file()]
    return sorted(files, key=lambda p: p.name)


class BatchTester:
    def __init__(self, with_tts: bool):
        self.with_tts = with_tts
        self.voice = None

    def process_image(self, image_path: Path) -> dict:
        print(f"[BATCH] Memproses {image_path.name} ...")
        start_time = datetime.now()

        # 1) Vision → teks (EN)
        text, txt_path, timings = generate_text_from_image_path(
            str(image_path), output_name=image_path.stem, return_timings=True
        )
        if not text:
            return {
                "image": image_path.name,
                "status": "fail",
                "error": "vision_or_llm_failed",
                "txt_path": txt_path or "",
                "translated": False,
                "spoken_text": "",
                "wav_path": "",
            }

        # 2) Translate ke Indonesia (fallback ke teks asli jika gagal)
        translation_start = datetime.now()
        spoken_text, translated = translate_text_to_indonesian(text)
        translation_end = datetime.now()
        translation_duration = (translation_end - translation_start).total_seconds()
        if translated:
            persist_translated_text(txt_path, spoken_text)

        # 3) Opsional: TTS
        wav_path = ""
        if self.with_tts:
            if self.voice is None:
                self.voice = load_voice()
            tts_start = datetime.now()
            # Hanya simpan file .wav, tanpa playback
            wav_path = tts_from_text(spoken_text, voice=self.voice, audio_folder=str(TEST_AUDIO_DIR)) or ""
            tts_end = datetime.now()
            tts_duration = (tts_end - tts_start).total_seconds()
        else:
            tts_duration = None

        # Catat latensi untuk setiap gambar (menggunakan waktu start -> akhir proses)
        speech_start_time = tts_end if self.with_tts else translation_end
        stage_durations = {
            "capture": None,  # tidak ada capture kamera pada batch testing
            "vision_generate": timings.get("vision_seconds") if timings else None,
            "translation": translation_duration,
            "tts": tts_duration,
        }
        log_latency(
            start_time,
            speech_start_time,
            context=wav_path or (txt_path or ""),
            stage_durations=stage_durations,
        )

        return {
            "image": image_path.name,
            "status": "ok",
            "error": "",
            "txt_path": txt_path or "",
            "translated": translated,
            "spoken_text": spoken_text,
            "wav_path": wav_path,
        }


def write_report(rows: List[dict], output_dir: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"batch_results_{ts}.csv"

    fieldnames = [
        "image",
        "status",
        "error",
        "txt_path",
        "translated",
        "spoken_text",
        "wav_path",
    ]

    with report_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return report_path


def main():
    args = parse_args()

    data_dir = (PROJECT_ROOT / args.data_dir).resolve()
    if not data_dir.exists():
        print(f"[ERROR] Folder data tidak ditemukan: {data_dir}")
        sys.exit(1)

    images = list_images(data_dir)
    if not images:
        print(f"[ERROR] Tidak ada file gambar di {data_dir}")
        sys.exit(1)

    if args.limit is not None:
        images = images[: max(args.limit, 0)]

    tester = BatchTester(with_tts=not args.no_tts)
    results = []

    for idx, img in enumerate(images, 1):
        print(f"[INFO] ({idx}/{len(images)}) {img.name}")
        try:
            result = tester.process_image(img)
        except Exception as exc:  # tangkap error tak terduga agar batch tetap jalan
            result = {
                "image": img.name,
                "status": "error",
                "error": str(exc),
                "txt_path": "",
                "translated": False,
                "spoken_text": "",
                "wav_path": "",
            }
        results.append(result)

    report_path = write_report(results, PROJECT_ROOT / "outputs")
    success = sum(1 for r in results if r["status"] == "ok")
    print(f"[DONE] Selesai. Berhasil: {success}/{len(results)}. Laporan: {report_path}")


if __name__ == "__main__":
    main()

