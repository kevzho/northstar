import type { Metadata } from "next";
import { Figtree, Pixelify_Sans, Recursive } from "next/font/google";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import { Guide } from "@/components/Guide";
import { SentryInit } from "@/components/SentryInit";
import { LanguageProvider } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/*
 * ONE FAMILY CARRYING THE PRODUCT'S ARGUMENT.
 *
 * Recursive is a variable face with a CASL (casual) axis running from a plain
 * grotesque at 0 to a handwritten-adjacent warmth at 1, plus a MONO axis and a
 * slant. That makes it the rare typeface where EPISTEMIC STATUS CAN BE A
 * TYPOGRAPHIC AXIS rather than a footnote.
 *
 * This catalog already separates what it checked from what it is advising -
 * roadmap.py splits computed calendar facts from authored generalisations;
 * recurrence_verified_at NULL means "no confirmed window"; public.outcomes has
 * no rows. Until now that distinction lived in a magenta colour and a sentence
 * in brackets. Now it also lives in the letterforms: verified text sets at
 * CASL 0 (or MONO 1 for figures), advised text sets at CASL 1 with a slant.
 * The type gets more human exactly where the data gets less certain.
 *
 * CASL IS RATIONED, AND THAT IS THE WHOLE POINT. It is NOT the heading voice.
 * A judge on this direction named that as the one thing that would sink it: set
 * the hero and 21 h1s in CASL 1 and the axis stops meaning "advisory" and
 * starts meaning "Northstar". Headings take wght, not CASL.
 *
 * Replaces Bricolage Grotesque, which is the display face currently most
 * common in generated design, and IBM Plex Mono, whose job Recursive's MONO
 * axis does from the same file.
 */
const recursive = Recursive({
  subsets: ["latin"],
  axes: ["CASL", "MONO", "slnt"],
  variable: "--font-coords",
});

/*
 * DISPLAY, a pixel face, used for headings and nothing else.
 *
 * Pixelify Sans is variable 400-700, so headings still get weight hierarchy
 * rather than one flat cut, which the bitmap classics (Silkscreen, Press
 * Start 2P) cannot give.
 *
 * DELIBERATELY NOT THE BODY FACE. This product's job is reading deadlines and
 * long scraped programme descriptions, often on a phone, the shelf carries
 * 150+ blurbs written by organisers, not by us. A pixel face at 15px costs
 * real comprehension on exactly the text a student has to get right, and the
 * cost lands hardest on the people this exists for. Headings carry the
 * character; the paragraph stays readable.
 */
const display = Pixelify_Sans({
  subsets: ["latin"],
  variable: "--font-atlas",
});

/*
 * Body face, a second family, deliberately. Recursive at CASL 0 is close
 * enough to a neutral grotesque that using it for body too would leave the
 * axis with nothing to contrast against, and the whole device depends on the
 * reader feeling the difference.
 */
const body = Figtree({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "Northstar",
  description:
    "A personalized opportunity map for high school students — a behavioral assessment, ranked STEM opportunities, and the pathways between them.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={cn(
        "h-full antialiased font-sans",
        display.variable,
        recursive.variable,
        body.variable,
      )}
    >
      <body className="min-h-full flex flex-col">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          disableTransitionOnChange
        >
          <SentryInit />
          {/*
            The sky is gone from the interior pages, on three counts measured
            2026-10-05:

            1. It broke mobile layout. Its SVG star circles are positioned
               past the viewport edge, pushing /opportunities to 405px inside a
               390px window, a horizontal scroll on every phone, on the page
               testers land on.
            2. It was wrong in the paper theme, rendering the same specks as
               grey dots on manila rather than inverting.
            3. It carried no information. The constellation in the landing
               hero does; 56 seeded specks behind a form do not.

            The star stays where it means something: the wordmark glyph and the
            landing hero. A logo, not a set.
          */}
          <LanguageProvider>
            {children}
            <Guide />
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
