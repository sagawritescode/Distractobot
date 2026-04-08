# DistractoBot & Dashboard Architecture

This document illustrates the flow of data from capturing a spoken thought to managing it as an actionable task on the dashboard.

## 🏗 System Overview

The system is split into two primary components:
1. **DistractoBot**: A native macOS menu bar app that listens for hotkeys and processes audio locally.
2. **Dashboard**: A Flask-based web interface for reviewing, filtering, and organizing captured distractions into lists.

## 🔄 Data Flow Diagram

```mermaid
graph TD
    subgraph "DistractoBot (Menubar App)"
        A[Hotkey Pressed / Click] --> B["AudioManager (Recording)"]
        B -->|Stop| C["Transcriber (MLX Whisper)"]
        C -->|Raw Text| D["LLMProcessor (Ollama)"]
        D -->|Structured JSON| E["Database (SQLite)"]
        E --> F[rumps Notification]
    end

    subgraph "Local Storage"
        E -.-> G[("distractions.db")]
    end

    subgraph "Dashboard (Flask Web App)"
        G -.-> H["Dashboard Backend (Flask)"]
        H --> I["Web UI (Browse Distractions)"]
        I -->|Status Update| J["Clear / Reject"]
        I -->|Assign To List| K["Actionables (Tasks/Work/etc.)"]
        K -->|Update DB| G
    end

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#bbf,stroke:#333,stroke-width:2px
    style G fill:#dfd,stroke:#333,stroke-width:2px
    style I fill:#fff,stroke:#333,stroke-width:2px
```

## 🧩 Component Breakdown

### 1. DistractoBot Components
- **`audio_manager.py`**: Handles microphone access, file paths, and threading for clean audio capture.
- **`transcriber.py`**: Uses local Apple Silicon optimized Whisper models to convert audio to text.
- **`llm_processor.py`**: Sends the transcribed text to Ollama (likely Gemma or Llama models) to extract structured data (Intent, Source, Summary).
- **`database.py`**: Simple SQLite wrapper for the `thoughts` and `actionables` tables.

### 2. Dashboard Features
- **Distraction Inbox**: Shows all "open" thoughts with their AI-generated summaries.
- **Filtering**: Allows searching by source or summary and filtering by date.
- **Actionable System**: 
  - Allows assigning a thought to a specific **List Type** (e.g., Home, Work, Groceries).
  - Supports **Subtypes** for extra granularity.
  - Automatically marks the original thought as "cleared" once assigned.

## 🛠 Tech Stack
- **Backend/Logic**: Python
- **UI (App)**: `rumps` (macOS native menu bar)
- **UI (Dashboard)**: Flask, HTML5, Vanilla CSS, JavaScript
- **AI Engine**: MLX-Whisper (Transcription), Ollama (Categorization)
- **Persistence**: SQLite3
