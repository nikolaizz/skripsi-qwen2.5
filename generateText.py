import os
import cv2
import base64
import requests
from datetime import datetime

# === KONFIGURASI OLLAMA ===
MODEL_NAME = "qwen2.5vl:3b"
OLLAMA_URL = "http://127.0.0.1:11434/api/chat"  # endpoint chat Ollama

# === FOLDER ===
CAPTURE_DIR = os.path.join(os.getcwd(), "captures")
OUTPUT_DIR = os.path.join(os.getcwd(), "outputs")

os.makedirs(CAPTURE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


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


def run_ollama_with_image(image_path):
    """
    Kirim gambar ke model Qwen2.5-VL:4b.
    Hasil teks disimpan ke OUTPUT_DIR sebagai .txt.
    Return: path file .txt atau None.
    """
    if not os.path.exists(image_path):
        print(f"[ERROR] File gambar tidak ada: {image_path}")
        return None

    # Encode ke base64 (format multimodal Ollama)
    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"[ERROR] Gagal membaca/encode gambar: {e}")
        return None

    prompt = "You are a visually impaired assistant. Describe the image briefly without being wordy. Mention if there is any danger for visually impaired people. Use simple, short sentences."
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "user", "images": [img_b64]},
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
    output_path = os.path.join(OUTPUT_DIR, f"output_{ts}.txt")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[INFO] Hasil interpretasi disimpan: {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] Gagal menulis file output: {e}")
        return None

def generate_text_from_camera():
    """
    Fungsi utama yang akan dipanggil modul lain:
    1. Capture gambar
    2. Kirim ke Ollama
    3. Baca teks dari file .txt

    Return: (text, txt_path) atau (None, None) jika gagal.
    """
    img_path = capture_image()
    if not img_path:
        return None, None

    txt_path = run_ollama_with_image(img_path)
    if not txt_path:
        return None, None

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            text = f.read().strip()
    except Exception as e:
        print(f"[ERROR] Gagal membaca file teks: {e}")
        return None, txt_path

    print("[INFO] Teks hasil interpretasi berhasil dibaca.")
    return text, txt_path


def clean_files():
    """
    Menghapus semua file dalam captures/ dan outputs/
    """
    removed = 0
    for folder in (CAPTURE_DIR, OUTPUT_DIR):
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
