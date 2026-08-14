"use client";

/**
 * React binding for the chosen future path.
 *
 * Identical pattern to lib/use-assessment.ts: localStorage is an external
 * store read through `useSyncExternalStore`, so every subscriber re-renders
 * the moment the choice changes — in this tab via writeChosenPath, in another
 * tab via the browser's `storage` event.
 */

import { useMemo, useSyncExternalStore } from "react";
import {
  CHOSEN_PATH_KEY,
  parseChosenPath,
  type ChosenPath,
} from "./plan";

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

/** Snapshot is the raw string so unchanged reads stay referentially stable. */
function getSnapshot(): string | null {
  try {
    return window.localStorage.getItem(CHOSEN_PATH_KEY);
  } catch {
    return null;
  }
}

function getServerSnapshot(): string | null {
  return null;
}

/** Persist the chosen path and wake every hook subscriber in this tab. */
export function writeChosenPath(path: ChosenPath): void {
  try {
    window.localStorage.setItem(CHOSEN_PATH_KEY, JSON.stringify(path));
  } catch {
    // Private browsing or a full quota — the in-memory value still updates.
  }
  notify();
}

/** Clear the chosen path and wake subscribers. */
export function resetChosenPath(): void {
  try {
    window.localStorage.removeItem(CHOSEN_PATH_KEY);
  } catch {
    // Nothing to do — a failed clear leaves the previous choice in place.
  }
  notify();
}

/**
 * The chosen path, or null when the student has not charted one yet.
 * Always null on the server render, so the first paint matches the HTML.
 */
export function useChosenPath(): ChosenPath | null {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  return useMemo(() => parseChosenPath(raw), [raw]);
}
