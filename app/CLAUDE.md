# app

Expo, one codebase: `npx expo start --web` is the desktop app in a browser, the judging
surface; Expo Go or the iOS Simulator runs the same code on a phone. The app is a chat UI
and nothing else: it posts a message to the API and renders the reply's cards.

Layout: `src/api.ts` is the one client; `src/screens/Chat.tsx` is the screen; `src/components/`
holds one card per attachment kind the API returns (templates, explanation, candidates,
forecast, clip, post, comparison).

Rules: no computation here, the API's numbers are shown as they arrive. Every button sends a
chat message, so the app and a typed sentence do the same thing.

Config: `EXPO_PUBLIC_API_URL`, default `http://localhost:8000`; on a phone, the droplet or
the laptop's LAN address.
