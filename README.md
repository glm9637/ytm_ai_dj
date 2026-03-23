YTM AI DJ: Home Assistant Integration

YTM AI DJ is a custom Home Assistant integration that acts as an automated DJ. It dynamically manages your music in real-time based on a user-defined vibe and a scheduled energy curve, powered by Google's Gemini LLM.

Features

    Config Flow Integration: Set up your YouTube Music credentials and Gemini API Key via the native HA integrations page.

    Party Management Dashboard: A custom sidebar UI (Lit element) to create parties, set vibes (e.g., "90s upbeat techno"), and schedule energy curves.

    Music Assistant (MASS) Integration: Uses the MASS engine to bypass Chromecast "URL blocked" errors, ensuring gapless playback and reliable enqueuing.

    Smart Audio Queue Engine: Monitors your active queue every 30 seconds. When the queue runs low (< 2 songs), it queries Gemini for the next track, adjusting the "party progress %" to manage the energy (warm-up vs. peak vs. cooldown).

    Duration Filtering: Strictly picks songs between 2 to 7 minutes to avoid "10-hour loops" or 30-second interludes.

    Live Syncing: Watches your actual play history. If you manually skip or play a song, the AI DJ updates its context instantly to prevent duplicates.

Setup Requirements
1. Music Assistant (Mandatory)

For this integration to play music on your speakers (Chromecasts, Sonos, etc.) without stopping, you must have Music Assistant installed and configured with your YouTube Music account.
2. Python Dependencies

Ensure your environment has access to:

    ytmusicapi >= 1.7.0

    google-generativeai >= 0.5.0

Installation

    Copy the custom_components/ytm_ai_dj folder into your custom_components/ directory.

    Ensure your manifest.json includes "version": "1.0.0" (Required for HACS).

    Restart Home Assistant.

1. Configuration

    Gemini API Key: Get one for free from Google AI Studio.

    YouTube Music Headers:

        Open YouTube Music in your browser -> Developer Tools (F12) -> Network tab.

        Refresh, click a request to music.youtube.com, and copy the Request Headers.

2. Usage

    Go to Settings -> Devices & Services -> Add Integration -> AI DJ.

    Enter your keys and headers.

    Open the AI DJ panel in the sidebar.

    Select a Target Speaker: Choose a Music Assistant player (prefixed with mass_) from the dropdown.

    Start your party!

Technologies Used

    Home Assistant Core: ConfigFlow, Store, WebSockets API.

    Frontend: Lit Elements with real-time polling.

    AI: Google Gemini API (gemini-2.5-flash).

    Music Engine: Music Assistant (MASS) & ytmusicapi.

Note on Playback

To ensure the AI DJ can manage the queue, always start your music session via the Music Assistant interface or by selecting the MASS player in the AI DJ dashboard. Standard Chromecast entities do not support the dynamic enqueuing required for a gapless DJ experience.