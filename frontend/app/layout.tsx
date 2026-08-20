import type { Metadata } from "next";
import {
  Bricolage_Grotesque,
  IBM_Plex_Mono,
  Onest,
} from "next/font/google";
import { ThemeProvider } from "next-themes";
import "./globals.css";
import { Guide } from "@/components/Guide";
import { SentryInit } from "@/components/SentryInit";
import { Sky } from "@/components/decor/sky";
import { LanguageProvider } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/* Display face — characterful grotesque for titles; hierarchy from size. */
const atlas = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-atlas",
});

/* Body face — clean, even, quiet next to the display. */
const body = Onest({
  subsets: ["latin"],
  variable: "--font-body",
});

/* Coordinates face — every score, count, and date reads like an instrument. */
const coords = IBM_Plex_Mono({
  weight: ["400", "500"],
  subsets: ["latin"],
  variable: "--font-coords",
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
        atlas.variable,
        body.variable,
        coords.variable,
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
          <Sky />
          <LanguageProvider>
            {children}
            <Guide />
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
