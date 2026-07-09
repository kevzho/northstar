/**
 * Small, token-driven Meridian header used across the in-app routes. Kept
 * dependency-free (no icon library) so the shell works before any vendor
 * styling is added.
 */
import Link from "next/link";

type Props = {
  /** Optional back/out link relative to the site root. */
  backHref?: string;
  backLabel?: string;
  /** Right-aligned action, typically a primary CTA button. */
  actionHref?: string;
  actionLabel?: string;
};

export function PageHeader({
  backHref,
  backLabel,
  actionHref,
  actionLabel,
}: Props) {
  return (
    <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-4">
        <Link
          href="/"
          className="text-lg font-semibold tracking-tight text-[var(--northstar-dark)]"
        >
          Meridian
        </Link>
        {backHref && backLabel ? (
          <Link
            href={backHref}
            className="text-sm font-semibold text-[var(--northstar)]"
          >
            {backLabel}
          </Link>
        ) : null}
      </div>
      {actionHref && actionLabel ? (
        <Link
          href={actionHref}
          className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
        >
          {actionLabel}
        </Link>
      ) : null}
    </header>
  );
}
