<div align="center">
  <img src="assets/hero.png" alt="Lemihandle Hero Image" width="100%">

  # ✨ Lemihandle: Spatial Intent Engine

  **An AI-powered OS overlay that lets you control your computer using spatial gestures and voice.**

  [![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52.svg?logo=qt)](https://riverbankcomputing.com/software/pyqt/)
  [![MediaPipe](https://img.shields.io/badge/MediaPipe-Vision-FF6F00.svg?logo=google)](https://mediapipe.dev/)
  [![Gemini](https://img.shields.io/badge/AI-Gemini%202.5%20Flash%20Lite-1A73E8.svg?logo=google)](https://ai.google.dev/)
</div>

---

## 🚀 Overview

**Lemihandle** is an invisible, intelligent layer that sits on top of your Windows desktop. It watches your hands and face through your webcam, listens to your voice, and uses Google's multimodal **Gemini 2.5 Flash Lite** AI to instantly execute your intentions based on what is currently on your screen.

No clicking. No typing. Just point, speak, and command.

---

## 🎯 Features

- 🖖 **Gesture Tracking:** Uses Google MediaPipe to track intricate hand and face gestures in real-time.
  - **Pinch:** Instantly triggers an AI analysis of your current screen.
  - **Open Palm:** Acts as a push-to-talk button for your microphone.
  - **Closed Fist:** Submits your audio command (or dismisses the current UI).
  - **Head Nod:** A 2-step confirmation to execute an action.
- 🗣️ **Local Voice Transcription:** Captures audio through `sounddevice` and transcribes it instantly using a lightweight background thread.
- 🧠 **Multimodal AI Brain:** A `FastAPI` backend orchestrates communication with the Gemini API, sending both the screen context (screenshot) and your audio transcript to figure out what you want.
- 🛠️ **Agentic Tools:** The AI doesn't just answer questions—it executes tools. It can write files, perform system actions, and issue UI directives.
- 🖼️ **Glassmorphic UI:** A beautiful, transparent PyQt5 overlay that renders AI responses as smooth, floating glass cards on your desktop.

---

## 🏗️ Architecture

The project is split into two perfectly decoupled microservices to ensure the UI remains buttery-smooth while heavy AI inference happens in the background.

```text
Lemihandle/
├── frontend/                  # The PyQt5 + MediaPipe Overlay
│   ├── main.py                # Core application entry point
│   ├── overlay.py             # Transparent floating GUI
│   ├── gesture_engine.py      # Camera & hand/face tracking thread
│   ├── audio_engine.py        # Push-to-talk mic & whisper/speech-recognition
│   ├── network.py             # Asynchronous JSON payload transmitter
│   └── requirements.txt       # Frontend dependencies (Numpy 1.26.4)
│
├── backend/                   # The FastAPI AI Brain
│   ├── main.py                # FastAPI server & route handlers
│   ├── ai_agent.py            # Gemini 2.5 Flash Lite interaction & tool routing
│   ├── config.py              # API key rotation & env management
│   ├── tools.py               # Executable system tools (e.g., save file, clipboard)
│   ├── interactive_test.py    # Terminal-based testing client
│   └── requirements.txt       # Backend dependencies
└── assets/                    # Media and README assets
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10+
- A working webcam
- A working microphone
- A Google Gemini API Key

### 1. Backend Setup

Open a terminal and navigate to the `backend` directory:

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEYS=your_api_key_1,your_api_key_2
LEMIHANDLE_MODEL=gemini-2.5-flash-lite
```

Start the backend server:
```bash
python -m uvicorn main:app --port 8000
```

### 2. Frontend Setup

Open a **new** terminal and navigate to the `frontend` directory:

```bash
cd frontend
pip install -r requirements.txt
```
> **Note:** The frontend requires `numpy==1.26.4` to remain compatible with pre-compiled
> MediaPipe/TensorFlow binaries. `sounddevice` is also required for mic capture — both are
> already included in `requirements.txt`.

Start the overlay:
```bash
python main.py
```

---

## 🎮 How to Use

1. **Start both services.** You will see a small camera feed pop up in the top right corner of your screen.
2. **Push to Talk:** Hold up an **Open Palm** to start the microphone. Speak your command (e.g., *"Summarize this article for me"*).
3. **Submit Audio:** Close your hand into a **Fist**. Your voice will be transcribed.
4. **Trigger:** **Pinch** your index and thumb together. The UI will ask you to confirm.
5. **Confirm:** **Nod your head twice**. The engine will capture your screen, bundle it with your voice command, and send it to Gemini.
6. **Result:** A beautiful floating card will slide onto your screen with the AI's response or confirmation that it executed your tool!

*(To instantly dismiss any UI or cancel a recording, simply close your hand into a fist!)*

---

## 🤝 Contributing
Built with ❤️ using Python, PyQt5, MediaPipe, and Gemini. Pull requests and feature expansions (especially adding new tools to `backend/tools.py`) are highly encouraged!

## 📜 License
MIT License
