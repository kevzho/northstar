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
