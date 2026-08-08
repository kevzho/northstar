"use client";

/**
 * React binding for the stored assessment answers.
 *
 * localStorage is an external store, so this reads it through
 * `useSyncExternalStore` rather than a mount effect that calls setState. That
 * keeps the pages free of the cascading-render pattern the project's lint rules
 * reject, and it means every page showing trait data re-renders the moment an
 * answer changes — in this tab via `writeAnswers`, in another tab via the
 * browser's `storage` event.
 */

import { useMemo, useSyncExternalStore } from "react";
import {
  STORAGE_KEY,
  parseAnswers,
  type AssessmentAnswers,
} from "./scoring";

const listeners = new Set<() => void>();

function notify() {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  // `storage` only fires for *other* tabs; same-tab writes go through notify().
  window.addEventListener("storage", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}

/**
 * Snapshot is the raw string, not a parsed object: useSyncExternalStore
 * compares snapshots with Object.is, and a fresh object every read would loop
 * forever. Strings compare by value, so an unchanged store is a stable read.
 */
function getSnapshot(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function getServerSnapshot(): string | null {
  return null;
}

/** Persist answers and wake every hook subscriber in this tab. */
export function writeAnswers(answers: AssessmentAnswers): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(answers));
  } catch {
    // Private browsing or a full quota — the in-memory value still updates.
  }
  notify();
}

/** Remove any stored answers and wake subscribers. */
export function resetAnswers(): void {
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to do — a failed clear leaves the previous answers in place.
  }
  notify();
}

/**
 * Stored answers, or null when the student has not taken the assessment.
 * Always null on the server render, so the first paint matches the HTML.
 */
export function useStoredAnswers(): AssessmentAnswers | null {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return useMemo(() => parseAnswers(raw), [raw]);
}
