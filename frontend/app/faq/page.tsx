"use client";

/**
 * FAQ — the questions students, parents, and CAC judges actually ask.
 * Copy is translated through lib/i18n so the language selector reaches it.
 */

import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { SiteFooter } from "@/components/SiteFooter";
import { useLanguage } from "@/lib/i18n";

const KEYS = ["1", "2", "3", "4", "5", "6"] as const;

export default function FaqPage() {
  const { t } = useLanguage();

  return (
    <main className="flex min-h-screen flex-col px-6 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl flex-1">
        <AppNav
          right={
            <Link href="/" className="text-sm font-semibold text-aurora">
              {t("faq.back")}
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">{t("faq.eyebrow")}</p>
          <h1 className="h-display mt-3 text-4xl text-foreground">
            {t("faq.title")}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            {t("faq.intro")}
          </p>
        </header>

        <section className="mt-8 grid gap-4">
          {KEYS.map((key) => (
            <article key={key} className="rounded-lg border bg-card p-5">
              <h2 className="text-lg font-semibold text-foreground">
                {t(`faq.q${key}`)}
              </h2>
              <p className="mt-2 text-sm leading-7 text-muted-foreground">
                {t(`faq.a${key}`)}
              </p>
            </article>
          ))}
        </section>
      </div>
      <div className="mt-16">
        <SiteFooter />
      </div>
    </main>
  );
}
