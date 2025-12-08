import time
from datetime import datetime

import Jetson.GPIO as GPIO

from generateText import generate_text_from_camera
from generateTTS import load_voice, tts_from_text
from playAudio import play_wav
from translateText import translate_text_to_indonesian, persist_translated_text
from latencyLogger import log_latency

# === KONFIGURASI TOMBOL ===
BUTTON_PIN = 37        # pin fisik 37 (BOARD mode)
DEBOUNCE_SEC = 0.15    # 150 ms


# === STATE GLOBAL ===
last_press_time = 0.0
trigger_requested = False
is_processing = False
voice = None  # cache model Piper supaya tidak load berulang kali


def run_full_pipeline():
    """
    Satu rangkaian penuh:
    1. capture + Qwen2.5-VL:3b → teks (EN)
    2. Argos Translate → teks ID
    3. Piper TTS → wav
    4. play ke speaker
    """
    global voice

    print("\n================= PIPELINE DIMULAI =================")
    start_time = datetime.now()

    # 1. Ambil teks dari modul vision-language
    text, txt_path, timings = generate_text_from_camera(return_timings=True)
    if not text:
        print("[PIPELINE] Gagal di tahap vision/LLM. Stop.")
        print("================= PIPELINE GAGAL =================\n")
        return

    # 2. Terjemahkan ke Bahasa Indonesia (fallback ke teks asli jika gagal)
    translation_start = datetime.now()
    tts_text, translated = translate_text_to_indonesian(text)
    translation_end = datetime.now()
    translation_duration = (translation_end - translation_start).total_seconds()
    if translated:
        print("[PIPELINE] Teks berhasil diterjemahkan ke Bahasa Indonesia.")
        persist_translated_text(txt_path, tts_text)
    else:
        print("[PIPELINE] Memakai teks asli (pasangan en->id Argos belum siap).")

    # 3. Pastikan model Piper sudah diload
    if voice is None:
        voice = load_voice()

    # 4. TTS ke .wav
    tts_start = datetime.now()
    wav_path = tts_from_text(tts_text, voice=voice)
    tts_end = datetime.now()
    tts_duration = (tts_end - tts_start).total_seconds()
    if not wav_path:
        print("[PIPELINE] Gagal di tahap TTS. Stop.")
        print("================= PIPELINE GAGAL =================\n")
        return

    # 5. Catat latensi dan play audio
    speech_start_time = tts_end
    stage_durations = {
        "capture": timings.get("capture_seconds"),
        "vision_generate": timings.get("vision_seconds"),
        "translation": translation_duration,
        "tts": tts_duration,
    }
    log_latency(start_time, speech_start_time, context=wav_path or "", stage_durations=stage_durations)
    play_wav(wav_path)

    print("================= PIPELINE SELESAI =================\n")


def on_button_pressed():
    """
    Dipanggil dari callback setelah debounce.
    Hanya meng-set flag untuk dieksekusi di main loop.
    """
    global trigger_requested, is_processing

    if is_processing:
        print("[INFO] Tombol ditekan, tapi pipeline masih berjalan. Abaikan.")
        return

    if not trigger_requested:
        trigger_requested = True
        print("[EVENT] Tombol ditekan! Pipeline akan dijalankan...")


def button_callback(channel):
    """
    Callback level bawah (dipanggil langsung oleh Jetson.GPIO),
    meng-handle debounce berdasarkan waktu.
    """
    global last_press_time
    now = time.time()

    if now - last_press_time < DEBOUNCE_SEC:
        return

    last_press_time = now
    on_button_pressed()


def main():
    global trigger_requested, is_processing

    # --- Setup GPIO untuk tombol ---
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(
        BUTTON_PIN,
        GPIO.FALLING,
        callback=button_callback,
        bouncetime=1  # kecil, debounce utama di logika waktu
    )

    print("=== Pipeline Tombol Otomatis ===")
    print(f"Tombol pada pin fisik {BUTTON_PIN} (BOARD mode).")
    print("Satu kaki tombol -> pin 37, satu kaki -> GND (misal pin 39).")
    print("Tekan tombol untuk menjalankan pipeline.")
    print("Tekan Ctrl+C untuk keluar.\n")

    try:
        while True:
            # cek apakah ada request dari tombol
            if trigger_requested and not is_processing:
                trigger_requested = False
                is_processing = True
                try:
                    run_full_pipeline()
                finally:
                    is_processing = False

            time.sleep(0.1)  # kecil saja supaya CPU nggak 100%

    except KeyboardInterrupt:
        print("\n[MAIN] Dihentikan oleh pengguna. Keluar...")
    finally:
        GPIO.cleanup()


if __name__ == "__main__":
    main()
