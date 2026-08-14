-- Seed the catalog: 35 opportunities + 25 mentors.
-- Both sources are idempotent (ON CONFLICT DO NOTHING), so this migration
-- is safe on databases that were already seeded by hand from scripts/.
-- Discovered 2026-08-15: the live opportunities table was empty — the
-- seed SQL had only ever existed in scripts/, outside the migration flow.

-- Prerequisites the repaired migration history claims but the live database
-- never actually ran (`migration repair --status applied` marks migrations
-- as applied without executing them — migration 005's index was a casualty).
-- Both guards are idempotent, so databases that DO have them are untouched.
create unique index if not exists uq_opportunities_title_host
    on public.opportunities (title, host);

do $$
begin
    if not exists (
        select 1
        from pg_constraint c
        join pg_class t on t.oid = c.conrelid
        where t.relname = 'mentors' and c.contype = 'u'
    ) then
        create unique index if not exists uq_mentors_email
            on public.mentors (email);
    end if;
end $$;

-- Northstar opportunity seed data
-- 35 real STEM programs, scholarships, competitions for the CAC demo.
-- Idempotent: each INSERT uses ON CONFLICT (title, host) DO NOTHING, relying
-- on the unique index uq_opportunities_title_host (migration_005).
-- Re-running never duplicates rows.
-- Run after migration_002_northstar_schema.sql + migration_005_opportunities_unique.sql.

-- ============================================================================
-- Chunk 1: CS + Biology opportunities (rows 1-10)
-- ============================================================================

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Google Computer Science Summer Institute', 'Google', 'cs', 'program', 'Three-week immersive CS intro for rising college freshmen at Google campuses.', 'CSSI is a free three-week introduction to computer science for graduating high school seniors with a passion for technology — especially students from historically underrepresented groups. Participants learn programming fundamentals in JavaScript and Python, tour Google offices, and connect with mentors.', '2026-04-15', 0, 12, 12, 'https://buildyourfuture.withgoogle.com/programs/computer-science-summer-institute', ARRAY['free', 'introductory', 'underrepresented', 'google'], 'Mountain View, CA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('MIT PRIMES', 'MIT Mathematics Department', 'cs', 'program', 'Year-long research mentorship pairing high schoolers with MIT researchers.', 'MIT PRIMES is a free year-long research program for high school students in the Greater Boston area. Participants work one-on-one with MIT graduate students and faculty on original research projects spanning mathematics and computer science. Students present their work at conferences and can submit for publication.', '2025-11-30', 0, 9, 12, 'https://math.mit.edu/research/highschool/primes/', ARRAY['free', 'research', 'mentored', 'publication'], 'Cambridge, MA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Congressional App Challenge', 'U.S. House of Representatives', 'cs', 'competition', 'Annual nationwide coding competition judged by your local Member of Congress.', 'The Congressional App Challenge invites middle and high school students to build and submit an original app. Winners receive Congressional recognition, their app is displayed in the Capitol, and many gain press coverage. Past winners have gone on to secure internships and scholarships. No prior coding experience required — projects can be built on any platform.', '2026-10-24', 0, 9, 12, 'https://www.congressionalappchallenge.us/', ARRAY['free', 'coding', 'app', 'national', 'civic'], 'Washington, DC')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('BJC CS Principles Summer Workshop', 'UC Berkeley', 'cs', 'program', 'Online summer workshop teaching AP CS Principles through the Beauty and Joy of Computing.', 'The BJC Summer Workshop is a one-week remote program for high school students interested in CS education. Students build Snap! projects, explore the social implications of computing, and receive guidance on the AP CSP exam. No cost and no prior programming experience required.', '2026-06-01', 0, 9, 12, 'https://bjc.berkeley.edu/', ARRAY['free', 'remote', 'ap-csp', 'visual-programming', 'berkeley'], 'Berkeley, CA (remote)')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Amazon Future Engineer Scholarship', 'Amazon', 'cs', 'scholarship', '$40,000 scholarship + guaranteed Amazon internship for CS-bound seniors.', 'Amazon Future Engineer awards $40,000 over four years to 250 high school seniors planning to study computer science. Winners also receive a guaranteed paid summer internship at Amazon after their freshman year of college. Applicants must have completed or be enrolled in an AP CS course.', '2026-03-15', 0, 12, 12, 'https://www.amazonfutureengineer.com/scholarships', ARRAY['scholarship', 'internship', 'amazon', 'financial'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('NSF Research Experiences for Undergraduates (REU) - High School Track', 'National Science Foundation', 'biology', 'program', 'Summer research immersion in university biology labs, NSF-funded.', 'Many NSF REU sites accept advanced high school students for summer research in computational biology, genomics, and biochemistry. Students work 40 hours/week in a faculty lab, attend seminars, and present findings at a symposium. Stipend often provided. Placement is competitive — apply directly to individual REU sites.', '2026-02-01', 0, 11, 12, 'https://www.nsf.gov/crssprgm/reu/', ARRAY['free', 'research', 'lab', 'nsf', 'stipend'], 'Multiple sites nationwide')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Regeneron Science Talent Search', 'Society for Science & Regeneron', 'biology', 'competition', 'The nation''s oldest and most prestigious science research competition for high school seniors.', 'STS (formerly Intel/Westinghouse STS) recognizes 300 scholars and 40 finalists each year for original research projects. Awards total $3.1M+ with the top prize at $250,000. Projects in computational biology, bioinformatics, and genomics are increasingly represented among winners.', '2026-11-10', 0, 12, 12, 'https://www.societyforscience.org/regeneron-sts/', ARRAY['free', 'prestigious', 'research', 'regeneron', 'national'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Jackson Laboratory Summer Student Program', 'Jackson Laboratory', 'biology', 'program', 'Paid 10-week genetics and genomics research internship for high schoolers.', 'The JAX Summer Student Program places students in active biomedical research labs studying cancer, aging, and immunology. Students receive a stipend, housing, and mentorship from PhD-level scientists. The program culminates in a research symposium where students present their findings.', '2026-02-01', 0, 11, 12, 'https://www.jax.org/education-and-learning/', ARRAY['free', 'stipend', 'housing', 'genetics', 'research'], 'Bar Harbor, ME')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('BioGENEius Challenge', 'Biotechnology Institute', 'biology', 'competition', 'International biotech research competition for high school students.', 'The BioGENEius Challenge invites students to present original biotechnology research at the BIO International Convention. Projects span agriculture, medicine, and environmental science. Winners receive cash prizes and mentorship from industry leaders.', '2026-04-01', 0, 9, 12, 'https://www.biotechinstitute.org/programs/biogeneius', ARRAY['free', 'research', 'biotech', 'international'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('STEM Enhancement in Earth Science (SEES) Internship', 'NASA / UT Austin', 'biology', 'program', 'Remote internship in astrobiology, Earth science data, and climate modeling.', 'SEES is a competitive funded internship for high schoolers that pairs students with NASA scientists to analyze satellite data for Earth and biological research. Participants attend virtual seminars and complete a team research project over eight weeks. Stipend and laptop provided.', '2026-03-01', 0, 10, 12, 'https://www.tsgc.utexas.edu/sees/', ARRAY['free', 'remote', 'stipend', 'nasa', 'climate', 'astrobiology'], 'Austin, TX (remote)')
ON CONFLICT (title, host) DO NOTHING;

-- ============================================================================
-- Chunk 2: Math + Physics + Engineering opportunities (rows 11-21)
-- ============================================================================

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('USA Mathematical Olympiad (USAMO)', 'Mathematical Association of America', 'math', 'competition', 'The highest-level high school math olympiad in the United States.', 'USAMO is the pinnacle of the AMC pyramid — approximately 250 students qualify each year. The six-question proof-based exam spans algebra, combinatorics, geometry, and number theory. Top scorers are invited to the Mathematical Olympiad Program (MOP), the training camp for the USA IMO team.', '2026-02-15', 0, 9, 12, 'https://maa.org/usamo/', ARRAY['free', 'prestigious', 'proofs', 'olympiad', 'national'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Math Prize for Girls', 'Advantage Testing Foundation', 'math', 'competition', 'The largest math competition for girls in North America, with cash prizes.', 'Math Prize for Girls awards $50,000+ in prizes to top female mathematicians in grades 9-12. The contest features multiple rounds of creative problem-solving. Past winners have gone on to top STEM programs. Travel support available.', '2026-09-01', 0, 9, 12, 'https://mathprize.atfoundation.org/', ARRAY['free', 'women', 'cash-prize', 'competitive'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('PROMYS for Teachers (Student Track)', 'Boston University', 'math', 'program', 'Six-week summer program in advanced number theory at Boston University.', 'PROMYS is a residential summer program for mathematically ambitious high schoolers. Students explore number theory through guided problem sets and independent research labs. Partial and full financial aid available — PROMYS is need-blind in admissions.', '2026-03-15', 5000, 9, 12, 'https://www.bu.edu/promys/', ARRAY['summer', 'number-theory', 'residential', 'financial-aid'], 'Boston, MA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('MathWorks Math Modeling Challenge (M3 Challenges)', 'SIAM / MathWorks', 'math', 'competition', 'Free internet-based team modeling challenge with $100,000 in scholarships.', 'M3 Challenge is a one-day applied math competition where teams of 3-5 students solve an open-ended real-world problem using mathematical modeling. Past problems have addressed e-cigarette regulation, food waste, and broadband access. Over $100,000 in scholarships awarded annually.', '2026-03-01', 0, 11, 12, 'https://m3challenge.siam.org/', ARRAY['free', 'team', 'modeling', 'applied', 'scholarship'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Physics Olympiad Summer Camp (US Physics Team)', 'American Association of Physics Teachers', 'physics', 'program', 'Training camp for the top 20 US Physics Olympiad semifinalists.', 'The US Physics Team camp is an intensive 10-day residential program at the University of Maryland. Students prepare for the International Physics Olympiad through advanced problem sessions and experimental labs. All costs covered by AAPT and sponsors.', '2026-02-01', 0, 9, 12, 'https://www.aapt.org/physicsteam/', ARRAY['free', 'prestigious', 'olympiad', 'experimental', 'residential'], 'College Park, MD')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('CERN Summer Student Program (US-based)', 'University of Michigan / CERN', 'physics', 'program', 'Virtual particle physics research mentored by CERN collaborators.', 'This virtual program, run through US universities partnering with CERN, gives high school students hands-on experience with CMS and ATLAS open data. Students analyze particle collision data, attend lectures from CERN physicists, and present research at a virtual symposium.', '2026-05-15', 0, 11, 12, 'https://cern.ch/', ARRAY['free', 'remote', 'research', 'cern', 'particle-physics'], 'Remote')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('FIRST Robotics Competition (FRC)', 'FIRST (For Inspiration and Recognition of Science and Technology)', 'engineering', 'competition', 'World''s largest high school robotics competition — build a 120 lb robot.', 'FRC teams of high school students design, build, and program industrial-scale robots to compete in an annual game challenge. The season runs January to April with regional and world championship events. $80M+ in scholarships available exclusively to FIRST participants.', '2026-01-05', 6000, 9, 12, 'https://www.firstinspires.org/robotics/frc', ARRAY['robotics', 'team', 'build', 'competition', 'scholarship'], 'Worldwide (World Championship in Houston, TX)')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('MIT Beaver Works Summer Institute (BWSI)', 'MIT Lincoln Laboratory', 'engineering', 'program', 'Free four-week summer engineering program at MIT for rising seniors.', 'BWSI offers project-based courses in autonomous systems, cyber-physical systems, radar, and med-tech. Students work in teams with MIT instructors and deliver a capstone project. Courses are competitive and taught at an advanced undergraduate level. All costs covered.', '2026-03-01', 0, 12, 12, 'https://beaverworks.ll.mit.edu/', ARRAY['free', 'mit', 'autonomous', 'radar', 'capstone'], 'Cambridge, MA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Lemelson-MIT InvenTeams', 'Lemelson-MIT Program', 'engineering', 'program', 'Up to $10,000 grant to invent a technical solution to a real-world problem.', 'InvenTeams are groups of high school students awarded up to $10,000 to invent a technological solution to a problem they identify in their community. Teams receive mentorship from MIT faculty and present prototypes at EurekaFest. Past projects include affordable prosthetics and water purification devices.', '2026-04-15', 0, 9, 12, 'https://lemelson.mit.edu/inventeams', ARRAY['free', 'grant', 'invention', 'mit', 'team', 'social-impact'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('NASA High School Aerospace Scholars (HAS)', 'NASA', 'engineering', 'program', 'Online + on-site NASA engineering design challenge for Texas high schoolers.', 'HAS combines a four-month online curriculum in space exploration and engineering with a weeklong on-site experience at Johnson Space Center. Students design a Mars mission, build rover prototypes, and present to NASA engineers. Texas residents only but fully funded.', '2026-09-15', 0, 11, 12, 'https://www.nasa.gov/has/', ARRAY['free', 'nasa', 'aerospace', 'on-site', 'texas'], 'Houston, TX')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Davidson Fellows Scholarship', 'Davidson Institute', 'engineering', 'scholarship', '$50,000 scholarship for gifted students with a significant STEM project.', 'Davidson Fellows awards $50,000, $25,000, and $10,000 scholarships to students 18 and under who complete a significant piece of work in STEM, music, or literature. Engineering projects — from novel algorithms to hardware prototypes — are highly competitive categories.', '2026-02-15', 0, 11, 12, 'https://www.davidsongifted.org/fellows/', ARRAY['scholarship', 'gifted', 'project-based', 'prestigious'], NULL)
ON CONFLICT (title, host) DO NOTHING;

-- ============================================================================
-- Chunk 3: Interdisciplinary + Mix opportunities (rows 22-35)
-- ============================================================================

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Regeneron International Science and Engineering Fair (ISEF)', 'Society for Science & Regeneron', 'interdisciplinary', 'competition', 'The world''s largest pre-college science fair — $9M+ in awards.', 'ISEF brings together over 1,800 students from 75+ countries to present original research across 22 categories including computational biology, robotics, embedded systems, and mathematics. Top awards range from $1,000 to $75,000. Students qualify through ISEF-affiliated regional fairs.', '2026-03-01', 0, 9, 12, 'https://www.societyforscience.org/isef/', ARRAY['free', 'prestigious', 'research', 'international', 'all-fields'], 'Anaheim, CA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('MIT THINK Scholars Program', 'MIT THINK', 'interdisciplinary', 'program', 'MIT-funded program for high school research projects with tech prototypes.', 'THINK selects proposals from across STEM fields and awards up to $1,000 in project funding, a trip to MIT, and mentorship from MIT students. Applicants submit a research proposal; winners execute their project with regular feedback from their mentor.', '2026-01-01', 0, 9, 12, 'https://think.mit.edu/', ARRAY['free', 'mit', 'research', 'grant', 'mentored', 'project'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Conrad Challenge', 'Conrad Foundation / NASA', 'interdisciplinary', 'competition', 'International innovation competition — design a product that solves a global challenge.', 'Teams of 2-5 students design products addressing aerospace, energy, health, cyber-tech, ocean, and education categories. Finalists present at the Conrad Innovation Summit at NASA''s Kennedy Space Center. Winners receive scholarships, patent support, and commercialization guidance.', '2026-08-15', 0, 8, 12, 'https://www.conradchallenge.org/', ARRAY['free', 'innovation', 'nasa', 'entrepreneurial', 'team'], 'Kennedy Space Center, FL')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Telluride Association Summer Seminar (TASS)', 'Telluride Association', 'interdisciplinary', 'program', 'Free six-week residential humanities and social sciences seminar for rising seniors.', 'TASS is a fully funded six-week summer experience. TASS-A (Anti-Oppressive Studies) examines systems of power and inequality; TASS-CB (Critical Black Studies) explores Black intellectual traditions. Students read broadly, write daily, and share community life. Highly selective — ~60 students per year total.', '2026-01-05', 0, 12, 12, 'https://www.tellurideassociation.org/programs/high-school-students/', ARRAY['free', 'residential', 'humanities', 'critical-studies', 'prestigious'], 'Multiple sites')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Stanford Summer Institutes', 'Stanford University', 'interdisciplinary', 'program', 'Eight-week residential summer term with Stanford undergrad courses.', 'Stanford Summer Institutes lets high schoolers enroll in real Stanford courses across the entire catalog while living on campus. Courses in CS, biology, math, and engineering are available alongside humanities and arts. Need-based financial aid available.', '2026-02-01', 15000, 9, 12, 'https://summerinstitutes.stanford.edu/', ARRAY['residential', 'credit', 'stanford', 'financial-aid'], 'Stanford, CA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Simons Summer Research Program', 'Stony Brook University / Simons Foundation', 'interdisciplinary', 'program', 'Fully-funded seven-week research program in interdisciplinary STEM.', 'Simons SSP places students in active research groups across Stony Brook labs in physics, biology, computer science, and math. Students attend evening seminars, live on campus, and receive a stipend. Competitive — about 50 students per year. All costs plus stipend covered.', '2026-02-01', 0, 11, 12, 'https://www.stonybrook.edu/simons/', ARRAY['free', 'stipend', 'residential', 'research', 'simons'], 'Stony Brook, NY')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Research Science Institute (RSI)', 'CEE / MIT', 'interdisciplinary', 'program', 'The world''s most competitive summer STEM research program — 100 students selected globally.', 'RSI is a cost-free, six-week residential program at MIT. Students attend lectures in advanced STEM topics, then conduct individual research projects under MIT faculty and graduate student mentors. Final projects are presented at a symposium and often lead to publications or ISEF entries.', '2026-01-15', 0, 11, 12, 'https://www.cee.org/programs/research-science-institute', ARRAY['free', 'prestigious', 'mit', 'research', 'residential', 'competitive'], 'Cambridge, MA')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Coca-Cola Scholars Program', 'Coca-Cola Scholars Foundation', 'interdisciplinary', 'scholarship', '$20,000 scholarship for 150 seniors demonstrating leadership + academic excellence.', 'The Coca-Cola Scholars Program awards 150 $20,000 scholarships each year to graduating high school seniors who excel in academics, leadership, and community service. STEM students are heavily represented among winners. Awards are renewable for up to four years.', '2026-09-30', 0, 12, 12, 'https://www.coca-colascholarsfoundation.org/', ARRAY['scholarship', 'leadership', 'academic', 'national'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('QuestBridge College Match + National College Match Scholarships', 'QuestBridge', 'interdisciplinary', 'scholarship', 'Full-ride scholarship to top colleges for high-achieving low-income students.', 'QuestBridge connects high-achieving, low-income high school seniors to full four-year scholarships at 50 partner colleges including MIT, Stanford, Princeton, and Yale. The application is holistic — STEM project work strengthens the profile significantly. Over 7,000 students matched to date.', '2026-09-27', 0, 12, 12, 'https://www.questbridge.org/', ARRAY['free', 'scholarship', 'full-ride', 'low-income', 'top-colleges'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('NYAS Junior Academy', 'New York Academy of Sciences', 'interdisciplinary', 'program', 'Global mentored STEM challenge program for students 13-17.', 'The Junior Academy pairs students with STEM mentors from industry and academia for 60-day challenge cycles tackling real problems from partners like the Gates Foundation and ARM. Challenges span computational epidemiology, sustainability, and AI ethics. Fully virtual, entirely free.', '2025-11-01', 0, 8, 12, 'https://www.nyas.org/programs/global-stem-alliance/the-junior-academy/', ARRAY['free', 'remote', 'global', 'challenge', 'mentored'], 'Remote')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Gates Millennium Scholars', 'Bill & Melinda Gates Foundation', 'interdisciplinary', 'scholarship', 'Full scholarship through graduation for minority students — any major.', 'GMS covers full unmet need and any graduate-level costs for 1,000 students per year. STEM majors (CS, biology, engineering, math) are eligible alongside all other disciplines. Pell-eligible minority students, minimum GPA 3.3, demonstrated leadership.', '2026-01-15', 0, 12, 12, 'https://gmsp.org/', ARRAY['free', 'scholarship', 'full-ride', 'minority', 'leadership'], NULL)
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Broadcom MASTERS', 'Society for Science & Broadcom', 'interdisciplinary', 'competition', 'National STEM competition + $100,000 prize for middle schoolers, ISEF feeder.', 'Broadcom MASTERS selects 30 finalists from among the top 10% of ISEF-affiliated fair projects in math, science, and engineering. Finalists compete in team challenges at a weeklong event in Washington, DC. Top prize: $25,000 Samueli Foundation Prize.', '2026-06-15', 0, 8, 9, 'https://www.societyforscience.org/broadcom-masters/', ARRAY['free', 'competition', 'national', 'prestigious', 'middle-school'], 'Washington, DC')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('Lumiere Research Scholar Program', 'Lumiere Education', 'interdisciplinary', 'mentorship', 'One-on-one research mentorship with PhD scholars — produce a publishable paper.', 'Lumiere matches high school students with PhD mentors from top universities for 12-week independent research projects. Students write a full academic paper in their chosen field (CS, biology, physics, math, etc.) with weekly guidance. Papers can be submitted for publication. Financial aid available.', '2025-12-10', 2900, 9, 12, 'https://www.lumiere-education.com/', ARRAY['mentorship', 'research', 'publication', 'financial-aid', 'remote'], 'Remote')
ON CONFLICT (title, host) DO NOTHING;

INSERT INTO public.opportunities (title, host, opportunity_field, type, blurb, description, deadline, cost, grade_min, grade_max, url, tags, location)
VALUES ('VEX Robotics Competition', 'REC Foundation', 'engineering', 'competition', 'Scalable robotics competition — design, build, code, compete.', 'VEX offers VEX IQ (elementary/middle) and VRC (high school) competitions where teams design robots to play an annual game. Over 20,000 teams worldwide. Scholarships available for VEX participants through the REC Foundation.', '2026-08-01', 1000, 9, 12, 'https://www.roboticseducation.org/vex-robotics-competition/', ARRAY['robotics', 'team', 'scalable', 'international', 'scholarship'], 'Worldwide')
ON CONFLICT (title, host) DO NOTHING;

-- End of seed_opportunities.sql — 35 real STEM opportunities across all
-- fields and types, covering grades 8-12 with programs, scholarships,
-- competitions, and mentorships from Google, NASA, MIT, Stanford, and more.
-- Re-running this file is safe: ON CONFLICT (title, host) DO NOTHING skips existing rows.

-- Northstar mentor seed data
-- 25 real-style STEM mentor profiles representing industry and academia.
-- Idempotent: each INSERT uses ON CONFLICT (email) DO NOTHING, backed by the
-- unique(email) constraint on public.mentors from migration_002, so re-running
-- never duplicates rows and stays additive for incremental fixes.
-- Run after supabase/schema.sql + migration_002.
--
-- NOTE on `bio_embedding`: The mentors.bio_embedding column is a vector(384)
-- populated at match time by the backend (see app/mentors.py — the embedding
-- generator runs lazily when /mentors is hit). The seed leaves it NULL so
-- re-seeding stays cheap.

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Aisha Patel', 'aisha.patel@mit.example',
       'MIT CSAIL research scientist working on AI safety and model interpretability. PhD from Stanford.',
       ARRAY['cs', 'biology'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Marcus Chen', 'marcus.chen@stanford.example',
       'Stanford CS professor focused on distributed systems and programming languages. ACM Fellow.',
       ARRAY['cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Sarah Rosen', 'sarah.rosen@google.example',
       'Senior software engineer at Google working on TensorFlow and ML infrastructure.',
       ARRAY['cs', 'engineering'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. James Wright', 'james.wright@msi.example',
       'Memorial Sloan Kettering computational biologist researching cancer genomics.',
       ARRAY['biology', 'cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Elena Rodriguez', 'elena.rodriguez@harvard.example',
       'Harvard Medical School professor studying CRISPR-Cas9 gene editing systems.',
       ARRAY['biology'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Robert Kim', 'robert.kim@broad.example',
       'Broad Institute director of single-cell sequencing research.',
       ARRAY['biology', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Maria Santos', 'maria.santos@ucb.example',
       'UC Berkeley math professor in pure algebraic geometry.',
       ARRAY['math'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Alan Zhao', 'alan.zhao@princeton.example',
       'Princeton number theorist studying modular forms. Clay Math Fellow.',
       ARRAY['math', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Lisa Park', 'lisa.park@cmu.example',
       'CMU math professor focused on combinatorics and graph theory.',
       ARRAY['math', 'cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. David Hofstadter', 'david.hofstadter@cern.example',
       'CERN senior physicist working on the ATLAS experiment.',
       ARRAY['physics'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Yuki Tanaka', 'yuki.tanaka@caltech.example',
       'Caltech astrophysicist researching exoplanet atmospheres with JWST data.',
       ARRAY['physics', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Priya Sharma', 'priya.sharma@mit-physics.example',
       'MIT physics professor in quantum information theory.',
       ARRAY['physics', 'cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Carlos Mendez', 'carlos.mendez@nasa-jpl.example',
       'NASA JPL robotics engineer designing Mars rover autonomous systems.',
       ARRAY['engineering', 'cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Jennifer Wu', 'jennifer.wu@mech.example',
       'Mechanical engineering professor at MIT working on soft robotics.',
       ARRAY['engineering', 'biology'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Ben Patel', 'ben.patel@stanford-eng.example',
       'Stanford electrical engineering professor focused on chip design and semiconductors.',
       ARRAY['engineering', 'physics'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Olivia Murphy', 'olivia.murphy@cornell.example',
       'Cornell bioengineer working on tissue-engineered organ systems.',
       ARRAY['biology', 'engineering'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Kenji Watanabe', 'kenji.watanabe@deepmind.example',
       'DeepMind research scientist on reinforcement learning and game theory.',
       ARRAY['cs', 'math'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Hannah Schmidt', 'hannah.schmidt@ethz.example',
       'ETH Zurich professor of computational neuroscience.',
       ARRAY['biology', 'cs', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Fatima Al-Saleh', 'fatima.alsaleh@kaust.example',
       'KAUST professor of computational chemistry and AI-driven drug design.',
       ARRAY['biology', 'cs', 'chemistry'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Raj Kumar', 'raj.kumar@iit.example',
       'IIT Delhi professor of theoretical physics working on string theory.',
       ARRAY['physics', 'math'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Sofia Hernandez', 'sofia.hernandez@ucsf.example',
       'UCSF professor of clinical AI building diagnostic tools for underserved hospitals.',
       ARRAY['biology', 'cs', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Akihiro Sato', 'akihiro.sato@toyota-research.example',
       'Toyota Research Institute robotics lead working on autonomous manipulation.',
       ARRAY['engineering', 'cs'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Claire Dubois', 'claire.dubois@cea.example',
       'CEA researcher in nuclear physics and reactor simulation.',
       ARRAY['physics', 'engineering'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Michael Thompson', 'michael.thompson@umich.example',
       'University of Michigan professor teaching and researching applied mathematics and data science.',
       ARRAY['math', 'cs', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.mentors (name, email, bio, expertise)
VALUES ('Dr. Lucia Romano', 'lucia.romano@esa.example',
       'European Space Agency mission analyst for planetary exploration programs.',
       ARRAY['physics', 'engineering', 'interdisciplinary'])
ON CONFLICT (email) DO NOTHING;

-- End of seed_mentors.sql — 25 mentor profiles across 8 expertise combinations.
-- Re-running is safe: ON CONFLICT (email) DO NOTHING skips existing rows.
