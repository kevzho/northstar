"use client";

/**
 * Self-serve account deletion.
 *
 * /privacy told students to email a stranger their name in order to withdraw
 * their own assessment answers, with a note that a button was being built.
 * That is an honest answer at twenty users and a barrier at five hundred, and
 * these are minors.
 *
 * DELIBERATELY HARD TO DO BY ACCIDENT AND EASY TO DO ON PURPOSE. It is behind
 * a disclosure, then a typed confirmation of the account's own email. No
 * "are you sure?" dialog, a modal trains people to click through, where typing
 * your own address cannot be done without reading. The API enforces the same
 * check, so this is a real gate rather than a UI one.
 *
 * It says what goes, in full, before asking. A student deciding whether to
 * delete their account should not have to guess what that means.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { deleteAccount } from "@/lib/api";
import { supabase } from "@/lib/supabase";

const GOES: string[] = [
  "your profile, name, handle and email",
  "your assessment answers and the six trait scores built from them",
  "your matches, bookmarks, and anything you marked not-for-me",
  "your plan, your missions and any evidence you logged",
  "your friendships, team-up interest and public page",
];

export function DeleteAccountCard({ email }: { email: string | null }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const matches =
    email !== null &&
    typed.trim().toLowerCase() === email.trim().toLowerCase();

  async function remove() {
    setBusy(true);
    setError("");
    try {
      await deleteAccount(typed.trim());
    } catch (caught) {
      setBusy(false);
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not delete the account just now. Nothing was removed.",
      );
      return;
    }
    // The session now points at a user that does not exist; signing out keeps
    // the app from rendering a half-authenticated shell on the way to /.
    await supabase.auth.signOut().catch(() => {});
    router.push("/?deleted=1");
  }

  return (
    <section className="mt-8 rounded-lg border border-border bg-card p-5">
      <h2 className="text-note font-semibold text-foreground">Delete your account</h2>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Permanent, immediate, and it takes everything with it. There is no
        recovery and no grace period.
      </p>

      {!open ? (
        <Button
          variant="outline"
          onClick={() => setOpen(true)}
          className="mt-4 h-9 px-4 text-sm"
        >
          Delete my account
        </Button>
      ) : (
        <div className="mt-4">
          <p className="text-sm leading-6 text-foreground">This removes:</p>
          <ul className="mt-2 grid gap-1">
            {GOES.map((item) => (
              <li
                key={item}
                className="flex gap-2 text-xs leading-5 text-muted-foreground"
              >
                <span aria-hidden="true" className="text-aurora">
                  —
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">
            Nothing is kept for analytics. The catalog and the shelf are not
            yours and do not change.
          </p>

          <label
            htmlFor="confirm-delete"
            className="mt-4 block text-xs leading-5 text-foreground"
          >
            Type <span className="font-mono text-star">{email ?? "your email"}</span>{" "}
            to confirm.
          </label>
          <Input
            id="confirm-delete"
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            autoComplete="off"
            spellCheck={false}
            placeholder={email ?? "your email"}
            className="mt-1.5 h-10 max-w-sm bg-panel-raised px-3 text-sm"
          />

          <div className="mt-4 flex flex-wrap gap-3">
            <Button
              onClick={remove}
              disabled={!matches || busy}
              className="h-10 px-4 font-semibold"
            >
              {busy ? "Deleting…" : "Delete permanently"}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                setOpen(false);
                setTyped("");
                setError("");
              }}
              disabled={busy}
              className="h-10 px-4"
            >
              Keep my account
            </Button>
          </div>

          {error ? (
            <p aria-live="polite" className="mt-3 text-note leading-6 text-foreground">
              {error}
            </p>
          ) : null}
        </div>
      )}
    </section>
  );
}
