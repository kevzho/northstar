"use client";

/**
 * Bookmark toggle button for an opportunity.
 *
 * Checks existing bookmarks on mount, then toggles via POST /bookmarks or
 * DELETE /bookmarks/:id. Renders a filled label when bookmarked, an outline
 * label when not. Errors are swallowed so a network hiccup never bricks the
 * detail page, the student can retry on the next visit.
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { fetchBookmarks, bookmarkOpportunity, removeBookmark } from "@/lib/api";

export function BookmarkButton({ opportunityId }: { opportunityId: string }) {
  const [bookmarked, setBookmarked] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchBookmarks();
        if (!cancelled) {
          setBookmarked(list.some((b) => b.opportunity_id === opportunityId));
        }
      } catch {
        // Network error, default to un-bookmarked; user can still toggle.
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [opportunityId]);

  async function toggle() {
    if (loading) return;
    const was = bookmarked;
    setBookmarked(!was); // optimistic flip
    try {
      if (was) {
        await removeBookmark(opportunityId);
      } else {
        await bookmarkOpportunity(opportunityId);
      }
    } catch {
      setBookmarked(was); // revert on failure
    }
  }

  return (
    <Button
      variant={bookmarked ? "default" : "outline"}
      onClick={toggle}
      disabled={loading}
      className="h-12 px-6 text-sm font-semibold"
    >
      {loading ? "..." : bookmarked ? "Bookmarked" : "Bookmark"}
    </Button>
  );
}
