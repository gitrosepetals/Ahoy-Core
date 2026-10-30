# A-hoy Ship (Capacitor)

Mobile shell for the Captain app. Milestone A wires config + push plugin dependency; native iOS/Android projects are added when you run `npx cap add ios|android` on a machine with Xcode / Android Studio.

## Setup

```bash
cd apps/mobile
npm install
# Optional once tooling is available:
# npx cap add ios
# npx cap add android
npx cap sync
```

Deep links / universal links for magic-link auth and push payloads should use paths:

- `/auth/verify?token=…` — sign-in only
- `/ship` — home
- `/ship/queue` — approval queue (Milestone C)
- `/ship/reviews/:id` — review detail (Milestone C)

Associated domains (to configure in Apple / Android consoles later): `applinks:app.ahoy.example` (placeholder).
