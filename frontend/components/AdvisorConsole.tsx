"use client";

/**
 * Route advisor, as a thing you type into rather than a place you go.
 *
 * WHY THIS IS A COMPONENT AND NOT A PAGE. Asking "what else could I do with
 * this?" is a question about the page you are looking at. Sending someone to
 * /advisor to ask it meant leaving the thing they wanted to ask about, and the
 * advisor then had no idea what they had been reading. So the console lives in
 * the corner guide, open beside the page, and /advisor renders the same
 * component so the two can never drift apart.
 *
 * WHAT IT IS NOT. It does not score, rank or predict, and it never invents an
 * opportunity: the backend answers from the student's own profile and their
 * already-verified matches, and every answer carries the list it drew on. The
 * deterministic matcher keeps sole authority over what ranks where. A chat box
 * that could quietly reorder a student's plan would make the rest of this
 * product's honesty decorative.
 */

import { useState } from "react";
import { StarGlyph } from "@/components/decor/star-glyph";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import Link from "next/link";
import { askAdvisor, isApiError } from "@/lib/api";
import { answerFromFaq, type FaqAnswer } from "@/lib/faq";
import { parseBlocks } from "@/lib/plain-text";

type Exchange = Awaited<ReturnType<typeof askAdvisor>>;

const SUGGESTED = [
  "Where do I see my plan?",
  "What unusual routes fit how I actually think?",
  "How could I combine my top two fields into one direction?",
];

/** Model prose -> elements. Never HTML: the model writes the occasional bold
 *  run however firmly the prompt asks it not to, and whitespace-pre-wrap put
 *  the raw asterisks on screen. Built from parsed spans so nothing here can
 *  emit markup. */
function Answer({ text }: { text: string }) {
  return (
    <div className="grid gap-3">
      {parseBlocks(text).map((block, index) =>
        block.kind === "list" ? (
          <ul key={index} className="grid gap-1.5 pl-1">
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
  );
}

export function AdvisorConsole({ compact = false }: { compact?: boolean }) {
  const [question, setQuestion] = useState("");
  const [exchange, setExchange] = useState<Exchange | null>(null);
  /**
   * A product question, answered from lib/faq.ts without a model call.
   *
   * Asked "where do I see my map?", the advisor answered from the only corpus
   * it has -- matched opportunities -- and said the student had no plan, then
   * recommended three summer programmes. Correct retrieval, wrong corpus. A
   * question about the website is answered by the website.
   */
  const [faq, setFaq] = useState<FaqAnswer | null>(null);
  const [state, setState] = useState<
    "idle" | "asking" | "off" | "failed" | "limited"
  >("idle");
  // The server words its own refusal -- which cap was hit, when it resets --
  // so the UI shows that instead of guessing at "slow down".
  const [limitReason, setLimitReason] = useState("");

  async function ask(text: string) {
    if (!text.trim()) return;
    setExchange(null);
    setFaq(null);

    // Free, instant, and cannot invent an opportunity. Only questions that
    // are plainly about the product get this far; anything else falls
    // through to the model untouched.
    const local = answerFromFaq(text);
    if (local) {
      setFaq(local);
      setState("idle");
      return;
    }

    setState("asking");
    try {
      setExchange(await askAdvisor(text.trim()));
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

  const text = compact ? "text-xs leading-5" : "text-base leading-7";

  return (
    <div className="grid gap-3">
      <Textarea
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={(event) => {
          // Enter sends, shift+Enter makes a newline -- the convention every
          // other message box uses. Without it the only way to ask is to
          // reach for the button, which in a 20rem panel is a long way.
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void ask(question);
          }
        }}
        placeholder="e.g. I like debate and biology — what routes combine them?"
        className={
          compact
            ? "min-h-16 bg-panel-raised p-3 text-xs"
            : "min-h-24 bg-panel-raised p-4 text-base"
        }
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button
          onClick={() => void ask(question)}
          disabled={state === "asking" || !question.trim()}
          className={compact ? "h-8 px-3 text-xs" : "h-11 px-5"}
        >
          {state === "asking" ? "Thinking…" : "Ask"}
        </Button>
        {(compact ? SUGGESTED.slice(0, 1) : SUGGESTED).map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => {
              setQuestion(suggestion);
              void ask(suggestion);
            }}
            className="border border-border px-2.5 py-1.5 text-left text-xs text-muted-foreground transition hover:border-foreground hover:text-foreground"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {state === "off" ? (
        <p className={`${text} text-muted-foreground`}>
          The advisor is not configured — it needs an LLM key on the backend.
          Everything else on Northstar works without it.
        </p>
      ) : state === "limited" ? (
        <p className={`${text} text-foreground`}>
          {limitReason ||
            "You have reached the advisor's limit for now — try again later."}
        </p>
      ) : state === "failed" ? (
        <p className={`${text} text-muted-foreground`}>
          That call failed — sign in first, or try again in a moment.
        </p>
      ) : faq ? (
        <div className="border-t border-border pt-3">
          <p className={`${text} text-foreground`}>{faq.answer}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {faq.links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="border border-border px-2.5 py-1.5 text-xs font-semibold text-foreground transition hover:border-foreground"
              >
                {link.label} &rarr;
              </Link>
            ))}
          </div>
          {/* Said plainly. A student who thinks a model answered will trust
              this differently from how they should, in both directions. */}
          <p className="mt-3 text-[0.65rem] leading-4 text-muted-foreground">
            Answered from the guide, not the model. Nothing was spent.
          </p>
        </div>
      ) : exchange ? (
        <div
          className={
            compact
              ? "max-h-72 overflow-y-auto border-t border-border pt-3"
              : "border-t border-border pt-4"
          }
        >
          <div className={`${text} text-foreground`}>
            <Answer text={exchange.answer} />
          </div>
          {exchange.sources.length > 0 ? (
            <div className="mt-4 border-t border-border pt-3">
              <p className="text-[0.65rem] font-semibold uppercase tracking-wider text-muted-foreground">
                Backed by your verified matches
              </p>
              <ul className="mt-2 grid gap-1">
                {exchange.sources.map((source) => (
                  <li key={source.n} className="text-xs">
                    <span className="font-mono text-[0.65rem] text-aurora">
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
                    <span className="text-muted-foreground">
                      {source.field} · {source.type}
                      {source.deadline ? ` · due ${source.deadline}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mt-3 text-xs leading-5 text-muted-foreground">
              No matched opportunity backed that one, so treat it as a
              suggestion rather than a route.
            </p>
          )}
        </div>
      ) : (
        <p className={`${text} text-muted-foreground`}>
          <StarGlyph className="mr-1 inline-block h-2 w-2 text-star" />
          Ask where something is and the guide answers. Ask about directions
          and the model does, from your profile and your verified matches,
          showing which ones it used. Neither ranks or predicts.
        </p>
      )}
    </div>
  );
}
