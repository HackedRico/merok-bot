# Prior art for the two merok-bot phenomena

Checked September 18, 2026. Extends the "Has it been done" table in the calcifer.md research
doc, which covered the product half (voice drafting, traction prediction). This note covers
the two phenomena the pitch rests on.

## Phenomenon 1: templates spread, not posts

Method is old. Measurement on this data is new.

| Work | What it did | What it leaves open |
|---|---|---|
| Leskovec, Backstrom, Kleinberg, "Meme-tracking and the dynamics of the news cycle" (KDD 2009) | Clustered short phrases and their mutations across 900k news and blog posts a day, plotted volume over time, named the shapes of the curves | News and blogs, not X. Volume, not distinct authors. No engagement. The judge will know this paper; name it. |
| Sweed and Shahaf, "Catchphrase: automatic detection of cultural references" (ACL 2021) | Detects snowclones, the "X is the new Y" phrasal templates, against a quote corpus | Needs a seed corpus. Our templates are mined bottom-up from repetition. |
| Coordination literature: Pacheco et al. 2021 framework, Schoch et al. "Coordination patterns reveal online political astroturfing" (Sci Rep 2022) | Exact and near-duplicate text across accounts as a coordination signal | Treats every replicated text as suspect. We want the opposite split: which replication is organic. |
| Shafin and Ahmed, "Not all duplicates are coordination: generic vs non-generic duplicate campaigns" (arXiv 2609.13671, September 12, 2026) | 187k tweets from six Russian IO datasets. Splits duplicate campaigns into generic (reusable low-information copy) and non-generic. Generic campaigns are 39 percent of embedding-found clusters and rare under exact match. Filtering them out yields a denser coordination graph. | Six days old. Their "generic" bucket is our meme bucket. Cite it for the spam versus organic split: same signal, opposite question. |
| Twitter's 2020 copypasta policy | Platform hid verbatim reposts | Evidence the platform itself treats verbatim replication as one class. We show two. |

Nobody has run phrase-cluster mining over a September 2026 X firehose sample with engagement
trajectories, and nobody frames the generic-duplicate split as organic meme versus paid
replication. Pitch line: MemeTracker for X in 2026, with the split the September 2026 paper
says you need.

## Phenomenon 2: government learned to meme

Nobody has measured it. Everyone has described it.

| Work | What it did | What it leaves open |
|---|---|---|
| Pew Research, "Federal agency X accounts are getting far more engagement in the second Trump term" (June 1, 2026) | 24 agencies. Median likes plus reposts per post: 197 in 2024, 929 in 2025. DHS 57 to about 2,300. Vocabulary shifts ("American", "president", "criminal"). | Measured volume and words, not format. Did not touch memes or slang. |
| NBC, CNN, NPR (August 2025), CNN and Fortune (January 2026) | Qualitative: White House and DHS adopt trend formats, AI imagery, "the memes will continue" | Journalism, no baseline, no counts. |
| Chang et al., "The meme is the message: generative memesis" (arXiv 2411.00934) | 239k Instagram images, 2024 election. Meme format predicts engagement more strongly than AI generation does. | Images on Instagram, users not officials. Supports the premise that format carries engagement. |
| CRS reports R44081, R45337; Pew 2020 congressional social media | Adoption of platforms by members, engagement by party | Pre-meme era. Useful for the "before" baseline framing. |
| Sponsor's own "White House on X" slide | The claim, as an anecdote | Our chart is that slide with numbers. |

Gap confirmed. The chart nobody has drawn: for each official account, by month, the share of
posts that match a firehose template or a slang lexicon, against that account's own engagement
baseline.

Methodological trap, from Pew: engagement rose for nearly every agency after January 2025 for
reasons unrelated to format. A raw before-and-after conflates meme adoption with the regime
change. The baseline has to be per author and per period. Compare meme-format posts against
non-meme posts by the same account in the same month, or the finding is confounded and the
judge, who reads this literature, will say so.

## Product half

No change from the calcifer.md table. Tweet Hunter, Typefully and Hypefury draft and predict
as black boxes. The sponsor's own Digital Twin paper is the drafting method. Nothing new to
add.

## What this changes in the pitch

- Open with MemeTracker by name, then the 2026 curve. The judge teaches this; he will place it.
- Cite Shafin and Ahmed for the spam split. Six days old is a signal the team is current.
- Say "per-author baseline" out loud on the government chart, and say why Pew's number is not
  enough.

## Sources

- https://www.cs.cornell.edu/home/kleinber/kdd09-quotes.pdf
- https://snap.stanford.edu/memetracker/
- https://aclanthology.org/2021.acl-short.1/
- https://arxiv.org/abs/2609.13671
- https://www.nature.com/articles/s41598-022-08404-9
- https://www.pewresearch.org/short-reads/2026/06/01/federal-agency-x-accounts-are-getting-far-more-engagement-in-the-second-trump-term-than-under-biden/
- https://www.govexec.com/management/2026/06/federal-agencies-more-attention-social-media-more-criticism/414220/
- https://arxiv.org/abs/2411.00934
- https://www.nbcnews.com/politics/politics-news/white-house-social-media-2025-memes-ai-maga-messaging-rcna220152
- https://www.npr.org/2025/08/18/nx-s1-5482921/memes-white-house-dhs-social-media-trump
- https://fortune.com/2026/01/27/white-house-social-media-meme-misinformation-altered-images-videos/
- https://www.congress.gov/crs-product/R45337
- https://www.pewresearch.org/internet/2020/07/16/1-the-congressional-social-media-landscape/
