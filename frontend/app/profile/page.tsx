import Link from "next/link";
import { traitLabels, type TraitKey } from "@/lib/assessment";

const sampleScores: Record<TraitKey, number> = {
  builder: 82,
  analyst: 74,
  riskTolerance: 61,
  ambiguityComfort: 78,
  collaboration: 68,
  executionTempo: 85,
};

export default function ProfilePage() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-col gap-4 border-b border-[var(--border)] pb-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link
              href="/assessment"
              className="text-sm font-semibold text-[var(--northstar)]"
            >
              Back to assessment
            </Link>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-[var(--northstar-dark)]">
              Trait Profile
            </h1>
            <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--muted)]">
              This preview shows the six interpretable signals Northstar will
              compute from assessment choices.
            </p>
          </div>
          <Link
            href="/futures"
            className="inline-flex h-11 items-center justify-center rounded-md bg-[var(--northstar)] px-5 text-sm font-semibold text-white transition hover:bg-[var(--northstar-dark)]"
          >
            Generate futures
          </Link>
        </header>

        <section className="mt-8 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-5 shadow-sm">
          <div className="grid gap-5">
            {(Object.keys(sampleScores) as TraitKey[]).map((trait) => (
              <div key={trait}>
                <div className="mb-2 flex items-center justify-between gap-4">
                  <span className="text-sm font-semibold text-[var(--foreground)]">
                    {traitLabels[trait]}
                  </span>
                  <span className="text-sm text-[var(--muted)]">
                    {sampleScores[trait]}/100
                  </span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-[#e6e1d8]">
                  <div
                    className="h-full rounded-full bg-[var(--northstar)]"
                    style={{ width: `${sampleScores[trait]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
