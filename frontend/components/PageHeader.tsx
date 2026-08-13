/**
 * Small, token-driven Northstar header used across the in-app routes. Kept
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
        <Link href="/" className="h-display text-xl text-[var(--foreground)]">
          Northstar
        </Link>
        {backHref && backLabel ? (
          <Link
            href={backHref}
            className="text-sm font-semibold text-[var(--aurora)]"
          >
            {backLabel}
          </Link>
        ) : null}
      </div>
      {actionHref && actionLabel ? (
        <Link href={actionHref} className="btn-primary h-11 px-5">
          {actionLabel}
        </Link>
      ) : null}
    </header>
  );
}
