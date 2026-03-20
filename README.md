# YTM AI DJ: Home Assistant Integration

**YTM AI DJ** is a custom Home Assistant integration that acts as an automated DJ. It dynamically manages a YouTube Music playlist in real-time based on a user-defined vibe and a scheduled energy curve, powered by Google's Gemini LLM.

## Features
- **Config Flow Integration**: Easily set up your YouTube Music credentials and Gemini API Key right from the Home Assistant integrations page.
- **Party Management Dashboard**: A dedicated, built-in custom UI (Lit element) located in your HA sidebar. Create new parties, set vibes (e.g., "90s upbeat techno"), and schedule start/end times.
- **Smart Audio Queue Engine**: A backend task runs every 30 seconds to monitor your active party's playlist. When the queue runs low (less than 2 unplayed songs), it queries Gemini (`gemini-1.5-flash`) for the next track dynamically adjusting to the "party progress %" to manage the energy curve (e.g., warm-up vs. peak vs. cooldown).
- **Intelligent Song Duration Filtering**: It strictly queues songs between 2 to 7 minutes to avoid randomly picking ambient noise or 10-hour loops.
- **Live Syncing**: Keeps track of manually played or skipped songs in real-time, feeding that contextual history back to the LLM to prevent duplicate or hallucinatory song queues.

## Setup Requirements

Due to the dependencies, you must ensure your Home Assistant Python environment has access to the requirements specified in `manifest.json`.
Required packages:
- `ytmusicapi >= 1.7.0`
- `google-generativeai >= 0.5.0`

If you are developing or running Home Assistant core locally, ensure they are in your virtual environment: 
```bash
pip install ytmusicapi google-generativeai
```

### 1. Installation

1. Copy the `custom_components/ytm_ai_dj` folder into your Home Assistant configuration directory under `custom_components/`.
2. Restart Home Assistant.

### 2. Configuration & Authentication

To authenticate this integration, you need two items:

1. **Gemini API Key**: Grab one for free from [Google AI Studio](https://aistudio.google.com/).
2. **YouTube Music Headers**: 
   - Open YouTube Music in your browser.
   - Open the Developer Tools (F12) -> Network tab.
   - Refresh the page, click on any request to `music.youtube.com`, and copy the exact `Cookie` string or the raw Request Headers. (Refer to the `ytmusicapi` setup documentation for more details on `auth`).

### 3. Usage

1. Navigate to **Settings -> Devices & Services -> Add Integration -> AI DJ**.
2. Input your `Gemini API Key` and your `YouTube Music HTTP Headers`.
3. Once successfully connected, restart Home Assistant to load the UI panel.
4. Open the new **"AI DJ"** panel on your left sidebar in Home Assistant.
5. Create a party and start grooving! You'll see automatic sync into a YouTube Music playlist that matches your party name.

## Technologies Used
- Home Assistant core integrations built in Python (`ConfigFlow`, `Store`, `async_track_time_interval`, WebSockets API)
- Lit Elements for the Frontend Component
- YouTube Music API via `ytmusicapi`
- Google Gemini API (`genai`)
