import os
import requests
from dotenv import load_dotenv
from groq import Groq
import asyncio
import edge_tts
from moviepy import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, CompositeAudioClip, concatenate_videoclips
import time
import json
import random

# --- DIRECTORY SETUP ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "history_log.txt")
INFO_FILE = os.path.join(SCRIPT_DIR, "upload_info.txt")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "today_histroy.mp4")
AUDIO_FILE = os.path.join(SCRIPT_DIR, "voice.mp3")
MUSIC_FILE = os.path.join(SCRIPT_DIR, "music.mp3")

# --- 1. CONFIGURATION (GITHUB SAFE) ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

TEST_MODE = False 

TARGET_W = 1080
TARGET_H = 1920

# --- (UX) ---
print("\n" + "="*40)
print("🎬 AI SHORTS GENERATOR STARTING...")
print("="*40)
answer = input("Would you like to open the files after finishing with it? (y/n): ").strip().lower()
auto_open = answer.startswith('y')
print("-" * 40 + "\n")

# --- 2. GENERATING CONTENT ---
story_text = ""
keywords = []
upload_caption = ""

if TEST_MODE:
    print("⚠️ TEST MODE: Active")
    story_text = "Did you know that in ancient Rome, they used a special kind of concrete that could last for thousands of years even underwater? The secret was volcanic ash."
    keywords = ["ancient rome", "volcano", "ruins"]
    upload_caption = "ROMAN CONCRETE | #history"
else:
    print("🚀 Fetching from Groq...")
    client = Groq(api_key=GROQ_API_KEY)
    history = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            history = "".join(lines[-20:]) # Keep only the last 20 topics to prevent long prompts
    
    prompt = f"""
    Task: Write a highly engaging, viral-style script about a mind-blowing, TRUE historical event. It should be 130-150 words (perfect for a 60-second TikTok/Shorts video).
    
    Guidelines for the story:
    - Start with a strong, curiosity-inducing hook (e.g., "History books forgot to mention...", "This is the craziest true story about...").
    - Focus on bizarre, shocking, or deeply fascinating real historical events (not well-known clichés).
    - Use conversational, fast-paced storytelling.
    - End with a thought-provoking conclusion or plot twist.
    
    Avoid these previous topics: {history}
    
    CRITICAL RULE FOR KEYWORDS: Do NOT use proper nouns or specific names (like 'Nabataean Kingdom' or 'Julius Caesar'). 
    Only use generic, highly visual stock-footage search terms like 'sand dunes', 'old stone ruins', 'ocean waves', 'dark cave'.
    Caption: Write an engaging TikTok caption to encourage comments, plus trending hashtags. Use emojis.
    Provide ONLY JSON:
    {{
        "story": "Full detailed story with normal punctuation.",
        "keywords": ["visual term 1", "visual term 2", "visual term 3", "visual term 4"],
        "caption": "Engaging TikTok caption | #history #shorts"
    }}
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        data = json.loads(completion.choices[0].message.content)
        story_text = data["story"].strip()
        keywords = data["keywords"]
        upload_caption = data["caption"].strip()
    except Exception as e: exit(f"❌ Groq Error: {e}")

# --- 3. VOICE & TIMING ---
print("1. Generating Voice...")
GOOD_VOICES = ["en-US-ChristopherNeural", "en-US-SteffanNeural", "en-GB-RyanNeural", "en-US-AriaNeural"]
VOICE = random.choice(GOOD_VOICES)
print(f"-> Selected voice: {VOICE}")
word_timings = []

async def generate_audio():
    communicate = edge_tts.Communicate(story_text, VOICE, rate="+15%") # Speed up by 15%
    await communicate.save(AUDIO_FILE)

asyncio.run(generate_audio())

print("-> Voice generated! Extracting exact word timings using Groq Whisper...")
try:
    with open(AUDIO_FILE, "rb") as file:
        transcription = client.audio.transcriptions.create(
            file=("voice.mp3", file.read()),
            model="whisper-large-v3",
            response_format="verbose_json",
            timestamp_granularities=["word"],
            language="en"
        )

    for w in transcription.words:
        word_text = w["word"] if isinstance(w, dict) else w.word
        start_time = w["start"] if isinstance(w, dict) else w.start
        end_time = w["end"] if isinstance(w, dict) else w.end
        
        clean_text = word_text.replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip().upper()
        if clean_text:
            word_timings.append({
                "text": clean_text,
                "start": start_time,
                "end": end_time
            })
    print(f"-> Captured {len(word_timings)} words for PERFECT subtitles via Whisper!")
    
except Exception as e:
    print(f"⚠️ Whisper fallback failed: {e}")
    temp_audio = AudioFileClip(AUDIO_FILE)
    words = story_text.split()
    step = temp_audio.duration / len(words)
    for i, w in enumerate(words):
        word_timings.append({"text": w.upper(), "start": i * step, "end": (i + 1) * step})
    temp_audio.close()

# --- GROUPING WORDS FOR SUBTITLES ---
grouped_timings = []
chunk_size = 3 # Words per subtitle chunk
for i in range(0, len(word_timings), chunk_size):
    chunk = word_timings[i:i + chunk_size]
    grouped_timings.append({
        "text": " " + " ".join([w["text"] for w in chunk]) + " ", # Add spaces for visual padding
        "start": chunk[0]["start"],
        "end": chunk[-1]["end"]
    })

# --- 4. VIDEO DOWNLOAD ---
print("2. Downloading background clips...")
narration = AudioFileClip(AUDIO_FILE)
clips_needed = int(narration.duration // 8) + 2
headers = {"Authorization": PEXELS_API_KEY}
downloaded_files = []
search_terms = (keywords * 5)[:clips_needed]

for i, term in enumerate(search_terms):
    url = f"https://api.pexels.com/videos/search?query={term.replace(' ', '%20')}&orientation=portrait&size=medium&per_page=1&page={random.randint(1, 10)}"
    try:
        res = requests.get(url, headers=headers).json()
        if "videos" in res and len(res["videos"]) > 0:
            v_url = res["videos"][0]["video_files"][0]["link"]
            fname = os.path.join(SCRIPT_DIR, f"temp_{i}.mp4")
            with open(fname, "wb") as f: f.write(requests.get(v_url).content)
            downloaded_files.append(fname)
            print(f"  [{i+1}/{clips_needed}] Downloaded: {term}")
    except: continue

# --- 5. EDITING ---
print("3. Editing video...")
final_clips = []
for i, f in enumerate(downloaded_files):
    clip = VideoFileClip(f)
    scale = max(TARGET_W / clip.w, TARGET_H / clip.h)
    c_res = clip.resized(scale)
    c_final = c_res.cropped(width=TARGET_W, height=TARGET_H, x_center=c_res.w/2, y_center=c_res.h/2)
    
    # Crossfade between clips
    if i > 0:
        try:
            # MoviePy 1.x
            c_final = c_final.crossfadein(0.5)
        except AttributeError:
            # MoviePy 2.x
            import moviepy.video.fx as vfx
            c_final = c_final.with_effects([vfx.CrossFadeIn(0.5)])
            
    final_clips.append(c_final)

video_bg = concatenate_videoclips(final_clips, padding=-0.5, method="compose")
# Loop background if shorter than audio
if video_bg.duration and video_bg.duration < narration.duration:
    repeats = int(narration.duration // video_bg.duration) + 1
    video_bg = concatenate_videoclips([video_bg] * repeats, method="compose")
video_bg = video_bg.subclipped(0, narration.duration)

if os.path.exists(MUSIC_FILE):
    bg_music = AudioFileClip(MUSIC_FILE).transform(lambda gf, t: 0.1 * gf(t)).with_duration(narration.duration)
    narration = CompositeAudioClip([narration, bg_music])

video_bg = video_bg.with_audio(narration)

subtitle_clips = []
LINE_HEIGHT = 85 + (5 * 2) + 20
MAX_LINES = 2
SUBTITLE_AREA_H = LINE_HEIGHT * MAX_LINES
SUBTITLE_Y = 1500

for w in grouped_timings:
    txt = TextClip(
        text=w["text"].strip(),
        font="C:/Windows/Fonts/arialbd.ttf",
        font_size=80,
        color='white',
        stroke_color='black',
        stroke_width=4,
        size=(TARGET_W - 80, 300),  # ← explicit magasság, elég nagy 2 sorhoz is
        method='caption',            # ← caption kell ha fix size van megadva
        text_align='center'
    )

    try:
        txt = txt.with_position(('center', SUBTITLE_Y)).with_start(w["start"]).with_end(w["end"])
    except AttributeError:
        txt = txt.set_position(('center', SUBTITLE_Y)).set_start(w["start"]).set_end(w["end"])

    subtitle_clips.append(txt)

today_histroy = CompositeVideoClip([video_bg] + subtitle_clips)

# Fade in/out the entire video
try:
    # MoviePy 1.x
    today_histroy = today_histroy.fadein(0.5).fadeout(0.5)
except AttributeError:
    # MoviePy 2.x
    import moviepy.video.fx as vfx
    today_histroy = today_histroy.with_effects([vfx.FadeIn(0.5), vfx.FadeOut(0.5)])

print("4. Rendering...")
today_histroy.write_videofile(OUTPUT_FILE, fps=24, preset="ultrafast", logger='bar')

# --- 6. CLEANUP & LAUNCH ---
print("-> Final cleanup (deleting temporary files)...")

try:
    narration.close()
    today_histroy.close()
    video_bg.close()
    for c in final_clips: c.close()
except: pass

for f in downloaded_files: 
    try: 
        if os.path.exists(f): os.remove(f)
    except: pass

try:
    if os.path.exists(AUDIO_FILE): os.remove(AUDIO_FILE)
except: pass

with open(INFO_FILE, "w", encoding="utf-8") as f: f.write(upload_caption)

if not TEST_MODE:
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(story_text[:50] + "...\n")

print(f"\n🎉 DONE! Clean up finished.")
print(f"📁 Kept: {OUTPUT_FILE} and {INFO_FILE}")

if auto_open:
    try:
        os.startfile(OUTPUT_FILE)
        os.startfile(INFO_FILE)
    except: pass