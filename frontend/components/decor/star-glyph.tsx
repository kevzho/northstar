/**
 * The brand mark: a four-point star with a counter-star cut from its
 * center. Extracted from the landing page so AppNav and any future
 * surface can carry the same mark.
 */
export function StarGlyph({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      aria-hidden="true"
      className={className}
      fill="currentColor"
    >
      <path
        fillRule="evenodd"
        d="M50 0Q56 40 100 50 56 60 50 100 44 60 0 50 44 40 50 0ZM50 28Q54 46 72 50 54 54 50 72 46 54 28 50 46 46 50 28Z"
      />
    </svg>
  );
}
