/**
 * The one in-app nav row: wordmark left, page actions + theme toggle right.
 * Every route renders this instead of hand-rolling its own header, so nav
 * spacing, the toggle, and future nav items change in exactly one place.
 */
import Link from "next/link";
import { StarGlyph } from "@/components/decor/star-glyph";
import { ThemeToggle } from "@/components/theme-toggle";

export function AppNav({
  homeHref = "/",
  right,
}: {
  /** Where the wordmark links; in-app pages usually point at /dashboard. */
  homeHref?: string;
  /** Page-specific actions rendered left of the theme toggle. */
  right?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-5">
      <Link
        href={homeHref}
        className="flex items-center gap-2 text-foreground"
      >
        <StarGlyph className="h-3.5 w-3.5 text-star" />
        <span className="h-display text-xl">Northstar</span>
      </Link>
      <div className="flex items-center gap-3">
        {right}
        <ThemeToggle />
      </div>
    </div>
  );
}
