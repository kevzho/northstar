"use client";

/**
 * Sharing controls, rendered on the profile page: claim a handle, flip
 * the public toggle, copy the link. State loads from /me; signed-out
 * students see nothing (sharing is meaningless without a record).
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { authedFetch, updateSharing } from "@/lib/api";

export function SharingCard() {
  const [loaded, setLoaded] = useState(false);
  const [handle, setHandle] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const me = await (await authedFetch("/me")).json();
        if (!mounted) return;
        setHandle(me.handle ?? "");
        setIsPublic(Boolean(me.public_profile));
        setLoaded(true);
      } catch {
        // Signed out — the card simply doesn't render.
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  if (!loaded) return null;

  async function save(next: { handle?: string; public_profile?: boolean }) {
    setSaving(true);
    setNote(null);
    try {
      const result = await updateSharing(next);
      setHandle(result.handle ?? "");
      setIsPublic(result.public_profile);
      setNote("Saved.");
    } catch (error) {
      setNote(
        error instanceof Error && error.message.includes("409")
          ? "That handle is taken — try another."
          : "Could not save — handles are 3-20 lowercase letters, digits, or dashes.",
      );
    } finally {
      setSaving(false);
    }
  }

  const url =
    typeof window !== "undefined" && handle
      ? `${window.location.origin}/p/${handle}`
      : null;

  return (
    <section className="rounded-lg border bg-card mt-8 p-5">
      <h2 className="text-note font-semibold text-foreground">
        Share your record
      </h2>
      <p className="mt-1 text-xs leading-5 text-muted-foreground">
        Off by default. Public shows highlights only — your first name, trait
        and field shape, the path you charted, any social links you added,
        your missions and your positive outcomes. Not your email, grade, or
        goal statement. Turning it on also lists you in Discover and Team Up.
      </p>
      <div className="mt-4 flex flex-col gap-2 sm:flex-row">
        <Input
          value={handle}
          onChange={(event) => setHandle(event.target.value.toLowerCase())}
          placeholder="pick-a-handle"
          className="h-10 flex-1 bg-panel-raised px-3 font-mono text-sm"
        />
        <Button
          variant="outline"
          onClick={() => save({ handle })}
          disabled={saving}
          className="h-10 shrink-0 px-4"
        >
          Save handle
        </Button>
        <Button
          onClick={() => save({ public_profile: !isPublic })}
          disabled={saving || !handle}
          className="h-10 shrink-0 px-4"
        >
          {isPublic ? "Make private" : "Go public"}
        </Button>
      </div>
      {url && isPublic ? (
        <p className="mt-3 font-mono text-xs text-star">
          Live at {url}{" "}
          <button
            type="button"
            className="underline underline-offset-2"
            onClick={() => navigator.clipboard?.writeText(url)}
          >
            copy
          </button>
        </p>
      ) : null}
      {note ? (
        <p className="mt-2 text-xs text-muted-foreground">{note}</p>
      ) : null}
    </section>
  );
}
