# Repository Guidelines

## Project Structure & Module Organization
- `src/` contains application code for the Vue 3 app.
  - `src/main.js` boots the app and mounts the root component.
  - `src/App.vue` is the root single-file component.
  - `src/components/` holds reusable Vue components.
  - `src/assets/` contains static assets used by the UI.
- `public/` contains static files copied as-is at build time (e.g., `public/index.html`).
- Configuration lives at the repo root (e.g., `vue.config.js`, `babel.config.js`).

## Build, Test, and Development Commands
- `npm install` installs dependencies.
- `npm run serve` starts the Vue CLI dev server with hot reload.
- `npm run build` creates a production build in `dist/`.
- `npm run lint` runs ESLint and applies auto-fixes where possible.

## Coding Style & Naming Conventions
- Indentation: 2 spaces in JS/Vue files (default Vue CLI/ESLint style).
- Vue components: PascalCase file names (e.g., `MyWidget.vue`).
- JS modules: use camelCase for variables/functions and PascalCase for classes.
- Linting: ESLint with `plugin:vue/vue3-essential` and `eslint:recommended` (see `package.json`).
- UI color palette: use black, white, and grayscale tones only.

## Testing Guidelines
- No test framework is currently configured.
- If adding tests, document the framework and add scripts in `package.json` (e.g., `npm run test`).

## Commit & Pull Request Guidelines
- Commit history is minimal and informal (e.g., “first commit”, “fresh start”).
- Prefer concise, imperative messages going forward, e.g., `Add login form` or `Fix header layout`.
- Pull requests should include a clear summary, the motivation for the change, and any manual verification steps. Include screenshots for UI changes.

## Security & Configuration Tips
- Client configuration is managed via Firebase; avoid committing secrets. Prefer environment variables for any keys that should not be public.
- Firebase Functions (v2): if a function needs a secret, declare it on the decorator (e.g., `@https_fn.on_call(secrets=[...])` or `@firestore_fn.on_document_created(secrets=[...])`) or the secret will not be available at runtime, even if set.
- When adding new assets, keep file sizes small to avoid slowing down the dev server and build.

## Database Schema Updates
- Always reference `DB_SCHEMA.md` before making any database or Firestore schema updates.
- After any database schema update, update `DB_SCHEMA.md` to reflect the changes so it stays current.

## Firebase Setup
- This is a Firebase-backed project; keep initialization in a single module (e.g., `src/firebase.js`) and import it where needed.
- Current web configuration and initialization example:

```js
// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyCMuaSaSiJCTnmeLUbv_k6n-sf54N13-vQ",
  authDomain: "carllm-de234.firebaseapp.com",
  projectId: "carllm-de234",
  storageBucket: "carllm-de234.firebasestorage.app",
  messagingSenderId: "174750378350",
  appId: "1:174750378350:web:ad2d5cf1f58c4e3aeb797f",
  measurementId: "G-W7TEPX9RHK"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
```
