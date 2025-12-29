import {
  signInWithPopup as firebaseSignInWithPopup,
  signOut as firebaseSignOut,
  onAuthStateChanged as firebaseOnAuthStateChanged,
} from "firebase/auth";

const useFakeAuth = process.env.VUE_APP_E2E_FAKE_AUTH === "1";
let fakeUser = null;
const listeners = new Set();

const notifyListeners = () => {
  listeners.forEach((callback) => callback(fakeUser));
};

export const signInWithPopup = async (authInstance, provider) => {
  if (!useFakeAuth) {
    return firebaseSignInWithPopup(authInstance, provider);
  }
  fakeUser = {
    uid: "e2e-user",
    displayName: "E2E User",
    email: "e2e@example.com",
  };
  notifyListeners();
  return { user: fakeUser };
};

export const signOut = async (authInstance) => {
  if (!useFakeAuth) {
    return firebaseSignOut(authInstance);
  }
  fakeUser = null;
  notifyListeners();
};

export const onAuthStateChanged = (authInstance, callback) => {
  if (!useFakeAuth) {
    return firebaseOnAuthStateChanged(authInstance, callback);
  }
  listeners.add(callback);
  callback(fakeUser);
  return () => listeners.delete(callback);
};
