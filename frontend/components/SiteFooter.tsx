"use client";

/**
 * Shared site footer: Contact / FAQ links, a language selector, and the
 * byline. Rendered on the landing page and the marketing routes. The
 * language choice is global (lib/i18n) so switching here re-renders every
 * translated surface.
 */

import Link from "next/link";
import { StarGlyph } from "@/components/decor/star-glyph";
import { NativeSelect } from "@/components/ui/native-select";
import { LANGUAGES, useLanguage, type LanguageCode } from "@/lib/i18n";

export function SiteFooter() {
  const { lang, setLang, t } = useLanguage();

  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
        <div className="flex items-center gap-5">
          <p className="flex items-center gap-1.5 font-mono text-xs tracking-wide text-muted-foreground">
            <StarGlyph className="h-2.5 w-2.5" />
            Kevin Zhou © 2026
          </p>
          <Link
            href="/contact"
            className="text-sm text-muted-foreground transition hover:text-foreground"
          >
            {t("footer.contact")}
          </Link>
          <Link
            href="/faq"
            className="text-sm text-muted-foreground transition hover:text-foreground"
          >
            {t("footer.faq")}
          </Link>
        </div>
        <label className="flex items-center gap-2">
          <span className="sr-only">{t("footer.language")}</span>
          <NativeSelect
            aria-label={t("footer.language")}
            value={lang}
            onChange={(event) => setLang(event.target.value as LanguageCode)}
            className="h-9 px-3 text-sm"
          >
            {LANGUAGES.map((language) => (
              <option key={language.code} value={language.code}>
                {language.label}
              </option>
            ))}
          </NativeSelect>
        </label>
      </div>
    </footer>
  );
}
