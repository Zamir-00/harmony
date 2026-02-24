# Harmony

Harmony is a small self-hosted Discord-like app designed for groups of roughly 5-10 users.

## Features

- Real-time room-based text chat over WebSockets.
- Browser-based voice chat for everyone in a room (peer-to-peer WebRTC mesh).
- Screen sharing with system/computer audio where browser + OS permissions allow it.
- Minimal single-page UI, no external accounts or SaaS dependency.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

## Usage notes

- Start in one room with 2+ browser tabs/devices.
- Click **Start Voice** to share your microphone.
- Click **Share Screen + Audio** to share desktop/tab video and audio.
- Browsers often require HTTPS for full WebRTC + screen/audio support outside localhost.

## Deployment notes

- Data and room membership are in-memory only (reset on restart).
- For internet-facing use, put Harmony behind HTTPS (Nginx/Caddy) and add authentication.
- This is a lightweight mesh design: each participant sends streams directly to every other participant, which is best for small groups.
