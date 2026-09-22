# Northstar, in plain English

*What this app is made of, explained without jargon. Written against commit `3746d27`.*

---

## The one-paragraph version

Northstar is a website that helps a high-school student find STEM opportunities — research programs, hackathons, internships — that actually fit them, and then shows them a path forward. It is built out of three pieces: a **website** the student sees, a **server** that does the thinking, and a **database** that remembers everything. A few robots run on a timer in the background, going out to the internet every morning to find new opportunities so the list never goes stale.

---

## The three pieces

### 1. The website (what you see)

This is the part in your browser. It draws every page — the login screen, the quiz, the dashboard, the map, the opportunity listings. It's written with a toolkit called Next.js, which is one of the standard ways to build a modern website.

It's hosted by a company called Vercel, at **northstar.study**. Vercel's job is to keep copies of the site on machines around the world so it loads fast no matter where the student is.

Important thing to understand: **the website does not know anything on its own.** It is a display. Every time it needs a real answer — "what opportunities match me?" — it has to ask the server.

### 2. The server (what does the thinking)

This is a program written in Python that sits on the internet waiting to be asked questions. There are 39 different questions it knows how to answer, and each one has an address. `/match` means "rank the opportunities for this student." `/missions` means "what tasks does this student have?" `/advisor` means "answer this student's open-ended question."

The server is where the actual product lives. Two things in particular:

**The matching engine.** When a student asks for matches, the server compares the words in that student's profile against the words in every opportunity in the catalog, and scores how well they overlap. Then it nudges scores up for things like *the field matches what you said you're into* (+0.15), *you're the right grade for it* (+0.10), *it's free* (+0.05). The result is a ranked list, and each item comes with a sentence explaining why it ranked where it did.

This is deliberately not a black box. It's arithmetic you could do by hand on paper. If a student asks "why is this #1?", there is a real answer.

**Learning from what students actually do.** Separately, the server watches what students report back — did you apply, did you get in, was it worth it. Over time this builds a "students like you also liked this" signal. It's capped so it can only move a score by a tiny amount (about 7% either way), and students who haven't logged anything yet get none of it. It's a nudge on top of the explainable engine, never a replacement for it.

### 3. The database (what remembers)

A Postgres database hosted by Supabase. 22 tables: students, opportunities, matches, outcomes, bookmarks, friendships, missions, and so on. Everything that has to survive a page refresh lives here.

Supabase also handles **logging in**. When a student signs in, Supabase hands their browser a signed pass — think of a wristband at a concert. The browser shows that wristband to the server on every request, and the server checks the signature before answering. No valid wristband, no answer. There's a check running every two hours in the background whose entire job is to confirm the bouncer is still at the door.

---

## The background robots

Three jobs run on GitHub's servers on a schedule, without anyone pressing a button.

**Every morning at ~9:17am Pacific — the opportunity hunt.**
A scraper reads Reddit and Devpost looking for posts about programs, contests, and internships. It finds a lot of junk. So everything it finds goes to an AI screener that reads each candidate and answers a narrow question: *is this a real, currently-open opportunity, and is there a working link?* Only candidates that clear all three checks get added to the live catalog automatically. Everything else waits in a pile for a human to look at.

Two guardrails worth naming. The AI is not allowed to invent programs or make up deadlines — it only extracts what's already in the post and gives a verdict. And every listing it approved is stamped `added_by='ai'`, so if a bad batch ever gets through, you can find and delete exactly those and nothing else.

This used to run on a laptop. It didn't run on any day the laptop lid was closed. Moving it to GitHub fixed that.

**Every two hours — the "is the site still up?" check.**
It loads the real homepage, asks the server if it's healthy, and tries to access a private page without logging in to confirm it still gets rejected. If any of those fail, an email goes out. This is how a broken deploy gets noticed by the developer instead of by a visitor.

**Every time code changes — the safety net.**
Before any change can land, an automated checklist runs: does the website still build, do the types line up, do the tests pass on both sides. 14 test files on the server side, plus tests specifically guarding the scoring math — the one place a silent bug would do the most damage.

---

## How a single request travels

A student opens the opportunities page.

1. The browser loads the page from Vercel. It's empty of real data.
2. The page asks Supabase for the student's login pass.
3. It sends `GET /match` to the server with that pass attached.
4. The server checks the signature. Bad or missing → `401`, conversation over.
5. The server pulls the student's profile and the full opportunity catalog from the database.
6. The matching engine scores every opportunity, adds the boosters, folds in the small "students like you" signal, writes an explanation sentence for each.
7. A ranked list comes back as data.
8. The page draws it as cards.

Total round trip: well under a second. Every step is either explainable arithmetic or a signature check.

---

## The quiz, and why it's separate

The assessment quiz runs **entirely in the browser** — the server isn't involved in scoring it. A student answers agree/disagree questions on a 1–5 scale. Each answer carries small weights toward six traits: builder, analyst, risk tolerance, comfort with ambiguity, collaboration, and execution tempo.

The math is three steps:
1. Add up the weights from the answers they chose.
2. Convert each trait to a 0–100 score, divided by the highest that trait *could* have scored. (Not a fixed number — this keeps traits fair against each other even though they don't appear in the same number of questions.)
3. Compare the resulting six-number fingerprint against a set of pre-written archetypes, and surface three: the **closest** fit, the most **ambitious** stretch, and the most **unconventional** direction.

No number in there is invented at runtime. Every weight is written down in a file you can open and read.

---

## The advisor, and what it's not allowed to do

There's a conversational feature where a student can ask an open question — "what unusual paths fit how I think?" The AI answering it can only draw on opportunities that are actually in the verified catalog, and it has to cite them by number so the interface can show "backed by" links.

What it is explicitly forbidden from doing: producing fit percentages or rankings. That authority belongs to the explainable matching engine and stays there. The advisor explores; the engine ranks.

It also has a hard spend ceiling — 10 questions per student per day, 150 across everyone — because the AI provider charges per call. Ask the same question twice and the second one is free, served from a cache.

---

## Where things live

| Piece | Technology | Where it runs |
|---|---|---|
| Website | Next.js / React | Vercel — `northstar.study` |
| Server | FastAPI / Python | Vercel serverless — `northstar-api-theta.vercel.app` |
| Database + login | Supabase Postgres | Supabase cloud |
| Scheduled robots | GitHub Actions | GitHub's servers |
| Error reports | Sentry | Both sides, production only |

---

## One naming quirk

The code, the API, and the live domain all say **Northstar**. The repository folder and the older planning documents say **Meridian**. Same project — it was renamed partway through, and the old name survives in a few places that were never worth the churn to change.
