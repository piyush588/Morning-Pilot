# Morning Pilot

Morning Pilot is a personalized morning audio news briefing that listeners can talk back to. It collects live web news based on your selected interests, compiles the stories into a spoken radio-style script using a language model, and voices the episode through ElevenLabs. 

While listening, you can interrupt at any point via voice or text to ask follow-up questions, request deeper context, or fact-check claims. Your questions automatically update your interest profile for future briefings.

---

## Key Features

- **Personalized News Gathering**: Collects live news across user-defined topics (for example: Cybersecurity, AI, Startups, Cricket, or Markets) using live web feeds and search.
- **Broadcast-Style Script Writing**: Compiles multiple source articles into an audio script written in natural, conversational spoken English rather than disconnected bullet points.
- **Voice Synthesis**: Generates voice audio using ElevenLabs.
- **Live Voice Interruption & Q&A**: Tap the microphone or type a question during playback. The briefing automatically pauses, retrieves relevant context from source articles, and speaks the answer.
- **Adaptive Interest Profile**: The system tracks user questions and increases weights for topics you explore, decaying older topics over time.
- **Flexible Model Support**: Works with either a local Ollama instance (`llama3.2:3b`) or cloud OpenAI models (`gpt-4o`).
- **Minimalist Interface**: Clean white-and-purple layout featuring a central voice orb, question bar, story cards with source links, and readable transcript views.

---

## How It Works

```
1. Trigger (Manual or Daily Schedule)
   │
2. Load User Profile
   └─ Reads tracked topics and current interest weights
   │
3. Multi-Source News Retrieval
   └─ Searches live web sources and RSS for each topic
   │
4. Extraction & Deduplication
   └─ Extracts headlines, summaries, and source URLs
   │
5. Script Synthesis (LLM)
   └─ Formulates a cohesive 3 to 5 minute spoken radio script
   │
6. Audio Generation (ElevenLabs)
   └─ Converts the script into an MP3 audio episode
   │
7. Playback & Real-Time Q&A
   └─ User listens, interrupts with follow-up questions, and profile weights update
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- An ElevenLabs API key (for text-to-speech)
- Optional: Local [Ollama](https://ollama.ai) with `llama3.2:3b` installed, or an OpenAI API key

### 1. Clone the Repository and Set Up Environment

```bash
git clone https://github.com/your-username/morning-pilot.git
cd morning-pilot

python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the sample environment file:

```bash
cp .env.example .env
```

Open `.env` and fill in your settings:

```ini
# ElevenLabs (Required for voice audio)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
ELEVENLABS_MODEL_ID=eleven_multilingual_v2

# LLM Configuration (Uses local Ollama by default if OpenAI key is omitted)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL=llama3.2:3b

# Web Search (Optional; falls back to live web search automatically)
TINYFISH_API_KEY=your_tinyfish_api_key_here

# Server Settings
APP_HOST=0.0.0.0
APP_PORT=8001
BRIEFING_SCHEDULE_HOUR=7
BRIEFING_MAX_STORIES=5
```

### 4. Initialize Profile and Run

Seed a default profile:

```bash
python scripts/seed_profile.py
```

Start the application:

```bash
python -m app.main
```

Open your browser at `http://localhost:8001`.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check and configured service status |
| `GET` | `/api/profile` | Retrieve the current user profile and interest scores |
| `PUT` | `/api/profile` | Update user name and tracked interest topics |
| `GET` | `/api/profile/interests` | Get scored interests and recent activity logs |
| `POST` | `/api/briefing/generate` | Synchronously generate a complete briefing |
| `POST` | `/api/briefing/generate/stream` | Stream generation progress step-by-step via Server-Sent Events (SSE) |
| `GET` | `/api/briefing/latest` | Retrieve the latest briefing metadata and story list |
| `GET` | `/api/briefing/{id}/audio` | Stream the generated MP3 audio file |
| `POST` | `/api/conversation/ask` | Submit a text question regarding the briefing and receive a cited answer |
| `POST` | `/api/conversation/ask-voice` | Upload a voice recording (`.webm`) for audio Q&A |

Interactive Swagger documentation is available at `http://localhost:8001/docs`.

---

## Project Structure

```
morning-pilot/
├── app/
│   ├── api/                 # FastAPI route handlers
│   │   ├── briefing.py      # Generation and audio streaming routes
│   │   ├── conversation.py  # Q&A and speech interaction routes
│   │   ├── health.py        # Service health checks
│   │   └── profile.py       # Profile management routes
│   ├── core/                # Core utilities
│   │   ├── cache.py         # File-based response cache
│   │   ├── db.py            # Local JSON profile and briefing store
│   │   └── scheduler.py     # APScheduler daily morning briefing cron
│   ├── models/              # Pydantic data schemas
│   │   ├── briefing.py
│   │   ├── conversation.py
│   │   └── profile.py
│   ├── services/            # Business logic and external integrations
│   │   ├── fetch.py         # Web page extraction and parsing
│   │   ├── llm.py           # Script generation and Q&A engine
│   │   ├── pipeline.py      # End-to-end briefing generator
│   │   ├── profile_engine.py# Dynamic scoring and decay logic
│   │   ├── search.py        # Live news search and query handling
│   │   ├── tts.py           # ElevenLabs speech generation
│   │   └── web_agent.py     # Source verification
│   ├── config.py            # Pydantic Settings
│   └── main.py              # Application entry point
├── frontend/                # Static web interface (HTML, CSS, Vanilla JS)
│   ├── css/
│   │   └── style.css        # Minimal white and purple design system
│   ├── js/
│   │   ├── api.js           # API client
│   │   ├── app.js           # Main UI controller
│   │   ├── components.js    # UI elements and SVG icon library
│   │   ├── conversation.js  # Audio recording and Q&A logic
│   │   ├── player.js        # Voice orb and audio playback controller
│   │   ├── profile.js       # Topic picker and sidebar manager
│   │   └── transcript.js    # Story cards and transcript view
│   └── index.html           # Main application view
├── scripts/
│   └── seed_profile.py      # Profile initialization script
├── requirements.txt         # Python dependencies
└── README.md
```

---

## License

This project is licensed under the MIT License.
