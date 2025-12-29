<template>
  <div class="app">
    <header class="nav">
      <div class="brand">
        <span class="brand-mark">CARLLM</span>
        <span class="brand-sub">diagnose smarter</span>
      </div>
      <nav class="nav-links">
      </nav>
      <div class="nav-actions">
        <button
          class="btn btn-ghost"
          type="button"
          @click="handleAuth"
          :disabled="isAuthBusy"
        >
          <span v-if="!user">Log in with Google</span>
          <span v-else>Log out</span>
        </button>
      </div>
    </header>

    <main v-if="!user" class="hero">
      <section class="hero-left">
        <p class="eyebrow">LLM-powered vehicle diagnostics</p>
        <h1>Turn symptoms into clear repair guidance in minutes.</h1>
        <p class="lead">
          CARLLM translates driver-reported issues and noise patterns into probable
          causes and recommended next steps.
        </p>
        <div class="hero-actions">
          <button
            class="btn btn-primary"
            type="button"
            @click="handlePrimaryAction"
            :disabled="isAuthBusy"
          >
            <span v-if="!user">Get started with Google</span>
            <span v-else>Go to dashboard</span>
          </button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <p v-if="user" class="user-pill">
          Signed in as <strong>{{ user.displayName || user.email }}</strong>
        </p>
      </section>

      <section class="hero-right" aria-label="Diagnostic preview">
        <div class="card">
          <h3>Symptoms</h3>
          <ul>
            <li>Rough idle after warm start</li>
            <li>Intermittent misfire on cylinder 3</li>
            <li>Fuel smell near engine bay</li>
          </ul>
          <h3>Likely causes</h3>
          <ul>
            <li>Leaking injector seal</li>
            <li>Failing ignition coil pack</li>
            <li>Vacuum leak at intake manifold</li>
          </ul>
        </div>
      </section>
    </main>

    <aside v-if="!user" class="floating-callout" aria-label="Internship availability">
      <p class="callout-eyebrow">Open to Summer 2026 internship</p>
      <h4>Electrical Engineering major</h4>
      <p>
        Interested in Software Engineering or Electrical Engineering roles.
      </p>
      <a class="callout-link" href="mailto:eddieharmon20@gmail.com">
        eddieharmon20@gmail.com
      </a>
    </aside>

    <section v-if="!user" id="how" class="section">
      <h2>How it works</h2>
      <div class="grid">
        <div class="tile">
          <h4>Gather inputs</h4>
          <p>Collect driver-reported symptoms and any notes you already have.</p>
        </div>
        <div class="tile">
          <h4>LLM fan‑out</h4>
          <p>Multiple LLM calls explore likely causes, checks, and fixes in parallel.</p>
        </div>
        <div class="tile">
          <h4>Rank + summarize</h4>
          <p>We merge the best answers into a clear, ranked diagnosis plan.</p>
        </div>
      </div>
    </section>

    <section v-if="!user" id="features" class="section alt">
    </section>

    <section v-else-if="view === 'cars'" class="dashboard">
      <div class="dashboard-header">
        <div>
          <h1>Garage</h1>
        </div>
        <button class="btn btn-primary" type="button" @click="openModal">Add car</button>
      </div>
      <div class="dashboard-empty" v-if="cars.length === 0">
        <p>Ready when you are. Your cases will appear here.</p>
      </div>
      <div class="cars-grid" v-else>
        <div v-for="car in cars" :key="car.id" class="car-card">
          <button
            class="car-card-delete"
            type="button"
            aria-label="Delete car"
            @click="deleteCar(car)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path
                d="M5 7h14M9 7V5h6v2m-7 3v7m4-7v7m4-7v7M7 7l1 12h8l1-12"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </button>
          <h3>{{ car.name }}</h3>
          <p>{{ car.year }} {{ car.make }} {{ car.model }}</p>
          <button class="btn btn-outline" type="button" @click="openCar(car)">
            Open dashboard
          </button>
        </div>
      </div>
    </section>

    <section v-else-if="view === 'car'" class="dashboard">
      <div class="dashboard-header">
        <div>
          <h1>{{ selectedCar?.name }}</h1>
          <p class="muted">
            {{ selectedCar?.year }} {{ selectedCar?.make }} {{ selectedCar?.model }}
          </p>
        </div>
        <div class="dashboard-actions">
          <button class="btn btn-outline" type="button" @click="backToCars">All cars</button>
          <button class="btn btn-primary" type="button" @click="openDiagnosticChat">
            New diagnostic
          </button>
        </div>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="dashboard-empty" v-if="diagnostics.length === 0">
        <p>No diagnostics yet. Start your first scan for this car.</p>
      </div>
      <div class="cars-grid" v-else>
        <button
          v-for="diag in diagnostics"
          :key="diag.id"
          class="car-card car-card-action"
          type="button"
          @click="openDiagnostic(diag)"
        >
          <h3>{{ diag.title }}</h3>
          <p class="muted">{{ diag.summary }}</p>
          <span class="card-cta">Continue chat</span>
        </button>
      </div>
    </section>

    <section v-else class="chat-board">
      <div class="dashboard-header">
        <div>
          <h1>Lets fix your car.</h1>
          <p class="muted">
            {{ selectedCar?.year }} {{ selectedCar?.make }} {{ selectedCar?.model }}
          </p>
        </div>
        <div class="dashboard-actions">
          <button class="btn btn-outline" type="button" @click="backToCar">Back to car</button>
        </div>
      </div>
      <div class="chat-shell">
        <div class="chat-history">
          <div v-if="chatMessages.length === 0" class="chat-empty">
            <p>Start with a quick description of the issue.</p>
          </div>
          <div
            v-for="message in renderedMessages"
            :key="message.id"
            class="chat-message"
            :class="message.role"
          >
            <p class="chat-meta">{{ message.role === "user" ? "You" : "CARLLM" }}</p>
            <div v-if="message.structured" class="structured-output">
              <p class="structured-title">
                {{ message.structured.diagnosticAnswer || "Diagnosis pending" }}
              </p>
              <div class="structured-block">
                <span class="structured-label">Justification</span>
                <ul
                  v-if="message.structured.justification.length"
                  class="structured-list"
                >
                  <li
                    v-for="(item, index) in message.structured.justification"
                    :key="index"
                  >
                    {{ item }}
                  </li>
                </ul>
                <p v-else class="structured-empty">No justification provided.</p>
              </div>
            </div>
            <div v-else-if="message.answers" class="answer-output">
              <ol class="answer-list">
                <li v-for="(pair, index) in message.answers.pairs" :key="index">
                  <p class="answer-question">{{ pair.question }}</p>
                  <p class="answer-value">{{ pair.answer }}</p>
                </li>
              </ol>
            </div>
            <p v-else class="chat-content">{{ message.content }}</p>
          </div>
        </div>
        <div v-if="activeQuestions.length" class="question-form">
          <div
            v-for="(question, index) in activeQuestions"
            :key="index"
            class="question-field"
          >
            <label class="question-label">{{ question }}</label>
            <textarea
              v-model="questionAnswers[index]"
              rows="2"
              placeholder="Type your answer"
            />
          </div>
          <button
            class="btn btn-primary"
            type="button"
            @click="submitIntakeAnswers"
            :disabled="isChatAwaiting || isChatSending"
          >
            Submit answers
          </button>
        </div>
        <div v-else class="chat-input-row">
          <textarea
            v-model="chatInput"
            rows="3"
            :placeholder="chatPlaceholder"
          />
          <button
            class="btn btn-primary"
            type="button"
            @click="sendChatMessage"
            :disabled="isChatAwaiting || isChatSending"
          >
            Send
          </button>
        </div>
        <div v-if="isChatAwaiting" class="chat-status">
          <span class="spinner" aria-hidden="true"></span>
          <span>Working on it…</span>
          <span class="token-count">{{ chatTokenCount }} total tokens</span>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </section>

    <div v-if="isModalOpen" class="modal-backdrop" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h2>Create a car</h2>
          <button class="icon-button" type="button" @click="closeModal" aria-label="Close">
            ×
          </button>
        </div>
        <form class="modal-body" @submit.prevent="submitCar">
          <label class="field">
            <span>Name</span>
            <input v-model="carForm.name" type="text" placeholder="e.g., Family SUV" required />
          </label>
          <label class="field">
            <span>Year</span>
            <input v-model="carForm.year" type="number" min="1980" max="2099" required />
          </label>
          <label class="field">
            <span>Make</span>
            <input v-model="carForm.make" type="text" placeholder="e.g., Toyota" required />
          </label>
          <label class="field">
            <span>Model</span>
            <input v-model="carForm.model" type="text" placeholder="e.g., RAV4" required />
          </label>
          <p class="field-note">
            Submodel and engine will be determined after you submit if multiple options exist.
          </p>
          <div class="modal-actions">
            <button class="btn btn-outline" type="button" @click="closeModal">Cancel</button>
            <button class="btn btn-primary" type="submit">Create car</button>
          </div>
        </form>
      </div>
    </div>

    <div
      v-if="isDeleteModalOpen"
      class="modal-backdrop"
      @click.self="closeDeleteModal"
    >
      <div class="modal">
        <div class="modal-header">
          <h2>Delete car</h2>
          <button
            class="icon-button"
            type="button"
            @click="closeDeleteModal"
            aria-label="Close"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <p class="field-note">
            This will remove <strong>{{ carPendingDelete?.name || "this car" }}</strong> from
            your garage. This action cannot be undone.
          </p>
          <div class="modal-actions">
            <button class="btn btn-outline" type="button" @click="closeDeleteModal">
              Cancel
            </button>
            <button class="btn btn-primary" type="button" @click="confirmDeleteCar">
              Delete car
            </button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from "vue";
import { auth, db, functions, googleProvider } from "./firebase";
import { signInWithPopup, signOut, onAuthStateChanged } from "./auth";
import {
  collection,
  addDoc,
  getDocs,
  limit,
  onSnapshot,
  query,
  where,
  orderBy,
  doc,
  updateDoc,
  deleteDoc,
} from "firebase/firestore";
import { httpsCallable } from "firebase/functions";

const user = ref(null);
const error = ref("");
const isAuthBusy = ref(false);
const isChatSending = ref(false);
const isModalOpen = ref(false);
const isDeleteModalOpen = ref(false);
const cars = ref([]);
const diagnostics = ref([]);
const view = ref("cars");
const selectedCar = ref(null);
const carPendingDelete = ref(null);
const chatId = ref("");
const diagnosticId = ref("");
const chatPhase = ref("");
const chatAwaitingResponse = ref(false);
const chatTokenCount = ref(0);
const chatMessages = ref([]);
const chatInput = ref("");
const carForm = ref({
  name: "",
  year: "",
  make: "",
  model: "",
});

if (process.env.VUE_APP_E2E_FAKE_AUTH === "1" && typeof window !== "undefined") {
  window.__carllmE2E = {
    setView: (nextView) => {
      view.value = nextView;
    },
    setChatProgress: ({ awaiting, tokens } = {}) => {
      chatAwaitingResponse.value = Boolean(awaiting);
      if (Number.isFinite(tokens)) {
        chatTokenCount.value = tokens;
      }
    },
  };
}

let unsubscribeChat = null;
let unsubscribeMessages = null;
let unsubscribeCars = null;
let unsubscribeDiagnostics = null;

const functionCalls = {
  question_prompt: httpsCallable(functions, "question_prompt"),
  fanout_diagnosis: httpsCallable(functions, "fanout_diagnosis"),
  chat_reply: httpsCallable(functions, "chat_reply"),
};

const handleAuth = async () => {
  error.value = "";
  isAuthBusy.value = true;
  try {
    if (!user.value) {
      await signInWithPopup(auth, googleProvider);
      view.value = "cars";
    } else {
      await signOut(auth);
    }
  } catch (err) {
    error.value = err?.message || "Authentication failed. Please try again.";
  } finally {
    isAuthBusy.value = false;
  }
};

const clearChatListeners = () => {
  if (unsubscribeChat) {
    unsubscribeChat();
    unsubscribeChat = null;
  }
  if (unsubscribeMessages) {
    unsubscribeMessages();
    unsubscribeMessages = null;
  }
};

const resetChatState = () => {
  clearChatListeners();
  chatId.value = "";
  diagnosticId.value = "";
  chatMessages.value = [];
  chatPhase.value = "";
  chatAwaitingResponse.value = false;
  chatTokenCount.value = 0;
  chatInput.value = "";
};

const isChatAwaiting = computed(() => chatAwaitingResponse.value || isChatSending.value);

const normalizeJustification = (value) => {
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter((item) => item.trim());
  }
  if (typeof value === "string" && value.trim()) {
    return [value.trim()];
  }
  return [];
};

const extractJsonPayload = (content) => {
  if (typeof content !== "string") {
    return null;
  }
  let trimmed = content.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("```")) {
    const lines = trimmed.split("\n");
    lines.shift();
    if (lines.length && lines[lines.length - 1].trim().startsWith("```")) {
      lines.pop();
    }
    trimmed = lines.join("\n").trim();
  }
  if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
    return null;
  }
  try {
    return JSON.parse(trimmed);
  } catch (error) {
    return null;
  }
};

const parseQuestionPayload = (message) => {
  if (!message || message.role !== "assistant") {
    return [];
  }
  const payload = extractJsonPayload(message.content);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return [];
  }
  if (!Array.isArray(payload.questions)) {
    return [];
  }
  return payload.questions
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
};

const parseAnswerPayload = (message) => {
  if (!message || message.role !== "user") {
    return null;
  }
  const payload = extractJsonPayload(message.content);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  if (!Array.isArray(payload.answers)) {
    return null;
  }
  const questions = Array.isArray(payload.questions) ? payload.questions : [];
  const answers = payload.answers
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
  const pairs = answers.map((answer, index) => ({
    question:
      typeof questions[index] === "string" && questions[index].trim()
        ? questions[index].trim()
        : `Question ${index + 1}`,
    answer,
  }));
  return { pairs };
};

const parseStructuredOutput = (message) => {
  if (!message || message.role !== "assistant") {
    return null;
  }
  const payload = extractJsonPayload(message.content);
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  const hasFields =
    "diagnostic_answer" in payload ||
    "diagnosticAnswer" in payload ||
    "explanation" in payload ||
    "justifacation" in payload ||
    "justification" in payload ||
    "model_name" in payload ||
    "modelName" in payload;
  if (!hasFields) {
    return null;
  }
  return {
    modelName:
      payload.model_name ||
      payload.modelName ||
      message?.metadata?.winnerModel ||
      message?.metadata?.model ||
      "",
    diagnosticAnswer: payload.diagnostic_answer || payload.diagnosticAnswer || "",
    justification: normalizeJustification(
      payload.justifacation ?? payload.justification
    ),
    explanation: payload.explanation || "",
  };
};

const renderedMessages = computed(() =>
  chatMessages.value
    .map((message) => ({
      ...message,
      structured: parseStructuredOutput(message),
      questions: parseQuestionPayload(message),
      answers: parseAnswerPayload(message),
    }))
    .filter((message) => !(message.role === "assistant" && message.questions.length))
);

const activeQuestions = computed(() => {
  if (chatPhase.value !== "intake_answers") {
    return [];
  }
  for (let i = chatMessages.value.length - 1; i >= 0; i -= 1) {
    const message = chatMessages.value[i];
    const questions = parseQuestionPayload(message);
    if (questions.length) {
      return questions;
    }
  }
  return [];
});

const questionAnswers = ref([]);

watch(activeQuestions, (questions) => {
  questionAnswers.value = questions.map(() => "");
});

const submitIntakeAnswers = async () => {
  error.value = "";
  if (!user.value || !selectedCar.value) {
    error.value = "You must be signed in and select a car.";
    return;
  }
  if (!chatId.value) {
    error.value = "Start the diagnostic before answering questions.";
    return;
  }
  const questions = activeQuestions.value;
  if (!questions.length) {
    error.value = "No active questions to answer.";
    return;
  }
  const trimmedAnswers = questionAnswers.value.map((answer) => answer.trim());
  if (trimmedAnswers.some((answer) => !answer)) {
    error.value = "Please answer every question.";
    return;
  }
  if (isChatAwaiting.value) {
    return;
  }

  isChatSending.value = true;
  try {
    const payload = JSON.stringify({
      questions,
      answers: trimmedAnswers,
    });
    const messageRef = await addDoc(
      collection(db, "chats", chatId.value, "messages"),
      {
        role: "user",
        promptType: "intake",
        content: payload,
        createdAt: Date.now(),
        source: "user",
        metadata: { intakeStage: "followup_answer" },
      }
    );

    await updateDoc(doc(db, "chats", chatId.value), {
      awaitingResponse: true,
      latestMessageId: messageRef.id,
      updatedAt: Date.now(),
      phase: "diagnosis_pending",
      tokensReceived: 0,
    });

    const callFunction = functionCalls.fanout_diagnosis;
    await callFunction({
      chatId: chatId.value,
      messageId: messageRef.id,
    });
  } catch (err) {
    error.value = err?.message || "Failed to send answers.";
    try {
      await updateDoc(doc(db, "chats", chatId.value), {
        awaitingResponse: false,
        updatedAt: Date.now(),
      });
    } catch (updateError) {
      console.error(updateError);
    }
  } finally {
    isChatSending.value = false;
  }
};

const chatPlaceholder = computed(() => {
  if (!chatId.value) {
    return "Describe what is happening with your car.";
  }
  if (chatPhase.value === "intake_answers") {
    return "Answer the follow-up questions.";
  }
  if (chatPhase.value === "normal") {
    return "Ask a follow-up question or add more details.";
  }
  return "Describe what is happening with your car.";
});

const listenForCars = (uid) => {
  const carsQuery = query(
    collection(db, "cars"),
    where("userId", "==", uid),
    orderBy("createdAt", "desc")
  );
  return onSnapshot(carsQuery, (snapshot) => {
    cars.value = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
  });
};

onMounted(() => {
  onAuthStateChanged(auth, (currentUser) => {
    user.value = currentUser;
    cars.value = [];
    diagnostics.value = [];
    selectedCar.value = null;
    view.value = "cars";
    resetChatState();
    if (unsubscribeCars) {
      unsubscribeCars();
      unsubscribeCars = null;
    }
    if (unsubscribeDiagnostics) {
      unsubscribeDiagnostics();
      unsubscribeDiagnostics = null;
    }
    if (currentUser) {
      unsubscribeCars = listenForCars(currentUser.uid);
    }
  });
});

watch(chatId, (newId) => {
  clearChatListeners();
  chatMessages.value = [];
  chatPhase.value = "";
  chatAwaitingResponse.value = false;
  chatTokenCount.value = 0;
  if (!newId) {
    return;
  }

  const chatRef = doc(db, "chats", newId);
  unsubscribeChat = onSnapshot(chatRef, (snapshot) => {
    if (!snapshot.exists()) {
      return;
    }
    const data = snapshot.data();
    chatPhase.value = data.phase || "";
    chatAwaitingResponse.value = Boolean(data.awaitingResponse);
    chatTokenCount.value = Number.isFinite(data.tokensReceived)
      ? data.tokensReceived
      : 0;
    if (!diagnosticId.value && data.diagnosticId) {
      diagnosticId.value = data.diagnosticId;
    }
  });

  const messagesQuery = query(
    collection(db, "chats", newId, "messages"),
    orderBy("createdAt", "asc")
  );
  unsubscribeMessages = onSnapshot(messagesQuery, (snapshot) => {
    chatMessages.value = snapshot.docs.map((docSnap) => ({
      id: docSnap.id,
      ...docSnap.data(),
    }));
  });
});

onBeforeUnmount(() => {
  clearChatListeners();
  if (unsubscribeCars) {
    unsubscribeCars();
    unsubscribeCars = null;
  }
  if (unsubscribeDiagnostics) {
    unsubscribeDiagnostics();
    unsubscribeDiagnostics = null;
  }
});

const openModal = () => {
  isModalOpen.value = true;
};

const closeModal = () => {
  isModalOpen.value = false;
};

const openDeleteModal = (car) => {
  carPendingDelete.value = car;
  isDeleteModalOpen.value = true;
};

const closeDeleteModal = () => {
  isDeleteModalOpen.value = false;
  carPendingDelete.value = null;
};

const submitCar = async () => {
  if (!user.value) {
    error.value = "You must be signed in to create a car.";
    return;
  }
  isModalOpen.value = false;
  try {
    const now = Date.now();
    const docRef = await addDoc(collection(db, "cars"), {
      name: carForm.value.name.trim(),
      year: Number(carForm.value.year),
      make: carForm.value.make.trim(),
      model: carForm.value.model.trim(),
      userId: user.value.uid,
      createdAt: now,
      updatedAt: now,
    });
    selectedCar.value = {
      id: docRef.id,
      name: carForm.value.name.trim(),
      year: Number(carForm.value.year),
      make: carForm.value.make.trim(),
      model: carForm.value.model.trim(),
    };
    openCar(selectedCar.value);
  } catch (err) {
    error.value = err?.message || "Failed to create car.";
  }
  carForm.value = {
    name: "",
    year: "",
    make: "",
    model: "",
  };
};

const deleteCar = async (car) => {
  if (!car?.id) {
    error.value = "Car not found.";
    return;
  }
  openDeleteModal(car);
};

const confirmDeleteCar = async () => {
  error.value = "";
  if (!user.value) {
    error.value = "You must be signed in to delete a car.";
    return;
  }
  const car = carPendingDelete.value;
  if (!car?.id) {
    error.value = "Car not found.";
    closeDeleteModal();
    return;
  }
  try {
    await deleteDoc(doc(db, "cars", car.id));
  } catch (err) {
    error.value = err?.message || "Failed to delete car.";
  } finally {
    closeDeleteModal();
  }
};

const listenForDiagnostics = (uid, carId) => {
  const diagnosticsQuery = query(
    collection(db, "diagnostics"),
    where("userId", "==", uid),
    where("carId", "==", carId),
    orderBy("createdAt", "desc")
  );
  return onSnapshot(diagnosticsQuery, (snapshot) => {
    diagnostics.value = snapshot.docs.map((doc) => ({ id: doc.id, ...doc.data() }));
  });
};

const openCar = (car) => {
  selectedCar.value = car;
  view.value = "car";
  diagnostics.value = [];
  resetChatState();
  if (user.value) {
    if (unsubscribeDiagnostics) {
      unsubscribeDiagnostics();
    }
    unsubscribeDiagnostics = listenForDiagnostics(user.value.uid, car.id);
  }
};

const backToCars = () => {
  view.value = "cars";
  selectedCar.value = null;
  diagnostics.value = [];
  resetChatState();
  if (unsubscribeDiagnostics) {
    unsubscribeDiagnostics();
    unsubscribeDiagnostics = null;
  }
};

const handlePrimaryAction = async () => {
  if (!user.value) {
    await handleAuth();
    return;
  }
  backToCars();
};

const openDiagnosticChat = () => {
  error.value = "";
  resetChatState();
  view.value = "chat";
};

const openDiagnostic = async (diag) => {
  error.value = "";
  if (!user.value) {
    error.value = "You must be signed in to open a diagnostic.";
    return;
  }
  if (!diag?.id) {
    error.value = "Diagnostic not found.";
    return;
  }

  resetChatState();

  try {
    const chatsQuery = query(
      collection(db, "chats"),
      where("diagnosticId", "==", diag.id),
      where("userId", "==", user.value.uid),
      limit(1)
    );
    const snapshot = await getDocs(chatsQuery);
    if (snapshot.empty) {
      error.value = "No chat found for this diagnostic yet.";
      return;
    }
    diagnosticId.value = diag.id;
    chatId.value = snapshot.docs[0].id;
    view.value = "chat";
  } catch (err) {
    error.value = err?.message || "Failed to open diagnostic chat.";
  }
};

const backToCar = () => {
  error.value = "";
  resetChatState();
  view.value = "car";
};

const createDiagnosticAndChat = async (initialSummary) => {
  if (!user.value || !selectedCar.value) {
    throw new Error("Missing user or car context.");
  }
  const now = Date.now();
  const dateLabel = new Date(now).toISOString().slice(0, 10);
  const diagnosticRef = await addDoc(collection(db, "diagnostics"), {
    userId: user.value.uid,
    carId: selectedCar.value.id,
    title: `Diagnostic ${dateLabel}`,
    summary: initialSummary,
    status: "open",
    createdAt: now,
    updatedAt: now,
  });
  const chatRef = await addDoc(collection(db, "chats"), {
    userId: user.value.uid,
    diagnosticId: diagnosticRef.id,
    carId: selectedCar.value.id,
    status: "open",
    phase: "intake_questions",
    awaitingResponse: true,
    tokensReceived: 0,
    createdAt: now,
    updatedAt: now,
  });
  diagnosticId.value = diagnosticRef.id;
  chatId.value = chatRef.id;
  return { chatId: chatRef.id, diagnosticId: diagnosticRef.id };
};

const getChatAction = (phase, hasChat) => {
  if (!hasChat || !phase || phase === "intake_questions") {
    return {
      promptType: "intake",
      intakeStage: "initial",
      nextPhase: "intake_questions",
      functionName: "question_prompt",
    };
  }
  if (phase === "intake_answers") {
    return {
      promptType: "intake",
      intakeStage: "followup_answer",
      nextPhase: "diagnosis_pending",
      functionName: "fanout_diagnosis",
    };
  }
  return {
    promptType: "normal",
    intakeStage: null,
    nextPhase: "normal",
    functionName: "chat_reply",
  };
};

const sendChatMessage = async () => {
  error.value = "";
  const trimmed = chatInput.value.trim();
  if (!trimmed) {
    error.value = "Please add a brief description.";
    return;
  }
  if (!user.value || !selectedCar.value) {
    error.value = "You must be signed in and select a car.";
    return;
  }
  if (isChatAwaiting.value) {
    return;
  }

  isChatSending.value = true;
  let activeChatId = chatId.value;
  try {
    if (!activeChatId) {
      const created = await createDiagnosticAndChat(trimmed);
      activeChatId = created.chatId;
    }

    const action = getChatAction(chatPhase.value, Boolean(chatId.value));
    const messageRef = await addDoc(collection(db, "chats", activeChatId, "messages"), {
      role: "user",
      promptType: action.promptType,
      content: trimmed,
      createdAt: Date.now(),
      source: "user",
      metadata: action.intakeStage ? { intakeStage: action.intakeStage } : {},
    });

    const chatUpdate = {
      awaitingResponse: true,
      latestMessageId: messageRef.id,
      updatedAt: Date.now(),
      phase: action.nextPhase,
      tokensReceived: 0,
    };
    if (action.intakeStage === "initial") {
      chatUpdate.firstPromptId = messageRef.id;
    }
    await updateDoc(doc(db, "chats", activeChatId), chatUpdate);

    chatInput.value = "";

    const callFunction = functionCalls[action.functionName];
    if (!callFunction) {
      throw new Error("Function is not configured.");
    }
    await callFunction({
      chatId: activeChatId,
      messageId: messageRef.id,
    });
  } catch (err) {
    error.value = err?.message || "Failed to send message.";
    if (activeChatId) {
      try {
        await updateDoc(doc(db, "chats", activeChatId), {
          awaitingResponse: false,
          updatedAt: Date.now(),
        });
      } catch (updateError) {
        console.error(updateError);
      }
    }
  } finally {
    isChatSending.value = false;
  }
};
// Diagnostic submission intentionally not wired yet.
</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Playfair+Display:wght@500&display=swap");

:root {
  color-scheme: light;
  --black: #111111;
  --black-soft: #1a1a1a;
  --white: #ffffff;
  --gray-50: #f7f7f7;
  --gray-100: #f0f0f0;
  --gray-150: #e9e9e9;
  --gray-200: #e2e2e2;
  --gray-300: #d5d5d5;
  --gray-400: #bdbdbd;
  --gray-500: #9c9c9c;
  --gray-600: #7a7a7a;
  --gray-700: #5c5c5c;
  --gray-800: #3b3b3b;
  --border: #d5d5d5;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
  background: radial-gradient(circle at top, #f7f7f7 0%, #eeeeee 55%, #e4e4e4 100%);
  color: var(--black);
}

.app {
  min-height: 100vh;
  padding: 32px 6vw 80px;
  display: flex;
  flex-direction: column;
  gap: 80px;
}

.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.brand-mark {
  font-size: 1.3rem;
}

.brand-sub {
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--gray-600);
}

.nav-links {
  display: flex;
  gap: 20px;
  font-weight: 500;
}

.nav-links a {
  text-decoration: none;
  color: var(--black);
}

.nav-actions {
  display: flex;
  align-items: center;
}

.hero {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 48px;
  align-items: center;
}

.hero-left h1 {
  font-family: "Playfair Display", serif;
  font-size: clamp(2.3rem, 4vw, 3.4rem);
  margin: 12px 0 16px;
}

.lead {
  font-size: 1.05rem;
  max-width: 520px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.3em;
  font-size: 0.75rem;
  color: var(--gray-600);
  margin: 0;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 24px 0 8px;
}

.btn {
  border: none;
  border-radius: 999px;
  padding: 12px 22px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--black);
  color: var(--white);
  box-shadow: 0 14px 24px rgba(0, 0, 0, 0.25);
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--black);
  color: var(--black);
}

.btn-ghost {
  background: var(--white);
  border: 1px solid var(--gray-300);
  color: var(--black);
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.error {
  color: var(--gray-700);
  margin-top: 8px;
}

.user-pill {
  margin-top: 12px;
  padding: 8px 14px;
  background: var(--white);
  border-radius: 999px;
  display: inline-block;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.08);
}

.card {
  background: var(--black-soft);
  color: var(--gray-100);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 24px 40px rgba(0, 0, 0, 0.25);
}

.card h3 {
  margin: 18px 0 10px;
}

.card ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 8px;
}

.card li::before {
  content: "•";
  color: var(--gray-400);
  margin-right: 8px;
}

.card-header,
.card-footer {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--gray-400);
}

.status {
  color: var(--gray-300);
}

.section {
  display: grid;
  gap: 20px;
}

.section h2 {
  font-size: 2rem;
  margin: 0;
}

.section p {
  max-width: 680px;
}

.grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.tile {
  background: var(--white);
  padding: 20px;
  border-radius: 18px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
}

.alt .tile {
  background: var(--gray-50);
}

.dashboard {
  display: grid;
  gap: 24px;
}

.dashboard-header {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.dashboard h1 {
  margin: 0 0 6px;
  font-size: clamp(2rem, 4vw, 2.8rem);
}

.muted {
  color: var(--gray-600);
  margin: 0;
}

.dashboard-empty {
  background: var(--white);
  padding: 36px;
  border-radius: 24px;
  text-align: center;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.08);
}

.cars-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
}

.car-card {
  position: relative;
  background: var(--white);
  padding: 20px;
  border-radius: 18px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
  display: grid;
  gap: 12px;
}

.car-card-delete {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid var(--gray-300);
  background: var(--white);
  color: var(--gray-700);
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: transform 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.car-card-delete:hover {
  transform: translateY(-1px);
  border-color: var(--black);
  color: var(--black);
}

.car-card-delete:focus-visible {
  outline: 2px solid var(--black);
  outline-offset: 2px;
}

.car-card-delete svg {
  width: 16px;
  height: 16px;
}

.car-card-action {
  border: none;
  text-align: left;
  cursor: pointer;
  width: 100%;
  font: inherit;
  appearance: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.car-card-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 30px rgba(0, 0, 0, 0.12);
}

.car-card-action:focus-visible {
  outline: 2px solid var(--black);
  outline-offset: 2px;
}

.card-cta {
  color: var(--black);
  font-weight: 600;
  font-size: 0.95rem;
}

.dashboard-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.field textarea {
  border-radius: 12px;
  border: 1px solid var(--gray-300);
  padding: 10px 12px;
  font-size: 1rem;
  resize: vertical;
}

.chat-board {
  display: grid;
  gap: 24px;
}

.chat-shell {
  background: var(--white);
  border-radius: 24px;
  padding: 24px;
  box-shadow: 0 16px 30px rgba(0, 0, 0, 0.08);
  display: grid;
  gap: 20px;
}

.chat-history {
  display: grid;
  gap: 12px;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 6px;
}

.chat-empty {
  background: var(--gray-50);
  border-radius: 16px;
  padding: 16px 18px;
  color: var(--gray-600);
}

.chat-message {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 16px;
  background: var(--gray-100);
}

.chat-content {
  margin: 0;
  white-space: pre-wrap;
}

.structured-output {
  display: grid;
  gap: 12px;
  background: var(--white);
  border-radius: 14px;
  padding: 12px;
  box-shadow: inset 0 0 0 1px rgba(28, 28, 28, 0.08);
}

.structured-title {
  margin: 0;
  font-weight: 700;
  text-align: center;
  font-size: 1.05rem;
  color: var(--black);
}

.structured-row,
.structured-block {
  display: grid;
  gap: 6px;
}

.structured-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gray-600);
}

.structured-value {
  margin: 0;
  font-weight: 600;
  color: var(--black);
}

.structured-list {
  margin: 0;
  padding-left: 18px;
  list-style: disc;
  color: var(--black);
  display: grid;
  gap: 6px;
}

.structured-empty {
  margin: 0;
  color: var(--gray-600);
  font-size: 0.9rem;
}

.question-form {
  display: grid;
  gap: 16px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid var(--border);
  background: var(--gray-50);
}

.question-field {
  display: grid;
  gap: 8px;
}

.question-label {
  font-weight: 600;
  color: var(--black);
}

.question-form textarea {
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 10px 12px;
  font-size: 1rem;
  resize: vertical;
}

.answer-output {
  display: grid;
  gap: 8px;
}

.answer-list {
  margin: 0;
  padding-left: 20px;
  color: var(--black);
  display: grid;
  gap: 10px;
}

.answer-question {
  margin: 0 0 4px;
  font-weight: 600;
  color: var(--black);
}

.answer-value {
  margin: 0;
  color: var(--gray-700);
}

.chat-message.user {
  background: var(--gray-200);
  justify-self: end;
}

.chat-message.assistant {
  background: var(--gray-150);
  justify-self: start;
}

.chat-meta {
  margin: 0;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gray-600);
}

.chat-status {
  margin: 0;
  color: var(--gray-600);
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 10px;
}

.spinner {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid var(--gray-300);
  border-top-color: var(--black);
  animation: spin 0.8s linear infinite;
}

.token-count {
  font-weight: 600;
  color: var(--black);
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}


.chat-input-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: end;
}

.chat-input-row textarea {
  border-radius: 16px;
  border: 1px solid var(--gray-300);
  padding: 12px 14px;
  font-size: 1rem;
  resize: vertical;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: grid;
  place-items: center;
  padding: 24px;
  z-index: 50;
}

.modal {
  background: var(--white);
  border-radius: 24px;
  padding: 24px;
  width: min(520px, 100%);
  box-shadow: 0 30px 60px rgba(0, 0, 0, 0.25);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.icon-button {
  border: none;
  background: transparent;
  font-size: 1.5rem;
  cursor: pointer;
}

.modal-body {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}

.field {
  display: grid;
  gap: 6px;
  font-weight: 500;
}

.field input {
  border-radius: 12px;
  border: 1px solid var(--gray-300);
  padding: 10px 12px;
  font-size: 1rem;
}

.field-note {
  margin: 0;
  font-size: 0.9rem;
  color: var(--gray-600);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.floating-callout {
  position: fixed;
  right: 28px;
  bottom: 28px;
  width: min(320px, 90vw);
  background: var(--white);
  border: 1px solid var(--gray-300);
  border-radius: 18px;
  padding: 18px 20px;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.12);
  display: grid;
  gap: 8px;
  z-index: 20;
}

.callout-eyebrow {
  margin: 0;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.22em;
  color: var(--gray-600);
}

.floating-callout h4 {
  margin: 0;
  font-size: 1.1rem;
}

.floating-callout p {
  margin: 0;
  color: var(--gray-700);
  font-size: 0.95rem;
}

.callout-link {
  color: var(--black);
  font-weight: 600;
  text-decoration: none;
}

.callout-link:hover {
  text-decoration: underline;
}

@media (max-width: 840px) {
  .nav {
    flex-direction: column;
    align-items: flex-start;
  }

  .nav-links {
    flex-wrap: wrap;
  }

  .cars-grid {
    grid-template-columns: 1fr;
  }

  .floating-callout {
    position: static;
    width: 100%;
    max-width: 100%;
  }
}
</style>
