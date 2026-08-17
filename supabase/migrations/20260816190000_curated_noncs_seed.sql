-- Curated non-CS STEM catalog — the flagship programs Reddit/Devpost can't
-- surface (measured: subject subreddits yield ~0 opportunity links). These
-- are famous, verifiable, high-prestige programs across biology, chemistry,
-- physics, math, engineering/materials/robotics, health, and humanities.
--
-- Honesty stamps:
--   added_by='human' — curated by a person from known program facts.
--   deadline IS NULL — these run annually and deadlines drift; the card
--   shows "Rolling deadline". A real date must be verified against each
--   program's site before relying on it (do NOT fabricate deadlines).
--   cost — 0 for free/fully-funded; a positive approximate for paid
--   programs (aid usually available; see each site).
--
-- Idempotent: ON CONFLICT (title, host) DO NOTHING.

insert into public.opportunities
    (title, host, opportunity_field, type, blurb, description, deadline, cost,
     grade_min, grade_max, url, tags, location, audience, location_scope, added_by)
values
-- ---- Biology / health / chemistry ---------------------------------------
('Research Science Institute (RSI)', 'Center for Excellence in Education', 'interdisciplinary', 'program',
 'Free, highly selective summer research program at MIT for rising seniors.',
 'Six weeks of STEM research at MIT with mentorship from working scientists; fully funded. Among the most selective HS research programs in the world.',
 null, 0, 11, 12, 'https://www.cee.org/programs/research-science-institute',
 array['research','selective','funded'], 'Cambridge, MA', 'high_school', 'us', 'human'),

('Simons Summer Research Program', 'Stony Brook University', 'biology', 'internship',
 'Paid, hands-on university research for rising seniors across STEM fields.',
 'Rising seniors join a Stony Brook research group for the summer, produce a poster and paper, and earn a stipend.',
 null, 0, 11, 12, 'https://www.stonybrook.edu/simons/',
 array['research','stipend','university'], 'Stony Brook, NY', 'high_school', 'us', 'human'),

('Summer Science Program (SSP)', 'Summer Science Program, Inc.', 'biology', 'program',
 'Residential research in biochemistry, genomics, astrophysics, or synthetic chemistry.',
 'A 39-day residential program where students complete a real research project; need-based aid makes it accessible.',
 null, 7000, 10, 12, 'https://summerscience.org',
 array['research','residential','aid-available'], 'Multiple campuses', 'high_school', 'us', 'human'),

('Stanford Institutes of Medicine Summer Research (SIMR)', 'Stanford University', 'health', 'internship',
 'Eight-week biomedical research internship with a stipend.',
 'Juniors and seniors work in a Stanford lab on a medical research project and present at a poster session; stipend provided.',
 null, 0, 11, 12, 'https://simr.stanford.edu',
 array['medical','research','stipend'], 'Stanford, CA', 'high_school', 'us', 'human'),

('Garcia Summer Research Program', 'Stony Brook University', 'engineering', 'internship',
 'Polymer and materials-science research for high schoolers.',
 'A seven-week program in the Garcia Center for Polymers at Engineered Interfaces; students pursue original materials research and can co-author papers.',
 null, 0, 10, 12, 'https://www.stonybrook.edu/garcia/',
 array['materials','polymers','research'], 'Stony Brook, NY', 'high_school', 'us', 'human'),

('Rockefeller University Summer Science Research Program', 'Rockefeller University', 'biology', 'internship',
 'Laboratory research in biomedical science in NYC.',
 'Students work alongside Rockefeller scientists on biomedical research over the summer.',
 null, 0, 10, 12, 'https://www.rockefeller.edu/outreach/ssrp/',
 array['biomedical','lab','nyc'], 'New York, NY', 'high_school', 'us', 'human'),

('Broad Summer Scholars Program (BSSP)', 'Broad Institute of MIT and Harvard', 'biology', 'internship',
 'Six weeks of genomics and biomedical research with a stipend.',
 'Rising seniors conduct research at the Broad Institute and receive mentorship and a stipend.',
 null, 0, 11, 12, 'https://www.broadinstitute.org/bssp',
 array['genomics','research','stipend'], 'Cambridge, MA', 'high_school', 'us', 'human'),

('USA Biology Olympiad (USABO)', 'Center for Excellence in Education', 'biology', 'competition',
 'The national biology competition; top scorers train for the international team.',
 'A multi-round exam competition culminating in a national finals camp and the International Biology Olympiad team.',
 null, 0, 9, 12, 'https://www.usabo-trc.org',
 array['olympiad','biology','national'], null, 'high_school', 'us', 'human'),

('U.S. National Chemistry Olympiad (USNCO)', 'American Chemical Society', 'biology', 'competition',
 'National chemistry competition leading to the international team.',
 'Local and national exams select students for a study camp and the International Chemistry Olympiad team.',
 null, 0, 9, 12, 'https://www.acs.org/education/students/highschool/olympiad.html',
 array['olympiad','chemistry','national'], null, 'high_school', 'us', 'human'),

-- ---- Physics / astronomy / space ----------------------------------------
('U.S. Physics Team (USAPhO)', 'American Association of Physics Teachers', 'physics', 'competition',
 'National physics olympiad selecting the U.S. team for the IPhO.',
 'The F=ma exam and USAPhO select students for a training camp and the International Physics Olympiad team.',
 null, 0, 9, 12, 'https://www.aapt.org/physicsteam/',
 array['olympiad','physics','national'], null, 'high_school', 'us', 'human'),

('NASA SEES Summer Intern Program', 'University of Texas / NASA', 'physics', 'internship',
 'Earth and space science research internship with NASA data.',
 'A virtual then on-site internship where students analyze NASA Earth-science data and present findings.',
 null, 0, 10, 12, 'https://www.csr.utexas.edu/education-outreach/sees-internship/',
 array['nasa','space','earth-science'], 'Austin, TX', 'high_school', 'us', 'human'),

-- ---- Math ---------------------------------------------------------------
('PROMYS (Program in Mathematics for Young Scientists)', 'Boston University', 'math', 'program',
 'Six weeks of deep number theory and mathematical problem-solving.',
 'A famously rigorous residential program in number theory; need-blind admission with substantial financial aid.',
 null, 0, 9, 12, 'https://promys.org',
 array['number-theory','residential','aid-available'], 'Boston, MA', 'high_school', 'us', 'human'),

('Ross Mathematics Program', 'Ohio State / Rose-Hulman', 'math', 'program',
 'Intensive summer immersion in abstract mathematics and number theory.',
 'Students explore mathematics from first principles over six weeks; aid available.',
 null, 0, 9, 12, 'https://rossprogram.org',
 array['number-theory','proofs','residential'], 'Multiple campuses', 'high_school', 'us', 'human'),

('Hampshire College Summer Studies in Mathematics (HCSSiM)', 'Hampshire College', 'math', 'program',
 'Six-week intensive for mathematically curious high schoolers.',
 'A collaborative program emphasizing mathematical discovery and community.',
 null, 4500, 9, 12, 'https://www.hcssim.org',
 array['discovery','residential','aid-available'], 'Amherst, MA', 'high_school', 'us', 'human'),

('Stanford University Mathematics Camp (SUMaC)', 'Stanford University', 'math', 'program',
 'Advanced mathematics camp: abstract algebra, number theory, topology.',
 'A selective residential/online camp in advanced pure mathematics; financial aid available.',
 null, 8250, 10, 12, 'https://sumac.spcs.stanford.edu',
 array['advanced','pure-math','aid-available'], 'Stanford, CA', 'high_school', 'us', 'human'),

('Canada/USA Mathcamp', 'Mathcamp', 'math', 'program',
 'Five-week program of advanced, self-directed mathematics.',
 'Students choose from dozens of advanced math courses; open internationally, with financial aid.',
 null, 0, 9, 12, 'https://www.mathcamp.org',
 array['advanced','international','aid-available'], 'Rotating host', 'high_school', 'global', 'human'),

('MathILy', 'MathILy', 'math', 'program',
 'Serious mathematics of substantial heft and infinite lightness.',
 'A five-week residential program emphasizing discovery-based advanced mathematics.',
 null, 0, 9, 12, 'https://www.mathily.org',
 array['discovery','residential','aid-available'], 'Multiple campuses', 'high_school', 'us', 'human'),

('American Mathematics Competitions (AMC)', 'Mathematical Association of America', 'math', 'competition',
 'The gateway competition (AMC 10/12 to AIME to USAMO).',
 'National exams that qualify students toward the AIME, USA(J)MO, and the Math Olympiad Program (MOP).',
 null, 0, 9, 12, 'https://maa.org/math-competitions',
 array['olympiad','amc','national'], null, 'high_school', 'us', 'human'),

-- ---- Engineering / materials / robotics ---------------------------------
('MIT Introduction to Technology, Engineering & Science (MITES)', 'Massachusetts Institute of Technology', 'engineering', 'program',
 'Free, rigorous residential STEM program for rising seniors.',
 'Six weeks at MIT of engineering and science coursework; fully funded, aimed at students underrepresented in STEM.',
 null, 0, 11, 12, 'https://mites.mit.edu',
 array['engineering','funded','residential'], 'Cambridge, MA', 'high_school', 'us', 'human'),

('FIRST Robotics Competition (FRC)', 'FIRST', 'engineering', 'competition',
 'Team-based robotics competition building large-scale robots.',
 'Student teams design, build, and program a robot for a new game each season; regional and championship events worldwide.',
 null, 0, 9, 12, 'https://www.firstinspires.org/robotics/frc',
 array['robotics','team','competition'], null, 'high_school', 'global', 'human'),

('FIRST Tech Challenge (FTC)', 'FIRST', 'engineering', 'competition',
 'Robotics competition with smaller, kit-based robots.',
 'Teams build and program robots to complete a seasonal challenge; accessible entry into competitive robotics.',
 null, 0, 7, 12, 'https://www.firstinspires.org/robotics/ftc',
 array['robotics','team','competition'], null, 'high_school', 'global', 'human'),

('Team America Rocketry Challenge (TARC)', 'National Association of Rocketry / AIA', 'engineering', 'competition',
 'The world''s largest student rocket contest.',
 'Teams design, build, and fly model rockets to precise altitude and duration targets.',
 null, 0, 7, 12, 'https://rocketcontest.org',
 array['aerospace','rocketry','team'], null, 'high_school', 'us', 'human'),

('Clark Scholar Program', 'Texas Tech University', 'interdisciplinary', 'internship',
 'Intensive seven-week research across STEM and other fields.',
 'A small cohort works one-on-one with faculty mentors on original research; includes a stipend.',
 null, 0, 11, 12, 'https://www.depts.ttu.edu/honors/academicsandenrichment/affiliatedandhighschool/clarks/',
 array['research','mentored','stipend'], 'Lubbock, TX', 'high_school', 'us', 'human'),

('Science Olympiad', 'Science Olympiad, Inc.', 'interdisciplinary', 'competition',
 'Team competition across 23 STEM events, from anatomy to engineering.',
 'Regional, state, and national tournaments spanning biology, chemistry, physics, earth science, and engineering build events.',
 null, 0, 6, 12, 'https://www.soinc.org',
 array['team','multi-discipline','national'], null, 'high_school', 'us', 'human'),

-- ---- Cross-STEM flagships ------------------------------------------------
('Regeneron Science Talent Search (STS)', 'Society for Science', 'interdisciplinary', 'competition',
 'The nation''s oldest and most prestigious science research competition for seniors.',
 'Seniors submit original research; finalists compete in Washington, D.C. for major scholarships.',
 null, 0, 12, 12, 'https://www.societyforscience.org/regeneron-sts/',
 array['research','scholarship','prestige'], null, 'high_school', 'us', 'human'),

('Regeneron International Science and Engineering Fair (ISEF)', 'Society for Science', 'interdisciplinary', 'competition',
 'The world''s largest pre-college science competition.',
 'Students advance through affiliated fairs to present research and compete for millions in awards.',
 null, 0, 9, 12, 'https://www.societyforscience.org/isef/',
 array['research','international','prestige'], null, 'high_school', 'global', 'human'),

('Davidson Fellows Scholarship', 'Davidson Institute', 'interdisciplinary', 'scholarship',
 'Scholarships up to $50,000 for significant work in STEM, literature, and more.',
 'Students submit a significant piece of work; winners receive scholarships and recognition in Washington, D.C.',
 null, 0, 9, 12, 'https://www.davidsongifted.org/fellows-scholarship/',
 array['scholarship','research','prestige'], null, 'high_school', 'us', 'human'),

('Conrad Challenge', 'Conrad Foundation', 'business', 'competition',
 'Team innovation and entrepreneurship competition solving global problems.',
 'Teams develop a product and business plan addressing real-world challenges; finals at an Innovation Summit.',
 null, 0, 8, 12, 'https://www.conradchallenge.org',
 array['entrepreneurship','innovation','team'], null, 'high_school', 'global', 'human'),

('Diamond Challenge', 'University of Delaware', 'business', 'competition',
 'Global high-school entrepreneurship competition.',
 'Students pitch a business or social venture concept for a share of a large prize pool.',
 null, 0, 9, 12, 'https://diamondchallenge.org',
 array['entrepreneurship','pitch','global'], null, 'high_school', 'global', 'human'),

-- ---- Humanities ---------------------------------------------------------
('Telluride Association Summer Seminar (TASS)', 'Telluride Association', 'humanities', 'program',
 'Free, intensive humanities and critical-theory seminar.',
 'A tuition-free residential seminar in critical thinking, writing, and discussion on questions of social justice.',
 null, 0, 10, 11, 'https://www.tellurideassociation.org/our-programs/high-school-students/',
 array['writing','seminar','funded'], null, 'high_school', 'us', 'human'),

('Iowa Young Writers Studio', 'University of Iowa', 'humanities', 'program',
 'Residential creative-writing program from the storied Iowa program.',
 'Two-week sessions in fiction, poetry, and creative writing; some financial aid.',
 null, 2000, 10, 12, 'https://iyws.clas.uiowa.edu',
 array['writing','creative','residential'], 'Iowa City, IA', 'high_school', 'us', 'human'),

('John Locke Institute Essay Competition', 'John Locke Institute', 'humanities', 'competition',
 'International essay competition across philosophy, politics, economics, and more.',
 'Students write an argumentative essay in a chosen subject; shortlisted authors are invited to an awards dinner.',
 null, 0, 9, 12, 'https://www.johnlockeinstitute.com/essay-competition',
 array['essay','international','writing'], null, 'high_school', 'global', 'human'),

-- ---- Research mentorship (open, often paid) ------------------------------
('Pioneer Research Program', 'Pioneer Academics', 'interdisciplinary', 'program',
 'Online research program with U.S. professors, open internationally.',
 'Students complete an accredited research project mentored one-on-one by a professor; financial aid available.',
 null, 0, 10, 12, 'https://pioneeracademics.com',
 array['research','online','international'], 'Online', 'high_school', 'global', 'human')

on conflict (title, host) do nothing;
