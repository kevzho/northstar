"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/use-auth";
import Link from "next/link";
import { MotionConfig, motion, useScroll, useTransform } from "motion/react";
import { useLanguage } from "@/lib/i18n";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { HorizonWaves } from "@/components/decor/horizon-waves";
import { AnimatedGroup } from "@/components/motion/animated-group";
import { InView } from "@/components/motion/in-view";
import { TextEffect } from "@/components/motion/text-effect";
import { Planet, Ship } from "@/components/decor/voyage";
import { DeadlineTicker, RecentlyAdded } from "@/components/CatalogSignals";
import { PILLAR_FIGURES } from "@/components/decor/pillar-diagrams";
import { StarGlyph } from "@/components/decor/star-glyph";
import { SiteFooter } from "@/components/SiteFooter";
import { SpriteSky } from "@/components/decor/sprite-sky";

/* three.js stays out of the initial bundle; the sky fades in after mount. */

const waypoints = [
  {
    mark: "01",
    planet: "moon" as const,
    title: "Trait profile",
    description:
      "Twenty prompts become six trait signals plus a field-interest map across ten fields. No black box — every score is a sum you can check.",
  },
  {
    mark: "02",
    planet: "ringed" as const,
    title: "Future paths",
    description:
      "Your traits are compared against archetypes to surface three directions: the steady fit, the stretch, and the one nobody had time to suggest.",
  },
  {
    mark: "03",
    planet: "giant" as const,
    title: "Real opportunities",
    description:
      "A TF-IDF match engine ranks curated STEM programs against your interests and goals, explains every score, and maps the pathways between them.",
  },
  // 04 exists because the feature did, and nobody could find it. Team-up has
  // matched on chosen_archetype, chosen_kind and field_scores since it shipped
  //, the same signals that build the plan, and it was reachable only from the
  // nav on a signed-in page. A student who never signs in never learns the
  // product has other students in it at all, which is the part that turns a
  // list of programmes into a reason to come back.
  {
    mark: "04",
    planet: "ringed" as const,
    title: "Students on the same path",
    description:
      "Team-up matches you against students whose path, fields and working style line up with yours, not by school or grade. Compare plans, split a project, or just have someone to ask. Opt-in, and you can leave at any time.",
  },
];

/*
 * Ursa Minor, hand-plotted. The line draws itself on load (pathLength
 * normalizes the two subpaths to the CSS dash length) and ends at Polaris,
 * which stays lit. Decorative only, hidden from assistive tech.
 */
function Constellation() {
  const scatter = [
    [30, 60, 1.4],
    [352, 300, 1.2],
    [60, 150, 1.1],
    [330, 200, 1.6],
    [210, 330, 1.2],
    [120, 90, 1.0],
    [260, 250, 1.3],
    [40, 260, 1.5],
    [370, 90, 1.1],
    [180, 40, 1.2],
    [310, 350, 1.0],
    [90, 380, 1.3],
    [240, 110, 1.0],
    [345, 30, 1.4],
    [25, 340, 1.1],
  ] as const;
  const stars = [
    [80, 330, 3],
    [150, 340, 2.6],
    [170, 280, 2.4],
    [100, 270, 2.6],
    [150, 210, 2.4],
    [210, 150, 2.8],
  ] as const;

  return (
    <svg
      viewBox="0 0 400 400"
      aria-hidden="true"
      className="mx-auto block w-full max-w-md"
    >
      {/* faint declination arcs — chart paper, not decoration for its own sake */}
      <circle
        cx="290"
        cy="80"
        r="150"
        fill="none"
        stroke="var(--border)"
        strokeWidth="0.5"
        opacity="0.5"
      />
      <circle
        cx="290"
        cy="80"
        r="240"
        fill="none"
        stroke="var(--border)"
        strokeWidth="0.5"
        opacity="0.35"
      />

      {scatter.map(([x, y, r], i) => (
        <circle
          key={`s${i}`}
          cx={x}
          cy={y}
          r={r}
          fill="var(--foreground)"
          opacity="0.35"
          className="constellation-star"
          style={{ animationDelay: `${0.1 + i * 0.12}s` }}
        />
      ))}

      <path
        d="M80 330 L150 340 L170 280 L100 270 L80 330 M100 270 L150 210 L210 150 L290 80"
        pathLength={480}
        fill="none"
        stroke="var(--aurora-dim)"
        strokeWidth="1"
        className="constellation-line"
      />

      {stars.map(([x, y, r], i) => (
        <circle
          key={`c${i}`}
          cx={x}
          cy={y}
          r={r}
          fill="var(--foreground)"
          className="constellation-star"
          style={{ animationDelay: `${0.4 + i * 0.3}s` }}
        />
      ))}

      {/* Polaris — the fixed point. Halo and star reveal together. */}
      <g className="constellation-star" style={{ animationDelay: "2.2s" }}>
        <circle
          cx="290"
          cy="80"
          r="14"
          fill="var(--star)"
          opacity="0.18"
          className="polaris-halo"
        />
        <path
          d="M290 66 293 77 304 80 293 83 290 94 287 83 276 80 287 77Z"
          fill="var(--star)"
        />
      </g>

      <text
        x="290"
        y="116"
        textAnchor="middle"
        fill="var(--muted)"
        fontSize="9"
        letterSpacing="2"
        fontFamily="var(--font-coords), monospace"
        className="constellation-star"
        style={{ animationDelay: "2.5s" }}
      >
        POLARIS
      </text>
    </svg>
  );
}

export default function Home() {
  const { t } = useLanguage();
  const router = useRouter();
  // A signed-in student who hits the marketing page (usually by clicking the
  // wordmark) wants their app, not the pitch, send them to the dashboard so
  // the logo never dumps them back on the signed-out hero.
  const { user, loading } = useAuth();
  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);
  const { scrollY } = useScroll();
  const pathwayRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress: pathwayProgress } = useScroll({
    target: pathwayRef,
    offset: ["start 0.75", "end 0.75"],
  });
  const shipTop = useTransform(pathwayProgress, [0, 1], ["2%", "96%"]);
  const constellationY = useTransform(scrollY, [0, 600], [0, -70]);
  const constellationOpacity = useTransform(scrollY, [0, 600], [1, 0.3]);

  return (
    <MotionConfig reducedMotion="user">
    <main className="bleed-root min-h-screen">
      {/*
        A 2D sprite collage that leans with the pointer, replacing the WebGL
        sky. three.js was being pulled into the page for decoration, and the
        decoration read as a generic space scene. These are the ten planet
        sprites the product already ships, laid out deterministically so the
        sky is the same place on every visit.
      */}
      <SpriteSky className="fixed inset-0 -z-10" />
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-8 sm:px-8 lg:px-10">
        <nav className="bleed-bg sticky top-0 z-40 -mt-8 flex items-center justify-between py-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-lg tracking-tight text-foreground"
          >
            <StarGlyph className="h-4 w-4 text-star" />
            <span className="h-display text-xl">Northstar</span>
          </Link>
          <div className="flex items-center gap-3">
            <Button render={<Link href="/login" />} className="h-9 px-4">
              Sign in / Sign up
            </Button>
            <ThemeToggle />
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr]">
          <AnimatedGroup
            preset="blur-slide"
            className="grid gap-0"
          >
            <TextEffect
              per="char"
              preset="fade"
              as="p"
              className="eyebrow"
              speedReveal={2}
            >
              A student-built opportunity map
            </TextEffect>
            {/* One italic word carries the thesis. The emphasis is on
                "deserves", not on "north star": the claim this project makes
                is about entitlement, not about navigation. */}
            <h1 className="h-display mt-5 max-w-3xl text-5xl leading-[1.05] text-foreground sm:text-6xl lg:text-7xl">
              Every student{" "}
              <em className="font-normal italic text-star">deserves</em> a{" "}
              <span className="whitespace-nowrap text-star">
                north star
                <StarGlyph className="ml-2 inline-block h-[0.45em] w-[0.45em] align-baseline" />
              </span>.
            </h1>
            <p className="mt-7 max-w-2xl text-base leading-8 text-muted-foreground sm:text-lg">
              Most students never hear about the research programs,
              scholarships, and competitions they were qualified for. Northstar
              starts with how you actually think and work — twenty behavioral
              questions — charts a course to real, ranked STEM opportunities with
              a reason attached to every one, and puts you next to the students
              walking the same route.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row">
              <Button render={<Link href="/login" />} className="h-12 px-7">
                Sign in to start
              </Button>
              <Button variant="outline" render={<Link href="/assessment" />} className="h-12 px-7">
                Try the assessment first
              </Button>
            </div>
            {/* The one thing on this site that needs nothing from you, no
                account, no assessment, no waiting for a deadline. Worth saying
                in the hero rather than three screens down, because a student
                who leaves without signing up should still leave with
                something. */}
            <p className="mt-5 text-sm leading-7 text-muted-foreground">
              Or skip all of it and{" "}
              <Link href="/learn" className="font-semibold text-aurora underline decoration-border underline-offset-4">
                take something off the shelf
              </Link>{" "}
              — free material you can start tonight, no account, each row
              quoting the line on its own page that proves it costs nothing.
            </p>
          </AnimatedGroup>

          <motion.div style={{ y: constellationY, opacity: constellationOpacity }}>
            <Constellation />
          </motion.div>
        </div>

        {/* Real deadlines, soonest first, straight from the shelf. Placed here
            because the hero makes a claim and this is the first thing that can
            check it, and because a visitor who scrolls past the fold should hit
            evidence, not another paragraph. Renders nothing at all if the query
            fails or nothing is open; see CatalogSignals. */}
        <div className="bleed-x mb-14">
          <DeadlineTicker />
        </div>

        <section aria-label="How Northstar works" className="pb-16">
          <h2 className="h-display text-section text-foreground">
            How you find it
          </h2>
          {/* The pathway: three worlds along a dashed course, revealed on
              scroll, the same shape as the product itself. */}
          <div ref={pathwayRef} className="relative mt-12">
            <div
              aria-hidden
              className="absolute bottom-4 left-7 top-4 border-l border-dashed border-border lg:left-1/2"
            />
            <motion.div
              aria-hidden
              style={{ top: shipTop }}
              className="absolute left-7 z-10 -translate-x-1/2 lg:left-1/2"
            >
              <Ship className="h-7 w-5 text-star" />
            </motion.div>
            {waypoints.map((waypoint, index) => (
              <InView
                key={waypoint.mark}
                once
                variants={{
                  hidden: { opacity: 0, scale: 0.6, y: 24 },
                  visible: { opacity: 1, scale: 1, y: 0 },
                }}
                transition={{ duration: 0.55, delay: index * 0.1 }}
                viewOptions={{ margin: "0px 0px -80px 0px" }}
              >
                <div className="relative flex min-h-[45vh] items-center gap-6 sm:gap-10 lg:grid lg:grid-cols-[1fr_3.5rem_1fr] lg:gap-x-12">
                  <Planet
                    kind={waypoint.planet}
                    className="lg:col-start-2 lg:row-start-1 lg:justify-self-center"
                  />
                  <div
                    className={
                      index % 2 === 0
                        ? "max-w-xl pt-1 lg:col-start-1 lg:row-start-1 lg:justify-self-end lg:text-right"
                        : "max-w-xl pt-1 lg:col-start-3 lg:row-start-1"
                    }
                  >
                    <p
                      className={`flex items-center gap-2 font-mono text-xs tracking-[0.2em] text-star ${
                        index % 2 === 0 ? "lg:justify-end" : ""
                      }`}
                    >
                      <StarGlyph className="h-3 w-3" />
                      {waypoint.mark}
                    </p>
                    <h3 className="mt-3 text-2xl font-semibold text-foreground sm:text-3xl">
                      {waypoint.title}
                    </h3>
                    <p className="mt-3 text-base leading-8 text-muted-foreground">
                      {waypoint.description}
                    </p>
                    {/* The figure repeats the paragraph's shape rather than
                        decorating it, six bars for six traits, three paths for
                        three directions, ranked rows with their reasons. Capped
                        narrow so it reads as a diagram in the margin, not an
                        illustration competing with the type. */}
                    {(() => {
                      const Figure = PILLAR_FIGURES[
                        waypoint.mark as keyof typeof PILLAR_FIGURES
                      ];
                      return Figure ? (
                        <Figure
                          className={`mt-6 h-auto w-full max-w-[13rem] text-foreground ${
                            index % 2 === 0 ? "lg:ml-auto" : ""
                          }`}
                        />
                      ) : null;
                    })()}
                  </div>
                </div>
              </InView>
            ))}
          </div>
        </section>

        {/* Why this exists, the one band printed on paper rather than sky.
            The register change is the section break: the page around it stays
            night, so this reads as a page from the atlas rather than another
            scroll of the same surface. Palette comes from the shared `.light`
            block in globals.css, never a second copy of it.

            Every number here is a claim about the CATALOG, not about how many
            people have used it. A judge can verify each one by querying the
            catalog. The audit that produced these numbers lives in
            northstar-docs/CATALOG-AUDIT.md, it was on this page and should
            not have been. Guarded by backend/tests/test_impact_claims.py. */}
        <div className="panel-paper bleed-x">
          <section
            aria-label="Why Northstar exists"
            className="mx-auto w-full max-w-6xl px-6 py-20 sm:px-8 lg:px-10"
          >
          <p className="eyebrow">Why this exists</p>
          <h2 className="h-display mt-3 text-section text-foreground">
            The opportunities were always there. The map wasn&apos;t.
          </h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <p className="text-base leading-8 text-muted-foreground">
              A student with a college counselor hears about summer research in
              tenth grade. A student without one finds out it existed after the
              deadline, if at all. That gap is not about talent and it is not
              about effort — it is about who happens to be told. Northstar is
              built for the students nobody told, as a project of{" "}
              <span className="text-foreground">Minorities in STEM</span>, a
              fiscally sponsored non-profit.
            </p>
            <p className="text-base leading-8 text-muted-foreground">
              So two things are deliberate. More than four in five programs on
              the high-school shelf cost nothing to apply to, because a catalog
              full of $3,000 summer intensives is a list of things you cannot
              do. And
              every ranking shows its reasoning — the field that matched, the
              grade window, the tags — because a score you cannot interrogate is
              only useful to someone who already has an adult to interpret it.
            </p>
          </div>
          {/* Three dated rows, each one clickable. The page no longer states a
              shelf size or a verification practice, those were removed on
              2026-09-27, so this is now the only claim in the section a visitor
              can check for themselves, which makes it carry more weight than it
              did, not less. Renders nothing when nothing is genuinely recent. */}
          <RecentlyAdded />
          </section>
        </div>

        <section aria-label="Frequently asked questions" className="pb-16 pt-16">
          <h2 className="h-display text-section text-foreground">
            {t("faq.title")}
          </h2>
          <div className="mt-8 grid gap-4">
            {(["1", "2", "3", "4"] as const).map((key) => (
              <details
                key={key}
                className="group rounded-lg border border-border bg-background/40 p-5 backdrop-blur"
              >
                <summary className="flex cursor-pointer items-center justify-between gap-4 text-base font-semibold text-foreground marker:content-none">
                  {t(`faq.q${key}`)}
                  <span className="font-mono text-muted-foreground transition group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="mt-3 text-sm leading-7 text-muted-foreground">
                  {t(`faq.a${key}`)}
                </p>
              </details>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button render={<Link href="/login" />} className="h-11 px-6">
              Sign in / Sign up
            </Button>
            <Button
              variant="outline"
              render={<Link href="/faq" />}
              className="h-11 px-6"
            >
              All questions
            </Button>
            <Button
              variant="outline"
              render={<Link href="/contact" />}
              className="h-11 px-6"
            >
              {t("footer.contact")}
            </Button>
          </div>
        </section>

      </section>

      <HorizonWaves className="block h-28 w-full text-foreground" />
      <SiteFooter />
    </main>
    </MotionConfig>
  );
}
