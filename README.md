# 🦯 Vision-to-Speech Assistive System for Visually Impaired

An edge AI system that helps visually impaired individuals understand their surroundings using camera-based scene description and text-to-speech output. Designed to run on **NVIDIA Jetson Orin Nano** devices.

## ✨ Features

- **Real-time Scene Description** — Captures images via camera and generates natural language descriptions using Qwen2.5-VL vision-language model
- **Hazard Detection** — Identifies potential dangers (obstacles, uneven surfaces, stairs, etc.) in the scene
- **Indonesian Translation** — Automatically translates descriptions from English to Indonesian using Argos Translate
- **Text-to-Speech** — Converts descriptions to spoken audio using Piper TTS with Indonesian voice
- **Hardware Button Trigger** — Simple GPIO button interface for hands-free operation
- **Latency Logging** — Tracks and records processing times for each pipeline stage

## 🏗️ Architecture

```
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│   Camera     │───▶│  Qwen2.5-VL    │───▶│ Argos Translate │
│  (Capture)   │    │  (via Ollama)  │    │   (EN → ID)     │
└──────────────┘    └────────────────┘    └────────┬────────┘
                                                   │
                                                   ▼
┌──────────────┐    ┌────────────────┐    ┌─────────────────┐
│   Speaker    │◀───│     aplay      │◀───│   Piper TTS     │
│   (Output)   │    │   (Playback)   │    │  (Indonesian)   │
└──────────────┘    └────────────────┘    └─────────────────┘
```

## 📁 Project Structure

| File | Description |
|------|-------------|
| `main.py` | Main entry point with GPIO button handling and pipeline orchestration |
| `generateText.py` | Camera capture and Qwen2.5-VL vision-language processing |
| `translateText.py` | English to Indonesian translation using Argos Translate |
| `generateTTS.py` | Text-to-speech conversion using Piper TTS |
| `playAudio.py` | Audio playback using ALSA (aplay) |
| `latencyLogger.py` | Pipeline performance logging |
| `findwebcamindex.py` | Utility to discover available camera indices |

### Directories

| Directory | Description |
|-----------|-------------|
| `captures/` | Captured images from camera |
| `outputs/` | Generated text descriptions (Indonesian) |
| `outputs-EN/` | Generated text descriptions (English) |
| `audios/` | Generated TTS audio files |
| `outputs-time/` | Latency measurement logs |

## 🛠️ Requirements

### Hardware
- NVIDIA Jetson device (Nano, Xavier, Orin, etc.)
- USB webcam or CSI camera
- Speaker/headphones
- Push button (connected to GPIO pin 37)

### Software Dependencies
- Python 3.8+
- [Ollama](https://ollama.com/) with `qwen2.5vl:3b` model
- OpenCV (`cv2`)
- [Piper TTS](https://github.com/rhasspy/piper)
- [Argos Translate](https://github.com/argosopentech/argos-translate)
- Jetson.GPIO

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd main-pipeline
   ```

2. **Install Python dependencies**
   ```bash
   pip install opencv-python requests piper-tts argostranslate
   ```

3. **Install and configure Ollama**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull the vision-language model
   ollama pull qwen2.5vl:3b
   
   # Start Ollama server
   ollama serve
   ```

4. **Install Argos Translate language pack**
   ```bash
   # Download and install English to Indonesian translation
   argos-translate --from-lang en --to-lang id download
   argos-translate --from-lang en --to-lang id install
   ```

5. **Download Piper TTS Indonesian voice model**
   - Ensure `id_ID-news_tts-medium.onnx` and `id_ID-news_tts-medium.onnx.json` are in the project root

## 🔌 Hardware Setup

Connect a momentary push button:
- One terminal → **Pin 37** (GPIO)
- Other terminal → **Pin 39** (GND)

The button uses internal pull-up, so pressing creates a falling edge trigger.

## 🚀 Usage

### Main Pipeline (Button-triggered)
```bash
python main.py
```
Press the button to trigger the pipeline. The system will:
1. Capture an image
2. Generate a scene description
3. Translate to Indonesian
4. Speak the description

### Debug/Testing Individual Modules

**Test vision module:**
```bash
python generateText.py
# Enter 'test' to capture and process, 'clean' to clear files
```

**Test TTS module:**
```bash
python generateTTS.py
```

**Test audio playback:**
```bash
python playAudio.py
```

**Find camera index:**
```bash
python findwebcamindex.py
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARGOS_SRC_LANG` | `en` | Source language for translation |
| `ARGOS_TGT_LANG` | `id` | Target language for translation |

### Code Configuration

In `main.py`:
- `BUTTON_PIN = 37` — GPIO pin for button (BOARD mode)
- `DEBOUNCE_SEC = 0.15` — Button debounce time

In `generateText.py`:
- `MODEL_NAME = "qwen2.5vl:3b"` — Ollama model name
- `OLLAMA_URL = "http://127.0.0.1:11434/api/chat"` — Ollama API endpoint

## 📊 Performance Logging

Latency data is saved to `outputs-time/` with timestamps for each pipeline run:
- `capture_seconds` — Image capture time
- `vision_generate` — VL model inference time
- `translation` — Translation time
- `tts` — TTS generation time
- `latency_seconds` — Total end-to-end latency

## 📄 License

This project is part of a thesis research project (Skripsi).

## 🙏 Acknowledgments

- [Qwen2.5-VL](https://github.com/QwenLM/Qwen2.5-VL) — Vision-language model
- [Ollama](https://ollama.com/) — Local LLM serving
- [Piper TTS](https://github.com/rhasspy/piper) — Fast neural TTS
- [Argos Translate](https://github.com/argosopentech/argos-translate) — Offline translation
