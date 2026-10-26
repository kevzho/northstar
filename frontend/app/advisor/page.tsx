"use client";

/**
 * Route advisor — exploration, not ranking.
 *
 * A single grounded exchange: the student asks about unusual or
 * interdisciplinary directions, the backend answers using only their
 * profile and their verified matched opportunities as sources, and every
 * response shows the "backed by" list. The deterministic engine keeps
 * sole authority over scores; this page is deliberately score-free.
 *
 * When LLM_API_KEY is unset the backend 503s and this page says the
 * feature is off — never a broken spinner.
 */

import { useState } from "react";
import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { parseBlocks } from "@/lib/plain-text";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { askAdvisor, isApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/use-require-auth";

type Exchange = Awaited<ReturnType<typeof askAdvisor>>;

const SUGGESTED = [
  "What unusual routes fit how I actually think?",
  "How could I combine my top two fields into one direction?",
  "What would a non-obvious college major look like for me?",
];

export default function AdvisorPage() {
  // Every question here goes to POST /advisor, which is auth-gated and
  // metered per student. Signed out a student could type a whole question and
  // get a 401 for it.
  useRequireAuth();
  const [question, setQuestion] = useState("");
  const [exchange, setExchange] = useState<Exchange | null>(null);
  const [state, setState] = useState<
    "idle" | "asking" | "off" | "failed" | "limited"
  >("idle");
  // The server words its own refusal (which cap, when it resets), so the UI
  // shows that rather than guessing at a generic "slow down" message.
  const [limitReason, setLimitReason] = useState("");

  async function ask(text: string) {
    if (!text.trim()) return;
    setState("asking");
    setExchange(null);
    try {
      const result = await askAdvisor(text.trim());
      setExchange(result);
      setState("idle");
    } catch (error) {
      if (isApiError(error) && error.status === 503) {
        setState("off");
      } else if (isApiError(error) && error.status === 429) {
        setLimitReason(error.detail);
        setState("limited");
      } else {
        setState("failed");
      }
    }
  }

  return (
    <main className="bleed-root min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-3xl">
        <AppNav
          homeHref="/dashboard"
          right={
            <Link
              href="/dashboard"
              className="text-sm font-semibold text-aurora"
            >
              Back to dashboard
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">Exploration, not prediction</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            Route advisor
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            Ask about unusual directions, hybrid fields, or college majors the
            rankings can&apos;t see. Answers are grounded in your profile and
            your verified matches — the sources are always shown, and this
            page never scores or predicts.
          </p>
        </header>

        <section className="mt-8">
          <Textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. I like debate and biology — what routes combine them?"
            className="min-h-24 bg-panel-raised p-4 text-base"
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Button
              onClick={() => ask(question)}
              disabled={state === "asking" || !question.trim()}
              className="h-11 px-5"
            >
              {state === "asking" ? "Thinking..." : "Ask"}
            </Button>
            {SUGGESTED.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => {
                  setQuestion(suggestion);
                  void ask(suggestion);
                }}
                className="border border-border px-3 py-2 text-xs text-muted-foreground transition hover:border-foreground hover:text-foreground"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </section>

        {state === "off" ? (
          <section className="rounded-lg border bg-card mt-8 p-6">
            <p className="text-sm leading-6 text-muted-foreground">
              The advisor is not configured yet — it needs an LLM key on the
              backend (<span className="font-mono text-xs">LLM_API_KEY</span>{" "}
              in <span className="font-mono text-xs">backend/.env</span>).
              Everything else on Northstar works without it.
            </p>
          </section>
        ) : state === "limited" ? (
          <section className="rounded-lg border border-star/40 bg-card mt-8 p-6">
            <p className="text-sm leading-6 text-foreground">
              {limitReason ||
                "You have reached the advisor's limit for now — try again later."}
            </p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Asking a question you have asked before is always free, and the
              rest of Northstar is unaffected.
            </p>
          </section>
        ) : state === "failed" ? (
          <section className="rounded-lg border border-destructive/40 bg-card mt-8 p-6">
            <p className="text-sm leading-6 text-muted-foreground">
              The advisor call failed — sign in first, or try again in a
              moment.
            </p>
          </section>
        ) : exchange ? (
          <section className="rounded-lg border bg-card mt-8 p-6">
            {/* Parsed, not pre-wrapped. The model writes the occasional bold
                run or bullet however firmly the prompt asks it not to, and
                whitespace-pre-wrap put the asterisks on screen. Elements are
                built from parsed spans, so nothing here can emit markup. */}
            <div className="grid gap-4 text-base leading-7 text-foreground">
              {parseBlocks(exchange.answer).map((block, index) =>
                block.kind === "list" ? (
                  <ul key={index} className="grid gap-2 pl-1">
                    {block.items.map((item, i) => (
                      <li key={i} className="flex gap-2">
                        <span aria-hidden="true" className="text-aurora">
                          &mdash;
                        </span>
                        <span>
                          {item.map((span, j) =>
                            span.bold ? (
                              <strong key={j} className="font-semibold">
                                {span.text}
                              </strong>
                            ) : (
                              <span key={j}>{span.text}</span>
                            ),
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p key={index}>
                    {block.spans.map((span, j) =>
                      span.bold ? (
                        <strong key={j} className="font-semibold">
                          {span.text}
                        </strong>
                      ) : (
                        <span key={j}>{span.text}</span>
                      ),
                    )}
                  </p>
                ),
              )}
            </div>
            {exchange.sources.length > 0 ? (
              <div className="mt-6 border-t border-border pt-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Backed by your verified matches
                </p>
                <ul className="mt-2 grid gap-1">
                  {exchange.sources.map((source) => (
                    <li key={source.n} className="text-sm">
                      <span className="font-mono text-xs text-aurora">
                        [{source.n}]
                      </span>{" "}
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-semibold text-star underline-offset-4 hover:underline"
                      >
                        {source.title}
                      </a>{" "}
                      <span className="text-xs text-muted-foreground">
                        {source.field} · {source.type}
                        {source.deadline ? ` · due ${source.deadline}` : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        ) : null}
      </div>
    </main>
  );
}
