Epic: AI DJ Integration for Home Assistant
Description: Create a custom Home Assistant integration that acts as an automated DJ, managing a YouTube Music playlist in real-time based on a user-defined vibe using the Gemini API.
User Story 1: Integration Setup & Authentication
Story: As a Home Assistant Admin, I want to configure the AI DJ integration with my Google and YouTube Music credentials during setup, so that the system has the necessary permissions to search for music and generate prompts.
Acceptance Criteria:
The user is prompted to input a Gemini API Key during the standard HA integration setup flow.
The user is prompted to provide YouTube Music authentication (e.g., via Cookie/Header input).
The integration successfully validates both connections before completing setup.
User Story 2: Party Management Dashboard (UI)
Story: As a party host, I want a dedicated dashboard in Home Assistant to create, view, and manage different "Parties" and their associated musical vibes.
Acceptance Criteria:
The UI has a sidebar listing existing parties and a "Create New Party" button.
Selecting a party displays a detail view with a "Vibe" text input field.
The detail view displays a historical list of played songs for that specific party.
The detail view includes an editable 'Party Start Time' field. When the 'Start' button is clicked for the first time and the field is not set, this field automatically populates with the current time now(), but the user can overwrite this value at any point.
The detail view includes an editable "Planned End Time" field alongside the Start Time
The user can delete individual songs from the history or clear the entire history.
There is a clear "Start" and "Stop" button for the active party.
The active party state, history, and calculated progress percentage must be stored persistently. If Home Assistant restarts, the AI DJ should automatically resume monitoring the active playlist without requiring the user to click "Start" again.
User Story 3: The AI DJ Engine (Backend Logic)
Story: As a party host, when I start a party, I want the system to automatically populate and maintain a YouTube Music playlist based on my defined vibe and the current time, so that the music plays continuously without my manual input.
Acceptance Criteria:
Upon pressing "Start", the system checks for a YTM playlist matching the party name and creates one if it doesn't exist.
The system monitors the playlist queue. If fewer than 2 songs remain, it triggers the LLM for a new recommendation.
The system polls the YouTube Music history every 30 seconds to update the "played songs" list in the HA UI and uses this data to prevent the LLM from suggesting duplicate tracks.
The system must filter search results by duration (e.g., strictly accepting tracks between 2:00 and 7:00 minutes).
If the exact artist/title match is not found in the top 3 results, the system should fall back to the closest match or trigger a new LLM request.
During the 30-second polling loop, if the system detects that the currently playing song is not the one the AI queued, it must log this new song into the "played songs" history.
The system must not duplicate queue entries if a user manually forces the playlist to skip forward.
Technical Implementation Notes (For the Developer):
Use ytmusicapi for playlist management and history polling.
Use type hints for all cases to catch type errors early
LLM Prompt Template: "You are a DJ hosting a party for the following vibe: {vibe_description}. Timeline Context:
Start Time: {start_time}
Expected End Time: {end_time}
Current Time: {current_time}
We are currently {progress_percentage}% through the planned duration. Use this percentage to map the energy curve (e.g., 0-20% warm-up, 40-70% peak energy, 95-100% cooldown).
These songs were played recently: {played_songs_list}. What is your next pick? Respond strictly in JSON format: {"artist": "Name", "title": "Song Title"}"
If the progress exceeds 100%, the script appends a note to the LLM saying: "The party has gone into overtime, keep the vibe going."

