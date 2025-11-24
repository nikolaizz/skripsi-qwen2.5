import os
import subprocess

AUDIO_DIR = "audios"
DEFAULT_DEVICE = "plughw:1,0"  # sesuaikan kalau device ALSA beda


def get_latest_wav(directory=AUDIO_DIR):
    """
    Mencari file WAV terbaru berdasarkan waktu modifikasi file.
    Return: path file .wav penuh atau None.
    """
    if not os.path.isdir(directory):
        print(f"[ERROR] Folder audio tidak ditemukan: {directory}")
        return None

    wav_files = [f for f in os.listdir(directory) if f.endswith(".wav")]

    if not wav_files:
        print("[ERROR] Tidak ada file .wav di folder audios/")
        return None

    wav_files = sorted(
        wav_files,
        key=lambda x: os.path.getmtime(os.path.join(directory, x)),
        reverse=True
    )

    latest_name = wav_files[0]
    return os.path.join(directory, latest_name)


def play_wav(file_path, device=DEFAULT_DEVICE):
    """
    Putar file WAV menggunakan aplay ke device ALSA yang diberikan.
    """
    if not file_path or not os.path.exists(file_path):
        print("[ERROR] File audio tidak ditemukan, batal play.")
        return

    print(f"[INFO] Memutar: {file_path}")
    try:
        subprocess.run(["aplay", "-D", device, file_path], check=False)
    except Exception as e:
        print(f"[ERROR] Gagal memutar audio: {e}")


def main():
    """
    Mode debug mandiri:
    - Cari .wav terbaru di audios/
    - Putar menggunakan aplay
    """
    latest = get_latest_wav(AUDIO_DIR)
    if latest:
        play_wav(latest)


if __name__ == "__main__":
    main()
