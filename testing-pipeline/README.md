# Testing Pipeline (Windows)

Pipeline ini mempermudah pengujian alur deskripsi visual pada laptop Windows
tanpa Jetson Orin Nano maupun tombol fisik.

## Prasyarat

Jalankan perintah berikut di root repo agar dependensi terpenuhi:

```
pip install opencv-python requests argostranslate piper-tts
```

Pastikan bahasa **English → Indonesian** Argos Translate sudah terpasang:

```
argos-translate --from-lang en --to-lang id download
argos-translate --from-lang en --to-lang id install
```

Model Piper `id_ID-news_tts-medium.onnx` sudah tersedia di repo (digunakan ulang
dari pipeline utama).

## Menjalankan

1. Pastikan kamera laptop dapat diakses (index 0) dan speaker internal aktif.
2. Dari root repo jalankan:

```
python testing-pipeline/run_pipeline_windows.py
```

Pipeline akan:

1. Mengambil foto dari kamera laptop.
2. Mengirimnya ke model Qwen2.5-VL melalui `generateText.py`.
3. Menerjemahkan keluaran Inggris ke Bahasa Indonesia dengan Argos.
4. Menyintesis suara via Piper.
5. Memutar hasilnya ke speaker laptop menggunakan `winsound`.

Gunakan `--loop` untuk menjalankan berulang, misalnya:

```
python testing-pipeline/run_pipeline_windows.py --loop --delay 5
```

Tekan `Ctrl+C` untuk menghentikan mode loop. Semua file capture/output/audio
tetap disimpan di direktori standar (`captures/`, `outputs/`, `audios/`) sehingga
Anda bisa meninjau hasilnya sama seperti pada Jetson.

