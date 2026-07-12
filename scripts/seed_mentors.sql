-- Northstar mentor seed data
-- 25 real-style STEM mentor profiles representing industry and academia.
-- Idempotent: each INSERT uses WHERE NOT EXISTS keyed on (email) so re-running
-- never duplicates rows. Run after supabase/schema.sql + migration_002.
--
-- NOTE on `bio_embedding`: The mentors.bio_embedding column is a vector(384)
-- populated at match time by the backend (see app/mentors.py — the embedding
-- generator runs lazily when /mentors is hit). The seed leaves it NULL so
-- re-seeding stays cheap.

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Aisha Patel', 'aisha.patel@mit.example',
       'MIT CSAIL research scientist working on AI safety and model interpretability. PhD from Stanford.',
       ARRAY['cs', 'biology']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'aisha.patel@mit.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Marcus Chen', 'marcus.chen@stanford.example',
       'Stanford CS professor focused on distributed systems and programming languages. ACM Fellow.',
       ARRAY['cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'marcus.chen@stanford.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Sarah Rosen', 'sarah.rosen@google.example',
       'Senior software engineer at Google working on TensorFlow and ML infrastructure.',
       ARRAY['cs', 'engineering']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'sarah.rosen@google.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. James Wright', 'james.wright@msi.example',
       'Memorial Sloan Kettering computational biologist researching cancer genomics.',
       ARRAY['biology', 'cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'james.wright@msi.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Elena Rodriguez', 'elena.rodriguez@harvard.example',
       'Harvard Medical School professor studying CRISPR-Cas9 gene editing systems.',
       ARRAY['biology']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'elena.rodriguez@harvard.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Robert Kim', 'robert.kim@broad.example',
       'Broad Institute director of single-cell sequencing research.',
       ARRAY['biology', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'robert.kim@broad.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Maria Santos', 'maria.santos@ucb.example',
       'UC Berkeley math professor in pure algebraic geometry.',
       ARRAY['math']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'maria.santos@ucb.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Alan Zhao', 'alan.zhao@princeton.example',
       'Princeton number theorist studying modular forms. Clay Math Fellow.',
       ARRAY['math', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'alan.zhao@princeton.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Lisa Park', 'lisa.park@cmu.example',
       'CMU math professor focused on combinatorics and graph theory.',
       ARRAY['math', 'cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'lisa.park@cmu.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. David Hofstadter', 'david.hofstadter@cern.example',
       'CERN senior physicist working on the ATLAS experiment.',
       ARRAY['physics']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'david.hofstadter@cern.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Yuki Tanaka', 'yuki.tanaka@caltech.example',
       'Caltech astrophysicist researching exoplanet atmospheres with JWST data.',
       ARRAY['physics', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'yuki.tanaka@caltech.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Priya Sharma', 'priya.sharma@mit-physics.example',
       'MIT physics professor in quantum information theory.',
       ARRAY['physics', 'cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'priya.sharma@mit-physics.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Carlos Mendez', 'carlos.mendez@nasa-jpl.example',
       'NASA JPL robotics engineer designing Mars rover autonomous systems.',
       ARRAY['engineering', 'cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'carlos.mendez@nasa-jpl.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Jennifer Wu', 'jennifer.wu@mech.example',
       'Mechanical engineering professor at MIT working on soft robotics.',
       ARRAY['engineering', 'biology']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'jennifer.wu@mech.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Ben Patel', 'ben.patel@stanford-eng.example',
       'Stanford electrical engineering professor focused on chip design and semiconductors.',
       ARRAY['engineering', 'physics']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'ben.patel@stanford-eng.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Olivia Murphy', 'olivia.murphy@cornell.example',
       'Cornell bioengineer working on tissue-engineered organ systems.',
       ARRAY['biology', 'engineering']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'olivia.murphy@cornell.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Kenji Watanabe', 'kenji.watanabe@deepmind.example',
       'DeepMind research scientist on reinforcement learning and game theory.',
       ARRAY['cs', 'math']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'kenji.watanabe@deepmind.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Hannah Schmidt', 'hannah.schmidt@ethz.example',
       'ETH Zurich professor of computational neuroscience.',
       ARRAY['biology', 'cs', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'hannah.schmidt@ethz.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Fatima Al-Saleh', 'fatima.alsaleh@kaust.example',
       'KAUST professor of computational chemistry and AI-driven drug design.',
       ARRAY['biology', 'cs', 'chemistry']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'fatima.alsaleh@kaust.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Raj Kumar', 'raj.kumar@iit.example',
       'IIT Delhi professor of theoretical physics working on string theory.',
       ARRAY['physics', 'math']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'raj.kumar@iit.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Sofia Hernandez', 'sofia.hernandez@ucsf.example',
       'UCSF professor of clinical AI building diagnostic tools for underserved hospitals.',
       ARRAY['biology', 'cs', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'sofia.hernandez@ucsf.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Akihiro Sato', 'akihiro.sato@toyota-research.example',
       'Toyota Research Institute robotics lead working on autonomous manipulation.',
       ARRAY['engineering', 'cs']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'akihiro.sato@toyota-research.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Claire Dubois', 'claire.dubois@cea.example',
       'CEA researcher in nuclear physics and reactor simulation.',
       ARRAY['physics', 'engineering']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'claire.dubois@cea.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Michael Thompson', 'michael.thompson@umich.example',
       'University of Michigan professor teaching and researching applied mathematics and data science.',
       ARRAY['math', 'cs', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'michael.thompson@umich.example');

INSERT INTO public.mentors (name, email, bio, expertise)
SELECT 'Dr. Lucia Romano', 'lucia.romano@esa.example',
       'European Space Agency mission analyst for planetary exploration programs.',
       ARRAY['physics', 'engineering', 'interdisciplinary']
WHERE NOT EXISTS (SELECT 1 FROM public.mentors WHERE email = 'lucia.romano@esa.example');

-- End of seed_mentors.sql — 25 mentor profiles across 8 expertise combinations.
-- Re-running is safe: WHERE NOT EXISTS skips existing rows.
