# carllm

![carllm logo](src/assets/logo.png)

**AI-powered car diagnostics that improve with every interaction.**

carllm is a Vue 3 + Firebase web application that uses modern large language models to guide users from vague, real-world vehicle symptoms to a clear, high-quality diagnostic. Rather than offering one-shot guesses, the system reasons iteratively, asks targeted follow-up questions, and continuously builds long-term knowledge about each vehicle.

---

## What carllm does differently

### Conversation-driven diagnostics
Instead of static forms or generic advice, carllm runs an interactive diagnostic session. The system asks clarifying questions until it has enough signal to reason confidently about the underlying issue.

### Persistent vehicle knowledge
Each user maintains a garage of vehicles. Details about a car—drivetrain, prior repairs, replaced parts, and other relevant context—are remembered and reused automatically in future sessions. Users do not have to restate information the system already knows.

### Multi-model reasoning with adjudication
When sufficient information has been gathered, the diagnostic task is fanned out to multiple LLMs in parallel. A dedicated judge model evaluates their responses and selects the most accurate and coherent diagnosis to present to the user. This approach prioritizes answer quality while minimizing user effort.

---

## How it works

### Garage & session model
Users create a garage of cars. Each car can have multiple diagnostic sessions, allowing issues to be explored independently while sharing long-term vehicle context.

### Adaptive questioning loop
During a session, the system identifies missing or ambiguous information and asks targeted follow-up questions. This loop continues until the model determines there is enough evidence to proceed.

### Parallel analysis & judging
Multiple LLMs analyze the completed case simultaneously. Their outputs are evaluated by a judge model, which selects and returns a single, high-confidence diagnostic.

### Knowledge accumulation
New information—such as confirmed vehicle characteristics or replaced components—is persisted to the vehicle record and influences all future diagnostics.

---

## Tech stack
- Vue 3 (frontend)
- Firebase
  - Authentication
  - Firestore
  - Cloud Functions
- Playwright for end-to-end testing

---

## Run locally
```bash
npm install
npm run serve
```

## Build
```bash
npm run build
```

## Lint
```bash
npm run lint
```

## End-to-end tests (Playwright)
```bash
npx playwright install
npm run test:e2e
```

---

## Firebase notes
- Firebase initialization is located in `src/firebase.js`.
- Secrets and private keys should be managed via environment variables and must not be committed to the repository.

---

## About the project
carllm is an exploration of iterative AI reasoning, stateful user context, and multi-model decision systems applied to a real-world problem domain. The focus is on building AI software that does not just answer questions, but learns over time and reduces friction for the user with each interaction.

---

## Summer 2026 internship
I’m currently looking for a **Summer 2026 internship**. I’m a college student majoring in **Electrical Engineering**, with strong interest in **Software Engineering** or **Electrical Engineering** roles.  
Email: **eddieharmon20@gmail.com**
