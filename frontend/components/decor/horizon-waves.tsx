/**
 * Layered horizon waves in the haikei style, three stacked organic bands
 * fading toward the footer. Generated once from a seeded script (seed
 * 20261103, scripts run via node; see the commit that added this file), so
 * the curves are unique to Northstar rather than a stock asset. Decorative
 * only; hidden from assistive tech.
 */
export function HorizonWaves({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 1440 220"
      preserveAspectRatio="none"
      aria-hidden="true"
      className={className}
    >
      <path
        fill="currentColor"
        opacity="0.05"
        d="M0 220 L0 52.5 C144.0 52.5 144.0 73.1 288.0 73.1 C432.0 73.1 432.0 89.0 576.0 89.0 C720.0 89.0 720.0 69.4 864.0 69.4 C1008.0 69.4 1008.0 68.4 1152.0 68.4 C1296.0 68.4 1296.0 95.2 1440.0 95.2 L1440 220 Z"
      />
      <path
        fill="currentColor"
        opacity="0.07"
        d="M0 220 L0 83.7 C120.0 83.7 120.0 124.1 240.0 124.1 C360.0 124.1 360.0 106.4 480.0 106.4 C600.0 106.4 600.0 109.7 720.0 109.7 C840.0 109.7 840.0 134.2 960.0 134.2 C1080.0 134.2 1080.0 81.2 1200.0 81.2 C1320.0 81.2 1320.0 105.9 1440.0 105.9 L1440 220 Z"
      />
      <path
        fill="currentColor"
        opacity="0.1"
        d="M0 220 L0 165.1 C102.9 165.1 102.9 136.0 205.7 136.0 C308.6 136.0 308.6 163.1 411.4 163.1 C514.3 163.1 514.3 130.6 617.1 130.6 C720.0 130.6 720.0 173.0 822.9 173.0 C925.7 173.0 925.7 148.5 1028.6 148.5 C1131.4 148.5 1131.4 155.6 1234.3 155.6 C1337.1 155.6 1337.1 148.0 1440.0 148.0 L1440 220 Z"
      />
    </svg>
  );
}
