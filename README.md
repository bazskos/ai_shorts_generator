# 🎬 AI Shorts Generator

A fully automated Python application that generates ready-to-upload, vertical (9:16) videos for TikTok, YouTube Shorts, and Instagram Reels. 

The script generates historical facts, synthesizes natural-sounding voiceovers, automatically downloads context-aware background footage, and edits everything together with highly visible, perfectly synced CapCut-style subtitles.

## 🚀 Features
* **AI Content:** Uses Llama 3.3 (Groq API) with strict JSON formatting to write engaging scripts and metadata.
* **Text-to-Speech:** Uses `edge-tts` for dynamic, human-like voiceovers.
* **Automated Footage Sourcing:** Connects to the `Pexels API` to download HD background videos matching AI-generated visual keywords.
* **Smart Editing:** Uses `MoviePy` to crop, scale, and concatenate videos with smooth crossfades, ensuring perfect 1080x1920 mobile formatting.
* **Dynamic Subtitles:** Generates perfectly synced, aesthetic 3-word chunked subtitles with a modern white text on black background for maximum engagement.

## 🛠️ Tech Stack
Python 3.x, Groq API, Pexels API, MoviePy, Edge-TTS

## ⚙️ How to Use
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file in the root directory and add your `GROQ_API_KEY` and `PEXELS_API_KEY`.
4. Run `python makeavideo.py` and let the magic happen.