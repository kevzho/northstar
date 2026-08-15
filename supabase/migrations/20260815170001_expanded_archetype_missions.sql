-- Missions for the twelve expansion archetypes (design, business,
-- humanities, health, and hybrids). Same contract as the first wave:
-- three per archetype, easy -> bold, each tied to the trait it
-- exercises. Archetype definitions live in frontend/lib/archetypes.ts.

insert into public.missions (archetype_id, title, description, trait_focus, effort, sort_order) values
('game-designer', 'Paper-prototype a game', 'Design a playable game with index cards and dice, then playtest it with three people. Their confusion notes are the evidence.', 'builder', 'an afternoon', 1),
('game-designer', 'Analyze why one level works', 'Take a level everyone remembers and break down its teaching structure beat by beat. Publish the analysis.', 'analyst', 'an afternoon', 2),
('game-designer', 'Ship a tiny playable', 'Build the smallest playable thing in any engine and put it on itch.io. Ten minutes of play is enough; public is the point.', 'executionTempo', 'two weeks', 3),

('product-designer', 'Redesign something broken', 'Pick a form, menu, or flow that frustrates people and redesign it. Before and after screens, plus the reasoning.', 'builder', 'a weekend', 1),
('product-designer', 'Run three usability tests', 'Watch three people use something you made (or a school site) while thinking aloud. Log every stumble without helping.', 'collaboration', 'an afternoon', 2),
('product-designer', 'Build a pattern library', 'Collect fifteen screenshots of one pattern done well and badly across apps. Annotate what separates them.', 'analyst', 'a weekend', 3),

('digital-media-artist', 'Publish a piece a week', 'Make and post one small finished piece weekly for three weeks - image, motion, sound, any medium. The streak is the evidence.', 'executionTempo', 'two weeks', 1),
('digital-media-artist', 'Remix with credit', 'Take an open-licensed work, transform it into something new, and document the lineage properly.', 'ambiguityComfort', 'a weekend', 2),
('digital-media-artist', 'Show work for critique', 'Post one piece somewhere real critique happens and incorporate one piece of feedback into a revision.', 'riskTolerance', 'an afternoon', 3),

('social-entrepreneur', 'Map one community need', 'Interview five people about a local problem nobody owns. Write the one-page case for why it persists.', 'collaboration', 'a weekend', 1),
('social-entrepreneur', 'Run a $0 pilot', 'Deliver the smallest version of your fix to five real people without spending money. Log what happened.', 'riskTolerance', 'two weeks', 2),
('social-entrepreneur', 'Do the unit math', 'Model what your pilot would cost and produce at 10x scale. One honest spreadsheet beats a pitch deck.', 'analyst', 'an afternoon', 3),

('quantitative-economist', 'Chart one market you know', 'Pick a market you actually participate in - sneakers, game skins, concert tickets - and chart its supply, demand, and one weirdness.', 'analyst', 'a weekend', 1),
('quantitative-economist', 'Run a natural experiment', 'Find two comparable situations that differ in one policy and compare outcomes with real data. Write up the caveats honestly.', 'ambiguityComfort', 'two weeks', 2),
('quantitative-economist', 'Forecast and grade yourself', 'Publish five economic predictions with probabilities, then score them when they resolve.', 'riskTolerance', 'two weeks', 3),

('investigative-journalist', 'File one records request', 'Send a public-records request to a local agency about something you are curious about. The request and response are the evidence.', 'riskTolerance', 'a weekend', 1),
('investigative-journalist', 'Verify a viral claim', 'Take one claim going around your school or feed and trace it to primary sources. Publish what held and what did not.', 'analyst', 'an afternoon', 2),
('investigative-journalist', 'Interview three sides', 'Report one local issue by interviewing three people who disagree. Write it so none of them can call it unfair.', 'collaboration', 'a weekend', 3),

('science-policy-advocate', 'Write a one-page brief', 'Take one scientific finding and write the one-page policy brief a busy council member would actually read.', 'analyst', 'a weekend', 1),
('science-policy-advocate', 'Attend and summarize a hearing', 'Sit through one public meeting - school board, city council - and publish a plain-language summary of what was decided.', 'ambiguityComfort', 'an afternoon', 2),
('science-policy-advocate', 'Make one public comment', 'Deliver a comment, in person or written, on an issue you briefed. The record of it is the evidence.', 'riskTolerance', 'an afternoon', 3),

('public-health-strategist', 'Map a health behavior', 'Survey thirty peers about one health behavior - sleep, screens, energy drinks - and publish the anonymized picture.', 'analyst', 'a weekend', 1),
('public-health-strategist', 'Design one intervention', 'Design the smallest nudge that could shift what you measured, run it for two weeks, and measure again.', 'builder', 'two weeks', 2),
('public-health-strategist', 'Interview a health worker', 'Twenty minutes with a school nurse, EMT, or county health worker about what prevention actually looks like. Five takeaways.', 'collaboration', 'an afternoon', 3),

('sports-scientist', 'Quantify one athlete: you', 'Track one performance metric on yourself for three weeks with a consistent protocol. Plot it and name what moved it.', 'executionTempo', 'two weeks', 1),
('sports-scientist', 'Break down one movement', 'Film a movement - free throw, sprint start, serve - and analyze it frame by frame against how coaches teach it.', 'analyst', 'an afternoon', 2),
('sports-scientist', 'Build a training aid', 'Make one physical or digital tool that gives an athlete feedback they could not see before. One user test included.', 'builder', 'a weekend', 3),

('bioethicist', 'Steelman both sides', 'Pick one live bioethics question and write the strongest honest case for each side. Readers should not guess your view.', 'ambiguityComfort', 'a weekend', 1),
('bioethicist', 'Trace one consent form', 'Read a real research consent form and annotate what a participant actually agrees to versus what they likely believe.', 'analyst', 'an afternoon', 2),
('bioethicist', 'Host one structured debate', 'Run a debate on your question with real rules and real sides. The recording or writeup is the evidence.', 'collaboration', 'an afternoon', 3),

('edtech-creator', 'Teach one concept better', 'Take a concept your class struggled with and build a better explainer - interactive, video, or worksheet. Test it on two students.', 'builder', 'a weekend', 1),
('edtech-creator', 'Measure the learning', 'Give a five-question check before and after your explainer. Publish the delta, even if it embarrasses you.', 'analyst', 'an afternoon', 2),
('edtech-creator', 'Get one teacher to use it', 'Convince one real teacher to run your material with a class. Their feedback is the evidence.', 'riskTolerance', 'a weekend', 3),

('conservation-storyteller', 'Document one local ecosystem', 'Spend three sessions in one natural spot and produce a photo essay or short film that makes someone care about it.', 'builder', 'a weekend', 1),
('conservation-storyteller', 'Pair story with data', 'Add real measurements - species counts, water readings, temperature logs - to your story so it argues, not just moves.', 'analyst', 'a weekend', 2),
('conservation-storyteller', 'Publish where it counts', 'Get the piece in front of a local audience: library display, community paper, town social feed. The placement is the evidence.', 'riskTolerance', 'an afternoon', 3)
on conflict (archetype_id, title) do nothing;
