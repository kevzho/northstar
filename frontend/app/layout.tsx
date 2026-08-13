import type { Metadata } from "next";
import {
  Instrument_Serif,
  Schibsted_Grotesk,
  Spline_Sans_Mono,
} from "next/font/google";
import "./globals.css";

/* Display face — the atlas voice. Single 400 weight; hierarchy comes from size. */
const atlas = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-atlas",
});

const body = Schibsted_Grotesk({
  subsets: ["latin"],
  variable: "--font-body",
});

/* Coordinates face — every score, count, and date reads like an instrument. */
const coords = Spline_Sans_Mono({
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
      className={`h-full antialiased ${atlas.variable} ${body.variable} ${coords.variable}`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
