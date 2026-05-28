"use client";

import { getApp, getApps, initializeApp, type FirebaseOptions } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type Auth,
  type User,
} from "firebase/auth";

let configPromise: Promise<FirebaseOptions> | null = null;

export async function adminAuth() {
  const app = getApps().length ? getApp() : initializeApp(await firebaseConfig());
  return getAuth(app);
}

export async function signInWithGoogle() {
  const auth = await adminAuth();
  const provider = new GoogleAuthProvider();
  provider.setCustomParameters({ prompt: "select_account" });
  return signInWithPopup(auth, provider);
}

export async function signOutAdmin() {
  return signOut(await adminAuth());
}

export function observeAdminAuth(auth: Auth, callback: (user: User | null) => void) {
  return onAuthStateChanged(auth, callback);
}

export async function authHeader(user: User): Promise<HeadersInit> {
  return { authorization: `Bearer ${await user.getIdToken()}` };
}

async function firebaseConfig(): Promise<FirebaseOptions> {
  configPromise ??= fetch("/api/firebase-config", { cache: "no-store" }).then(async (response) => {
    if (!response.ok) {
      throw new Error("Failed to load Firebase config");
    }
    return (await response.json()) as FirebaseOptions;
  });
  return configPromise;
}
