import os
from datetime import datetime

LATENCY_DIR = os.path.join(os.getcwd(), "outputs-time")
os.makedirs(LATENCY_DIR, exist_ok=True)


def log_latency(
    start_time: datetime,
    speech_start_time: datetime,
    context: str = "",
    stage_durations=None,
) -> str:
    """
    Simpan durasi dari awal capture hingga audio mulai diputar, serta
    (opsional) durasi per tahap pipeline.
    Return path file laporan.
    """
    latency = speech_start_time - start_time
    timestamp = speech_start_time.strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(LATENCY_DIR, f"latency_{timestamp}.txt")

    rows = [
        f"start_time={start_time.isoformat()}",
        f"speech_start_time={speech_start_time.isoformat()}",
        f"latency_seconds={latency.total_seconds():.3f}",
    ]

    if stage_durations:
        for key, value in stage_durations.items():
            if value is None:
                continue
            rows.append(f"{key}_seconds={value:.3f}")

    if context:
        rows.append(f"context={context}")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(rows))
        print(f"[PIPELINE] Data latensi disimpan: {file_path}")
    except Exception as exc:
        print(f"[WARN] Gagal menyimpan data latensi: {exc}")

    return file_path

