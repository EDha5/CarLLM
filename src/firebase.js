import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, connectAuthEmulator } from "firebase/auth";
import { getFirestore, connectFirestoreEmulator } from "firebase/firestore";
import { getFunctions, connectFunctionsEmulator } from "firebase/functions";

const firebaseConfig = {
  apiKey: "AIzaSyCMuaSaSiJCTnmeLUbv_k6n-sf54N13-vQ",
  authDomain: "carllm-de234.firebaseapp.com",
  projectId: "carllm-de234",
  storageBucket: "carllm-de234.firebasestorage.app",
  messagingSenderId: "174750378350",
  appId: "1:174750378350:web:ad2d5cf1f58c4e3aeb797f",
  measurementId: "G-W7TEPX9RHK",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const functionsTarget =
  process.env.VUE_APP_FUNCTIONS_ORIGIN ||
  (typeof window !== "undefined" && window.location.hostname.endsWith("carllm.ai")
    ? window.location.origin
    : "us-central1");
const functions = getFunctions(app, functionsTarget);
const googleProvider = new GoogleAuthProvider();

if (process.env.NODE_ENV === "development" && typeof window !== "undefined") {
  if (window.location.hostname === "localhost") {
    connectAuthEmulator(auth, "http://localhost:9099", { disableWarnings: true });
    connectFirestoreEmulator(db, "localhost", 8080);
    connectFunctionsEmulator(functions, "localhost", 5001);
  }
}

export { auth, db, functions, googleProvider };
