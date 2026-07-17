# Handoff: Boostly → Voice-to-Report Pivot

**Purpose of this document.** This is a full-context handoff from a prior research conversation (Cursor cloud agent on the `Alfred` repo, July 2026). Give this file to the agent working in the `boostly` repo as its first message or attachment. It contains: who the founder is, what was researched and decided, why Boostly is being repurposed rather than finished, the target product spec, and the agent's immediate task.

---

## 1. The founder and the constraints

Solo developer (Australia-based). Previous project — **Boostly, this repo** — connected multiple marketing platforms (Meta, Google, TikTok, YouTube) through APIs and used AI to manage marketing for local businesses ("Maria the bakery owner" persona). It was abandoned mid-build because the integrations, OAuth/app-review requirements, platform restrictions and ongoing maintenance made it too hard for one person to build, launch and support.

The next product must, in the founder's own criteria:

- Solve a problem businesses **already experience regularly** (an unavoidable task, not a new habit)
- Be easy to explain and demonstrate
- Require **little or no integration** with the customer's systems
- Avoid enterprise buyers, IT departments, procurement, security reviews
- Be purchasable directly by a local business owner
- Deliver value from simple inputs: **voice notes, documents, photos**
- Suit a **productised-service model**: ~$999 setup fee + ongoing monthly fee
- Be realistic for one developer to build, launch, market and maintain
- **Critical personal constraint: the founder is bad at sales.** Distribution must be inbound/low-touch: marketplaces, communities, SEO, demos-that-sell-themselves, or reseller partners. No cold calling.

## 2. What was researched (July 2026)

Eight deep research passes (~130 cited web searches): SMB pain-point mining; competitive landscape across 8 product categories; pressure-test of 3 seed ideas; productised-service business models and case studies; vertical willingness-to-pay ranking (AU + US); inbound sales channels; and two GO/NO-GO validation dives on the top concepts.

Full reports live in the **Alfred repo** (private), branch `cursor/deep-market-research`, folder `market-research/` (PR: https://github.com/andrewcornell2000-Work/Alfred/pull/4):

| File | Contents |
|---|---|
| `01-pain-points.md` | 32+ unavoidable admin/compliance pains with evidence and severity ratings |
| `02-competitive-landscape.md` | 8 categories: incumbents, real pricing, complaints, exploitable gaps |
| `03-seed-ideas-pressure-test.md` | Validation of training-platform / voice-to-report / smart-intake ideas |
| `04-productised-service-models.md` | 15 case studies; channels ranked by sales skill required; pricing psychology |
| `05-vertical-willingness-to-pay.md` | 15 verticals scored on compliance-forced spend (AU + US) |
| `06-sales-channels-inbound.md` | Every buyers-come-to-you platform, with fees and evidence |
| `07-validation-security-voice-to-report.md` | GO/NO-GO dive on the chosen idea (verdict: GO-WITH-CHANGES) |
| `08-validation-ndis-audit-stack.md` | GO/NO-GO dive on the runner-up (held in reserve) |
| `09-top-5-ideas-and-recommendation.md` | **Main deliverable**: scoring matrix, top-5, recommendation, MVP spec, GTM plan |

## 3. The decision

**Build: a voice-to-report service for small security guard companies (5–30 guards).**

A guard finishes a patrol/shift or handles an incident and sends a **voice note** — via WhatsApp, SMS/MMS, or a QR-code browser recorder (nothing to install). AI converts it into the security firm's **branded, timestamped, client-ready Daily Activity Report (DAR) or incident report PDF**, automatically delivered to the firm's client (property manager, strata, event venue) and archived with the original audio + verbatim transcript + guard one-tap confirmation as a **court-ready evidence chain**.

**Pricing:** $999 done-for-you setup (branded templates, report formats, client delivery list, guard roster) + **$199–299/month flat per company** (never per-user). Month-to-month, 14-day money-back.

**Key evidence behind the choice** (full citations in reports 03, 05, 07):
- DARs are **contractually mandated** and incident registers are **statutory** in AU (kept 3 years, open to police inspection) — the buyer doesn't need persuading, which neutralises the founder's sales weakness. Pitch: "your contracts already require this; here's an easier way to comply."
- The **exact price shape already exists**: incumbent Silvertrac charges $249/mo + a mandatory $842–1,404 setup fee on 12-month contracts, with an app guards must learn.
- **Guard turnover is 77–300%/year**, which breaks every app-based competitor (constant re-onboarding) and makes "no app, just a voice note" a durable moat.
- The voice-note→client-ready-PDF wedge is **unoccupied in AU/US** (validated July 2026; closest analogues: FieldOps in EU, GuardSync in AU strata, Trackforce's text-polish AI). Window estimated in quarters — speed matters.
- The fee is 0.3–1% of a small firm's revenue (one guarded site bills $15–20k/month).
- **The demo is the sale**: a prospect sends a voice note to a demo number and receives their own branded PDF back in minutes.

**Architecture requirement:** build the engine generically — *voice/photos in → structured, branded compliance document out* — so later verticals are template packs, not new products: commercial cleaning proof-of-service (#4 ranked), AU trades site-paperwork/SWMS (#3), done-for-you staff training portals (#5, cross-sell into the same high-turnover customers). NDIS audit-evidence (#2) is documented in report 08 but parked (crowding + requires an industry-consultant partner).

**Also considered and rejected:** an iPhone voxel game with IAP (median indie mobile game earns <$50/month; 1-in-100 reach $10k/month; needs paid UA at $4+ CPI — a worse sales problem, not a better one), and **finishing Boostly as-is** (see §4).

## 4. Why Boostly is being repurposed, not finished

The founder proposed finishing Boostly (possibly cut down to Meta + Google only). Assessment from the research:

1. **The platforms are eating the product.** Meta Advantage+ and Google Performance Max auto-generate ad creative natively, free, inside the dashboards the customer already uses. Cutting TikTok/YouTube leaves Boostly competing directly against the two platforms most aggressively absorbing its core feature.
2. **Gatekeepers remain.** Meta app review + business verification and the Google Ads API developer-token process are waiting/policy games AI assistance can't compress, plus a permanent API-maintenance treadmill.
3. **Wrong sale for this founder.** "AI improves your marketing" is a discretionary, promise-based pitch with brutal SMB churn (adjacent services see 8–12% *monthly*), in the most saturated AI category for SMBs (GoHighLevel agencies, AdCreative.ai, Ocoya, Predis…).

**The salvage plan — reuse, don't sell, don't finish:** Boostly's codebase contains weeks of product-agnostic SaaS work: Next.js App Router shell, auth, Stripe billing, onboarding flows, a polished UI system (coral/cream theme, shadcn/ui, Tailwind v4), and hard-won patterns. Keep that skeleton; delete the marketing core (platform OAuth, ad APIs, campaign logic); build the voice-to-report product inside it. Boostly-the-product is parked, not killed; Boostly-the-codebase makes the new product ship in weeks instead of months.

## 5. MVP spec (what to build)

1. **Capture (all three from day one — WhatsApp alone reaches only ~49% of Australians):**
   - WhatsApp Business API (voice notes in)
   - Twilio SMS/MMS (voice memo attachments)
   - No-login mobile-web recorder reached via QR code / link (per-guard or per-site tokens)
2. **Pipeline:** transcription → structured extraction into the firm's report template (structure-don't-invent prompting; low-confidence segments flagged, never guessed; AI follow-up prompt if required fields are missing, e.g. "you didn't mention headcount") → guard one-tap confirmation → branded PDF → auto-delivery to the firm's client by email + archive.
3. **Evidence chain as the headline feature:** original audio + verbatim transcript + AI draft + guard-confirmed final, all retained and exportable. Marketing line: "court-ready with the evidence attached." (This pre-empts the AI-report liability critique — see the Axon Draft One / King County controversy covered in report 07.)
4. **Owner dashboard:** report archive with search, client list and delivery rules, template/branding settings, guard roster, monthly value summary (reports generated, hours saved — the retention mechanism; ~43% of SMB churn happens in the first 90 days).
5. **Report types:** Daily Activity Report, incident report, shift/handover note — AU-appropriate formats first (existing template content online is almost all American; this is an SEO gap).
6. **Productised onboarding:** a fixed-scope intake form (logo, report formats, client emails, guard roster) that the founder turns into a configured instance — the $999 deliverable, templated so each new customer costs hours, not days.
7. **Stack guidance:** keep Boostly's Next.js + Tailwind + shadcn foundation; Supabase or equivalent Postgres/auth/storage; Twilio + WhatsApp Business API; LLM API with AU-region inference available; server-side PDF generation. One deployable app.

## 6. Go-to-market (for later, but shapes the build)

- **Demo phone number** on the landing page: owner sends a voice note about last night's shift → gets their own branded PDF back in minutes. Build this flow early; it is the sales pitch.
- **Fiverr + Upwork Project Catalog** listings for the $999 setup as a productised gig (buyers click buy; 10–20% fee is the outsourced sales team).
- **Template lead-magnet SEO:** free AU-specific DAR + incident-report templates; every incumbent farms this keyword cluster (proof it converts).
- **First 10 customers** (no cold calls): demo number + founding-customer pricing (setup waived for first 3 AU firms for case studies); artifact-led outreach using the NSW public security Master Licence register (Excel export + free API) and Victoria Police register — send a branded template in their livery, not a pitch; helpful presence in r/securityguards and owner communities; ASIAL supplier channels; security-podcast guesting. Full plan in report 07.
- **Later:** white-label resellers (insurance brokers, agencies) keeping 30–40% of the monthly fee.

## 7. The immediate task for the agent in the boostly repo

**Audit first, then refactor. Do not start deleting on day one.**

1. **Audit the codebase.** Map what exists: app structure, auth, billing/Stripe state, onboarding, UI system, and every marketing/platform integration (Meta/Google/TikTok/YouTube OAuth, ad-creation features, campaign logic). Assess completeness and identify anything ready-to-ship vs. half-built.
2. **Produce a keep/delete/adapt inventory:**
   - **Keep:** app shell, auth, billing, onboarding patterns, UI components/theme (re-skin later; structure first), deployment config.
   - **Delete:** all ad-platform integrations, OAuth flows for marketing platforms, campaign/ad-generation features, the Maria persona product surface.
   - **Adapt:** landing page → security-vertical positioning; onboarding → the $999 intake flow; any generation-quota/usage patterns → report-usage metering.
3. **Write the refactor plan** (a markdown doc in the repo) sequencing: strip marketing core → rename/rebrand scaffolding → build capture channels → pipeline → evidence chain → dashboard → demo-number flow. Then execute it incrementally with working checkpoints.
4. **Naming:** the new product needs its own name/brand (decide with the founder; don't ship as "Boostly"). Keep the brand config centralised (`lib/brand.ts` already exists for this).

## 8. Reference links

- Research PR (all 9 reports): https://github.com/andrewcornell2000-Work/Alfred/pull/4
- Main deliverable: https://github.com/andrewcornell2000-Work/Alfred/blob/cursor/deep-market-research/market-research/09-top-5-ideas-and-recommendation.md
- Security validation dive: https://github.com/andrewcornell2000-Work/Alfred/blob/cursor/deep-market-research/market-research/07-validation-security-voice-to-report.md
- Inbound channels: https://github.com/andrewcornell2000-Work/Alfred/blob/cursor/deep-market-research/market-research/06-sales-channels-inbound.md
- Key market anchors: Silvertrac pricing ($249/mo + $842–1,404 setup): https://www.therms.io/blog/therms-vs-silvertrac-complete-comparison-guide-for-security-guard-management-software/ · NSW security licence register (target list): https://verify.licence.nsw.gov.au/home/security · Guard turnover data: https://www.dronestrategicpartners.com/post/the-security-guard-shortage-why-turnover-is-accelerating-the-shift-to-automation · AI-report liability precedent: https://pceinc.org/wp-content/uploads/2025/01/20240920-Email-to-Police-Chiefs-re-Axon-Draft-One-King-County-Prosecuting-Attorney-Dan-Clark.pdf

*(The Alfred repo is private — links work for the repo owner. If this agent can't fetch them, ask the founder to paste the specific report needed.)*
