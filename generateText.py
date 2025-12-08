import os
import cv2
import base64
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional

# === KONFIGURASI OLLAMA ===
MODEL_NAME = "qwen2.5vl:3b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"  # endpoint chat Ollama

# === FOLDER ===
CAPTURE_DIR = os.path.join(os.getcwd(), "captures")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")
OUTPUT_DIR_EN = os.path.join(os.getcwd(), "outputs-EN")

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR_EN, exist_ok=True)


def capture_image():
    """
    Ambil satu frame dari kamera index 0 dan simpan ke CAPTURE_DIR.
    Return: path gambar atau None jika gagal.
    """
    print("[STEP] Menangkap gambar dari kamera (index 0)...")
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[ERROR] Kamera (index 0) tidak ditemukan atau tidak bisa dibuka.")
        return None

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        print("[ERROR] Tidak dapat menangkap gambar dari kamera.")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_path = os.path.join(CAPTURE_DIR, f"capture_{ts}.png")
    try:
        cv2.imwrite(image_path, frame)
        print(f"[INFO] Gambar disimpan: {image_path}")
        return image_path
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan gambar: {e}")
        return None


def run_ollama_with_image(image_path, output_name=None, resize: bool = False, max_side: int = 640):
    """
    Kirim gambar ke model Qwen2.5-VL:3b.
    Hasil teks disimpan ke OUTPUT_DIR sebagai .txt.
    Return: path file .txt atau None.
    Parameter:
        resize   : jika True, lakukan resize agar sisi terpanjang <= max_side.
        max_side : batas sisi terpanjang saat resize aktif.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] File gambar tidak ada: {image_path}")
        return None

    # Encode ke base64 (format multimodal Ollama) dengan opsi resize
    try:
        img = cv2.imread(image_path)
        if img is None:
            print(f"[ERROR] Cannot read image: {image_path}")
            return None
        if resize:
            h, w = img.shape[:2]
            scale = min(max_side / max(h, w), 1.0)
            if scale < 1.0:
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            print(f"[ERROR] Failed to encode image: {image_path}")
            return None
        img_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR] Gagal membaca/encode gambar: {e}")
        return None

    prompt = "You are a visually impaired assistant. Describe the image briefly without being wordy. Mention if there is any danger for visually impaired people. Use simple, short sentences."
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "user", "images": [img_b64]}
        ],
        "stream": False  # supaya respons langsung sekali, bukan streaming
    }

    print("[STEP] Mengirim gambar ke Ollama (Qwen2.5-VL)...")
    try:
        resp = requests.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Gagal memanggil Ollama. "
              f"Pastikan `ollama serve` aktif dan model '{MODEL_NAME}' tersedia. Detail: {e}")
        return None

    try:
        data = resp.json()
    except Exception as e:
        print(f"[ERROR] Gagal parse JSON dari Ollama: {e}\nRespons mentah: {resp.text}")
        return None

    # Ambil konten jawaban dari field message.content
    content = data.get("message", {}).get("content", "")
    if not content:
        print(f"[ERROR] Konten kosong atau struktur respons tak terduga.\nRespons: {data}")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_name:
        safe_name = Path(output_name).stem or "output"
        candidate = f"{safe_name}.txt"
        output_path = os.path.join(OUTPUT_DIR, candidate)
        if os.path.exists(output_path):
            # hindari overwrite, tambahkan timestamp jika sudah ada
            output_path = os.path.join(OUTPUT_DIR, f"{safe_name}_{ts}.txt")
    else:
        output_path = os.path.join(OUTPUT_DIR, f"output_{ts}.txt")

    # Selaraskan nama file EN agar mudah dicocokkan
    output_path_en = os.path.join(OUTPUT_DIR_EN, Path(output_path).name)

    try:
        with open(output_path_en, "w", encoding="utf-8") as f_en:
            f_en.write(content)
        print(f"[INFO] Hasil interpretasi (EN) disimpan: {output_path_en}")
    except Exception as e:
        print(f"[ERROR] Gagal menulis file output EN: {e}")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[INFO] Hasil interpretasi disimpan: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Gagal menulis file output: {e}")
        return None

def generate_text_from_camera(return_timings: bool = False):
    """
    Fungsi utama yang akan dipanggil modul lain:
    1. Capture gambar
    2. Kirim ke Ollama
    3. Baca teks dari file .txt

    Return default: (text, txt_path) atau (None, None) jika gagal.
    Bila return_timings=True, return (text, txt_path, timings) di mana
    timings memuat durasi per langkah (detik).
    """
    capture_start = datetime.now()
    img_path = capture_image()
    capture_end = datetime.now()
    timings = {
        "capture_seconds": (capture_end - capture_start).total_seconds(),
    }

    if not img_path:
        return (None, None, timings) if return_timings else (None, None)

    vision_start = datetime.now()
    txt_path = run_ollama_with_image(img_path, resize=False)
    vision_end = datetime.now()
    timings["vision_seconds"] = (vision_end - vision_start).total_seconds()

    if not txt_path:
        return (None, None, timings) if return_timings else (None, None)

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as e:
        print(f"[ERROR] Gagal membaca file teks: {e}")
        return (None, txt_path, timings) if return_timings else (None, txt_path)

    print("[INFO] Teks hasil interpretasi berhasil dibaca.")
    if return_timings:
        return text, txt_path, timings
    return text, txt_path


def generate_text_from_image_path(
    image_path: str,
    output_name: Optional[str] = None,
    return_timings: bool = False,
    resize: bool = True,
    max_side: int = 640,
):
    """
    Jalankan model vision menggunakan file gambar yang sudah ada.

    Parameter:
        image_path    : path file gambar yang ingin diproses.
        output_name   : nama file output (tanpa folder). Jika None, gunakan timestamp.
        return_timings: bila True, kembalikan juga durasi proses vision.
        resize        : True untuk resize sisi terpanjang <= max_side (dipakai batch).
        max_side      : batas sisi terpanjang saat resize aktif.

    Return:
        - default: (text, txt_path) atau (None, None) bila gagal.
        - jika return_timings=True: (text, txt_path, timings)
          di mana timings["vision_seconds"] berisi durasi step visi.
    """
    vision_start = datetime.now()
    txt_path = run_ollama_with_image(
        image_path, output_name=output_name, resize=resize, max_side=max_side
    )
    vision_end = datetime.now()
    timings = {"vision_seconds": (vision_end - vision_start).total_seconds()}

    if not txt_path:
        return (None, None, timings) if return_timings else (None, None)

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as e:
        print(f"[ERROR] Gagal membaca file teks untuk {image_path}: {e}")
        return (None, txt_path, timings) if return_timings else (None, txt_path)

    print(f"[INFO] Teks berhasil dibaca untuk {image_path}.")
    if return_timings:
        return text, txt_path, timings
    return text, txt_path


def clean_files():
    """
    Menghapus semua file dalam captures/, outputs/, dan outputs-EN/
    """
    removed = 0
    for folder in (CAPTURE_DIR, OUTPUT_DIR, OUTPUT_DIR_EN):
        for name in os.listdir(folder):
            fpath = os.path.join(folder, name)
            try:
                os.remove(fpath)
                removed += 1
            except Exception:
                pass
    print(f"[INFO] Bersih-bersih selesai. File terhapus: {removed}")


def main():
    """
    Mode debug mandiri:
    - 'test'  : capture + kirim ke Qwen2.5-VL
    - 'clean' : hapus semua file di captures/ dan outputs/
    - 'q'     : keluar
    """
    print("Perintah: test | clean | q (quit)")
    try:
        while True:
            cmd = input("Masukkan perintah: ").strip().lower()
            if cmd == "test":
                text, txt_path = generate_text_from_camera()
                if text:
                    print("\n=== HASIL TEKS ===")
                    print(text)
                    print("==================\n")
            elif cmd == "clean":
                clean_files()
            elif cmd in ("q", "quit", "exit"):
                print("Keluar.")
                break
            elif cmd == "":
                continue
            else:
                print("Perintah tidak dikenali. Gunakan: test | clean | q")
    except KeyboardInterrupt:
        print("\n[DONE] Dihentikan oleh pengguna.")


if __name__ == "__main__":
    main()
