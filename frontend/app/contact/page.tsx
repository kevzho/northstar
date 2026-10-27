"use client";

/**
 * Contact, a direct line to the maker, plus the opportunity-suggestion
 * ask (a cheap acquisition channel). Copy is translated through lib/i18n.
 */

import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { SiteFooter } from "@/components/SiteFooter";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/i18n";

const EMAIL = "dev.thorfinn@gmail.com";

export default function ContactPage() {
  const { t } = useLanguage();

  return (
    <main className="bleed-root flex min-h-screen flex-col px-6 py-8 sm:px-8">
      <div className="mx-auto w-full max-w-3xl flex-1">
        <AppNav
          right={
            <Link href="/" className="text-sm font-semibold text-aurora">
              {t("contact.back")}
            </Link>
          }
        />

        <header className="mt-10">
          <p className="eyebrow">{t("contact.eyebrow")}</p>
          <h1 className="h-display mt-3 text-title text-foreground">
            {t("contact.title")}
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted-foreground">
            {t("contact.intro")}
          </p>
        </header>

        <section className="rounded-lg border bg-card mt-8 p-6">
          <p className="text-sm font-semibold text-foreground">
            {t("contact.email")}
          </p>
          <a
            href={`mailto:${EMAIL}`}
            className="mt-1 block font-mono text-lg text-star underline-offset-4 hover:underline"
          >
            {EMAIL}
          </a>
          <p className="mt-2 text-xs leading-5 text-muted-foreground">
            {t("contact.response")}
          </p>
        </section>

        <section className="rounded-lg border bg-card mt-6 p-6">
          <h2 className="h-display text-section text-foreground">
            {t("contact.suggest")}
          </h2>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">
            {t("contact.suggestBody")}
          </p>
          <Button
            render={
              <a
                href={`mailto:${EMAIL}?subject=${encodeURIComponent(
                  "Opportunity suggestion for Northstar",
                )}`}
              />
            }
            className="mt-4 h-11 px-5"
          >
            {t("contact.suggest")}
          </Button>
        </section>
      </div>
      <div className="mt-16">
        <SiteFooter />
      </div>
    </main>
  );
}
