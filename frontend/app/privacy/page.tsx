"use client";

/**
 * The document the onboarding consent checkbox points at.
 *
 * It used to point at "the the IRB-style data policy for this project,"
 * which existed in no file. Every statement below is checked against the
 * code rather than aspirational: the field list is the `students` table,
 * the processor list is the four services the app actually calls, and the
 * deletion section says what is true today (email request) rather than
 * describing a DELETE /me route that has not shipped yet.
 *
 * When that route lands, update the Deletion section and add a
 * consent_policy_version stamp so a stored consented_at can prove which
 * version of this page a student agreed to.
 */

import Link from "next/link";
import { AppNav } from "@/components/AppNav";
import { SiteFooter } from "@/components/SiteFooter";

const UPDATED = "21 September 2026";
const EMAIL = "dev.thorfinn@gmail.com";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-10">
      <h2 className="h-display text-section text-foreground">{title}</h2>
      <div className="mt-3 grid gap-3 text-sm leading-7 text-muted-foreground">
        {children}
      </div>
    </section>
  );
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen px-6 py-8 sm:px-8">
      <div className="mx-auto max-w-2xl">
        <AppNav />

        <h1 className="h-display mt-10 text-title text-foreground">
          Privacy policy
        </h1>
        <p className="mt-3 font-mono text-sm uppercase tracking-[0.16em] text-muted-foreground">
          Last updated {UPDATED}
        </p>
        <p className="mt-6 text-base leading-7 text-foreground">
          Northstar is built for high school students, so most of the people
          reading this are minors. This page says exactly what the app stores,
          who else sees it, and how to get it deleted. If something here is
          unclear, email{" "}
          <a href={`mailto:${EMAIL}`} className="underline underline-offset-2">
            {EMAIL}
          </a>
          .
        </p>

        <Section title="What we store">
          <p>When you create an account and complete onboarding:</p>
          <ul className="grid list-disc gap-1 pl-5">
            <li>Your name, email address, and grade level.</li>
            <li>The interests you select and the goal statement you write.</li>
            <li>
              Whether you are looking at high school or college opportunities,
              and your location preference.
            </li>
            <li>
              Your assessment results — six behavioral trait scores and a
              field-interest map. The individual answers stay in your browser
              and are not sent to us.
            </li>
            <li>
              What you do in the app: opportunities you bookmark, dismiss, or
              log an outcome for, and missions you complete.
            </li>
            <li>
              If you turn on a public profile: a handle you choose, and any
              social links you add.
            </li>
            <li>
              If you use Team Up or add friends: who you are connected to, and
              any reports or blocks you create.
            </li>
            <li>
              If you use the Advisor: the questions you ask and the answers you
              get. These are kept so that re-asking a question is free rather
              than costing another model call.
            </li>
          </ul>
          <p>
            We do not store your password — sign-in goes through Google or a
            one-time email link. We do not use advertising trackers, and there
            is no analytics vendor on this site.
          </p>
        </Section>

        <Section title="Who else sees it">
          <ul className="grid list-disc gap-1 pl-5">
            <li>
              <strong className="text-foreground">Supabase</strong> stores the
              database and handles sign-in.
            </li>
            <li>
              <strong className="text-foreground">Vercel</strong> hosts the site
              and the API.
            </li>
            <li>
              <strong className="text-foreground">Sentry</strong> receives crash
              reports if the app breaks. These can include the page you were on.
            </li>
            <li>
              <strong className="text-foreground">NVIDIA</strong> (via its NIM
              model-hosting API) receives your
              question, your trait scores, your field-interest shares, your
              stated interests, your goal statement in your own words, and the
              titles of opportunities matched to you — but only when you use the
              Advisor page. If you never open it, nothing is sent.
            </li>
          </ul>
          <p>
            We do not sell your data, and we do not share it with schools,
            colleges, or the programs listed in the catalog.
          </p>
        </Section>

        <Section title="What is public">
          <p>
            Nothing, unless you turn it on. Public profiles are off by default.
            Turning yours on does two things: it lists you in other students&apos;
            Discover and Team Up feeds inside Northstar, and it makes your record
            readable by link outside it. Anyone with the link to{" "}
            <span className="font-mono">/p/your-handle</span> can see your first
            name, your trait and field scores, your chosen path, your social
            links, and the missions and positive outcomes you logged. Your
            email, full name, grade, and goal statement are never on that page.
          </p>
          <p>
            We ask search engines not to index these pages, and send a{" "}
            <span className="font-mono">noindex</span> directive with every one.
            You can turn your public profile off at any time from your profile
            page.
          </p>
        </Section>

        <Section title="Deleting your data">
          <p>
            Email{" "}
            <a
              href="/profile#confirm-delete"
              className="underline underline-offset-2"
            >
              Delete your account from your profile page
            </a>
            . It is immediate and permanent: the profile, your assessment
            answers and the six trait scores built from them, matches,
            bookmarks, dismissals, outcomes, missions, friendships, team-up
            interest and your public page all go at once. Nothing is kept
            afterwards and nothing is held back for analytics.
          </p>
          <p>
            You will be asked to type the email address on your account to
            confirm, because it is the one thing here that cannot be undone.
          </p>
          <p>
            If the button will not work for you, email{" "}
            <a
              href={`mailto:${EMAIL}?subject=Delete%20my%20Northstar%20data`}
              className="underline underline-offset-2"
            >
              {EMAIL}
            </a>{" "}
            from the address on your account and it will be done by hand.
          </p>
        </Section>

        <Section title="If you are under 13">
          <p>
            Northstar is built for high school students, and also has a college
            track you can pick during onboarding. Either way, please do not
            create an account if you are under 13. If we learn that an account
            belongs to someone under 13, we delete it.
          </p>
        </Section>

        <Section title="Changes">
          <p>
            If this policy changes in a way that affects what we collect, the
            date at the top changes. There is no automatic re-consent prompt
            yet, so this page is the record — if the date above is newer than
            when you signed up, something here changed.
          </p>
        </Section>

        <div className="mt-12 border-t border-border pt-6">
          <Link
            href="/onboarding"
            className="text-sm font-semibold text-aurora underline underline-offset-4"
          >
            Back to onboarding
          </Link>
        </div>
      </div>
      <SiteFooter />
    </main>
  );
}
