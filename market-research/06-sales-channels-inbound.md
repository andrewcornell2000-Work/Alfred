# Report 6: Inbound Sales Channels for a Sales-Averse Solo Founder

**Context:** selling an AI-powered productised service to small local businesses (~$999 setup + $50–300/mo). Critical constraint: "I'm not good at sales at all" — channels where buyers come to you, or where selling is near-passive.
**Method:** 24 web searches across marketplaces, gig platforms, white-label channels, directories, communities, and lead-gen platforms.

**Headline finding:** the three channel families where buyers genuinely come to you with money in hand are (1) **productised-gig marketplaces** (Fiverr/Upwork Project Catalog — buyers click "buy" with no sales call), (2) **reseller/white-label partners** (agencies, bookkeepers and coaches who already own local-business trust and do the selling for a 20–50% cut), and (3) **niche inbound SEO**, where demand for terms like "AI receptionist" has grown ~87x since 2019 ([UpFirst statistics](https://upfirst.ai/blog/virtual-assistant-statistics)). Most famous "launch" channels (AppSumo, Product Hunt, AI directories) reach deal-hunters and tech tinkerers, **not** local business owners.

---

## 1. Software/services marketplaces

### AppSumo — high volume, wrong economics, wrong buyer
- **Fees:** 30–70% revenue share; Net-60 payouts with refund reserves; platform-average refund rate ~17% ([Gatilab economics](https://gatilab.com/economics-of-lifetime-deals/)).
- **Evidence:** A 4-year LTD post-mortem: ~$90k total revenue but LTD customers "almost never upgrade… every active LTD customer is permanently a support customer at $0 ARPU" ([Indie Hackers](https://www.indiehackers.com/post/4-years-into-an-appsumo-lifetime-deal-the-unvarnished-math-and-a-question-i-m-stuck-on-4dd2b262ac)). WP Umbrella's founder: "if your costs scale with usage, you shouldn't do a lifetime deal, full stop" ([ScaleMath podcast](https://scalemath.com/podcast/should-you-run-a-lifetime-deal-aurelio-volle-wp-umbrella/)). "Lifetime deals are not revenue. They are debt." ([Alex Berman](https://alexberman.com/lifetime-deals-are-not-revenue-they-are-debt)).
- **Verdict: SKIP.** A productised *service* with per-client fulfilment cost and a monthly model is exactly the profile these sources warn against. Deals cluster at $49–199; buyers are solopreneur deal-hunters, not local plumbing companies.

### Shopify App Store — great terms, wrong product shape
0% on first $1M lifetime revenue, then 15% ([Shopify docs](https://shopify.dev/docs/apps/launch/distribution/revenue-share)) — but requires a real embedded app/integration, and buyers are e-commerce merchants, not local service businesses. **SKIP.**

### WordPress plugin directory — a 1–2% conversion grind
Only ~1% of 60,000+ plugins ever reach 10,000 installs; typical free→paid conversion 1–2%; realistic Year-1 CAC ~$1,100/customer ([Wilson & Keys report](https://www.wilsonkeys.com/evaluating-wordpress-plugins-and-its-500-million-sites-as-a-customer-acquisition-channel-report/)). **SKIP.**

### Wix / Squarespace app markets
Wix: 100% of revenue year one, then 80/20 ([Wix developer docs](https://dev.wix.com/docs/build-apps/launch-your-app/pricing-and-billing/about-monetizing-your-app.md)); Squarespace has no open marketplace. Requires integrated apps. **SKIP.**

### Xero / QuickBooks app stores
Exceptional *trust* (accountants recommend apps to clients) but mandate deep integration plus certification (Xero requires 10 live customers before listing — [Xero developer](https://developer.xero.com/grow-with-xero)). **SKIP as a listing channel — but steal the insight: the accountant/bookkeeper trust channel itself is accessible without any integration (see §3).**

### GoHighLevel marketplace — the sleeper B2B2SMB channel
- **0% commission on developer revenue until Dec 31, 2026**; agencies rebill your app to their local-business sub-accounts with their own markup ([GHL marketplace](https://www.gohighlevel.com/landing-marketplace)).
- **Snapshots** (pre-built configurations) sell for $97–$997; agencies report $1,500–$10,000/mo from snapshot sales; the GHL Facebook group (100k+ members) is an active buying audience ([gohighlevel.ai guide](https://www.gohighlevel.ai/blog/gohighlevel-marketplace)).
- **Verdict: TRIAL.** Buyers here are agencies who serve exactly the end market and *shop proactively*. Requires a light platform integration.

### Zapier app directory
Exists to market a software integration, not a done-for-you service. **SKIP.**

## 2. Productised-gig platforms

### Fiverr (incl. Fiverr Pro) — the purest "buyers come to you" channel
- **Fees:** flat 20% of every order ([Scalopa guide](https://scalopa.com/how-to-make-money-ai-fiverr-2026/)).
- **What AI gigs actually earn:** AI chatbot setup gigs start $75–150 with top sellers at **$3,000–8,000/mo**; custom-GPT building $150–400 with top sellers at **$3,000–10,000/mo** and *low competition* ([Scalopa data](https://scalopa.com/how-to-make-money-ai-fiverr-2026/)). Fiverr's own market data: AI chatbot projects average ~$216, custom GPT builds ~$341, advanced builds $500–1,500+ ([Fiverr cost guide](https://www.fiverr.com/resources/guides/costs/chatbot-developer)). Fiverr Pro chatbot developers charge **$500–$3,000+**; a real Pro seller lists packages at **$1,500 / $4,000 / $10,000** ([live gig](https://www.fiverr.com/eng_samerhany/build-ai-agents-chatbots-email-bots-integrations-internal-workflow)).
- **Why it fits:** buyers purchase from a listing like an Amazon product — zero sales calls. The $999 setup maps to a Premium package; the 20% fee is the cost of not having to sell.
- **Watch-outs:** cold-start (first 10 reviews) takes deliberate underpricing; the algorithm rewards fast response times.

### Upwork Project Catalog — same model, lower fee, bigger tickets
- **Fees:** ~10% flat ([Upwork Alerts](https://www.upworkalerts.com/blog/upwork-fees)).
- 290,000+ pre-scoped projects that clients buy without proposals. Catalog "beats proposals when the work is well-scoped, priced under $5,000… criminally underused" ([UpHunt analysis](https://uphunt.io/blog/upwork-project-catalog-2026-productized-services-vs-proposals)). Upwork's AI-services GSV exceeds $300M annualised ([aicap](https://aicap.in/fiverr-vs-upwork-ai-services-2026/)).
- **Verdict: ADOPT alongside Fiverr.**

### Contra — zero commission, but you bring the traffic
Low native client volume. **Use as a free portfolio/checkout page, not a demand source** ([Contra pricing](https://contra.com/pricing)).

### Legiit — niche marketplace where buyers are often *agencies* white-labelling services
15% seller fee; a listing here doubles as partner recruitment. **TRIAL, low effort** ([Legiit fees](https://intercom.help/legiit-online-marketplace-inc/en/articles/6503400-legiit-seller-fees)).

### Whop / Gumroad — checkout rails, not discovery
Fine as payment infrastructure for digital add-ons; **neither will deliver local-business buyers** ([group.app Whop review](https://www.group.app/blog/whop-review/), [Gumroad pricing](https://gumroad.com/pricing)).

## 3. Agency / reseller white-label channels — "they sell, he fulfils"

The strongest structural match for "I'm not good at sales": recruit a handful of partners once, then every subsequent sale is made by someone else.

- **Published splits:**
  - **Luxia** (Shopify ops automation): "We do 100% of the fulfilment. You take the credit (and the margin)" — agency keeps **60%** ([luxia.uk/for-agencies](https://luxia.uk/for-agencies/)).
  - **FlashCrafter** (websites+CRM for HVAC/plumbing/roofing agencies): **30% recurring margin** to the reselling agency ([flashcrafter.ai partners](https://www.flashcrafter.ai/agency/partners)).
  - **WildRun AI** (white-label AI receptionist): wholesale $99/seat/mo, agencies retail at $300–700/mo, **50–70% agency margin**; case study of an accounting firm reselling at $400–800/mo to 22 clients ([wildrunai.com/agencies](https://wildrunai.com/agencies)).
  - **OnCallClerk**: reseller charging $199/client/mo across 50 clients = **$119,400/yr at 80%+ margins** ([oncallclerk.com/white-label](https://oncallclerk.com/white-label)).
  - **BotHero's reseller survey:** referral/rev-share partners earn 20–40% of subscription; "the most successful resellers are marketers and business consultants, not developers" ([BotHero](https://blog.bothero.ai/chatbot-white-label-reseller-the-5-business-models-their-real-economics-and-how-to-pick-the-one-that-matches-your-situation)).
- **Who to recruit:** marketing agencies serving trades, **bookkeepers/accountants** (the single most powerful SMB referral channel — QuickBooks built a 250,000-strong ProAdvisor army on this trust dynamic; referral programs typically pay advisors 20%+ recurring — [GrowSurf examples](https://growsurf.com/examples/accounting-software-referral-programs/)), and business coaches/consultants who "have an audience but no desire to deliver."
- **The catch:** recruiting the first 3–5 partners *is* a sales activity — but it's a handful of peer-level conversations with people whose incentive is to say yes.
- **Verdict: ADOPT.** Concede 30–50% of revenue; the partner absorbs the entire sales function.

## 4. Directories & inbound SEO

- **Search demand is real and steep.** "AI receptionist" searches peaked at **87x their 2019 level**; HVAC/plumbing AI adoption jumped from 7–9% (2023–24) to 19–35% (2025–26) ([UpFirst stats](https://upfirst.ai/blog/virtual-assistant-statistics), [PipelineOn](https://pipelineon.com/blog/ai-tools-for-hvac-plumbing-contractors/)).
- **The winnable strategy:** target long-tail keywords with 50–500 monthly searches and difficulty <20 ("AI receptionist for plumbers", "staff training app for cleaning company"); first rankings ~month 3–6, compounding by month 12–18; comparison/bottom-funnel pages convert at 15–30% vs 1–3% for blog posts ([solo SaaS SEO playbook](https://www.promptstoproduct.com/seo-for-saas-playbook), [Ranking Lens](https://blog.rankinglens.com/saas-seo-0-to-1000-visitors)). Slow, but zero sales skill and near-zero cost.
- **Product Hunt: SKIP.** Audience is 67% founders/startup employees, ~2% business decision-makers. The definitive anecdote: "My users are dog groomers. They don't know what Product Hunt is… one user tagging me in a Facebook group generated 58 paying signups while I was eating dinner" ([Webmatrices thread](https://webmatrices.com/post/everyone-told-me-to-launch-on-product-hunt-my-users-are-dog-groomers-they-dont-know-what-product-hunt-is)).
- **There's An AI For That** ($49–347) and **Toolify** ($99, ≥6 dofollow DR-73 backlinks): audience is AI-curious tinkerers, not plumbers — **treat as cheap SEO backlinks, not buyer sources** ([TAAFT launch](https://theresanaiforthat.com/launch/), [Toolify submit](https://www.toolify.ai/submit)).

## 5. Community-based inbound (ranked by effort vs sales skill)

1. **Trade Facebook groups / niche subreddits — best effort-to-outcome ratio.** Documented results: SaveWise grew to $25k/mo purely via Reddit + Facebook groups (lurk → contribute → share a genuinely useful artifact) ([StackStarts](https://stackstarts.com/avnish-solopreneur-reddit-facebook-25k-month-business-2/)); MDZ.AI got 30% of early customers from 2 hrs/day of *helping, not selling* ([Starter Story](https://www.starterstory.com/stories/mdz-ai)); one Reddit post produced the first 100 users of a $60k-MRR app ([MRR Story](https://www.mrrstory.com/stories/he-got-his-first-100-users-from-one-reddit-post-now-hit-60k-mrr)). Sales skill required: writing helpful answers — no calls, no closing.
2. **Chamber of commerce:** $200–500/yr dues, credibility bump, but only 0–10 informal referrals/yr. Secondary at best. (BNI generates 15–20 referrals/yr at 60% close but demands weekly meetings and active reciprocal selling — wrong temperament fit.)
3. **Industry association preferred-vendor lists:** $650–$2,500/yr small, to $30,000+ national; "passive inclusion in a directory rarely yields significant ROI." Defer until there's revenue.
4. **Franchise expos / trade shows — worst fit.** All-in cost $18,000–45,000 for a regional 10×10; avg $112/lead; requires exactly the face-to-face selling this founder wants to avoid ([ExhibitionsVoice](https://exhibitionsvoice.com/blog/are-trade-shows-worth-it-complete-guide-2026)). **SKIP.**

## 6. Two-sided "businesses post problems" platforms

- **Bark.com: AVOID.** Pay-to-unlock shared leads ($5–50 each), shared with up to 5 competitors, ~14% close rate on responses ([WrenchStack review](https://wrenchstack.com/lead-gen/bark/)).
- **Thumbtack:** real demand flow but consumer home-services categories; no meaningful "AI automation for my business" request stream. **SKIP.**
- **Airtasker (AU):** demand skews to physical tasks; "Computers & IT" averages ~$280/task. **SKIP** as primary.

---

## (b) Ranked table — top 8 channels

Scoring 1–5. "Sales skill needed": **5 = almost none required** (better). "Fees/cost": 5 = cheapest.

| # | Channel | Buyer intent | Sales skill needed (5=none) | Fees/cost | Time to first sale | Fit for $999 + monthly | Total /25 |
|---|---|---|---|---|---|---|---|
| 1 | **Niche inbound SEO** (own site, long-tail vertical keywords) | 5 | 5 | 5 | 1 | 5 | **21**\* |
| 2 | **Fiverr (build toward Pro)** — 20% fee | 5 | 5 | 2 | 4 | 4 | **20** |
| 3 | **Upwork Project Catalog** — ~10% fee | 4 | 4 | 4 | 3 | 4 | **19** |
| 4 | **GoHighLevel marketplace + snapshots** — 0% commission until end-2026 | 4 | 4 | 5 | 3 | 3 | **19**† |
| 5 | **Trade Facebook groups / Reddit** (help-first) | 3 | 3 | 5 | 4 | 4 | **19** |
| 6 | **Agency/bookkeeper/coach white-label resellers** — give up 30–50% | 4 | 3 | 2 | 3 | 5 | **17** |
| 7 | **AppSumo lifetime deal** | 4 | 5 | 1 | 4 | 1 | **15** |
| 8 | **AI directories (TAAFT/Toolify)** | 2 | 5 | 4 | 2 | 2 | **15** |

\* SEO scores highest on paper but its 6–12-month time-to-first-sale means it can't be the *only* channel — it's the compounding layer.
† GHL requires accepting a light platform integration.

---

## (c) Recommended 3-channel stack

**Channel 1 — Fiverr + Upwork Project Catalog (cash now, zero selling).** List the identical productised offer on both; treat the 10–20% fees as an outsourced sales team.
1. One tightly-scoped offer with three tiers: ~$399 (starter, review-farming), ~$999 (the real setup), $2,500+ (premium with 3 months of monthly service bundled).
2. On Upwork, publish as a Project Catalog listing under $5,000 with a fixed delivery window.
3. First 30 days: respond to every enquiry within an hour, collect 10 reviews, then raise prices 2–3x.
4. Convert every marketplace buyer to the monthly retainer (via subscription gigs or off-platform once permitted) — the setup fee is the acquisition event; the monthly is the business.

**Channel 2 — Recruit 3–5 white-label resellers (they sell, he fulfils).** The recurring-revenue engine; the only "sales" ever needed is a few peer-level partner conversations.
1. One-page partner offer copying proven structures: partner keeps 40% of the monthly fee for life + 30% of the setup; fulfilment, support, updates are 100% yours.
2. Target, in order: (a) small marketing agencies already serving the vertical; (b) bookkeepers — the most powerful SMB referral channel, reachable through local meetups and advisor directories without building any integration; (c) business coaches.
3. Give each partner a co-branded one-pager and a demo instance. Five partners each selling 2 clients/month at $200/mo average = ~$1,200/mo of *new* recurring added monthly with zero direct selling.

**Channel 3 — Niche SEO site + help-first community presence (the compounding passive layer).** Start in week one; expect nothing for a quarter.
1. One topic cluster around the single best vertical: pillar page + 5–10 supporting pages targeting 50–500-volume long-tails, including comparison and cost pages (15–30% conversion).
2. Buy the cheap permanent listings once (Toolify $99, TAAFT $49) as SEO fuel.
3. 2–3 hrs/week in two trade Facebook groups and one subreddit answering questions with genuinely useful answers and a profile link.

**Explicitly deprioritised:** AppSumo (economics hostile to recurring services), Product Hunt (audience mismatch), Bark/Thumbtack (paid lead-chasing), integration-requiring app stores, trade-show booths. GoHighLevel is the best "next channel" once the first three are running.
