# Report 8: GO/NO-GO Deep-Dive — Provider-Level NDIS Compliance & Audit-Evidence Service

**Concept under validation:** support workers record voice notes after shifts → AI produces compliant progress notes AND the system maintains the provider-level audit stack — incident register with built-in 24-hour reportable-incident logic and NDIS Commission notification drafts, training/competency registers, complaints register, one-click audit evidence packs mapped to NDIS Practice Standards, quarterly mock-audit reports. Pricing ~$999 setup + ~$299/month. Target: registered NDIS providers with 5–50 support workers. Founder: solo developer, Australia-based, not from the NDIS industry, sales-averse.
**Method:** 21 web searches across competitors, channels, regulation, market data, and demand signals.

---

## 1. Competitive sweep at the provider level

### The most important finding first

The earlier research conclusion that "the provider-level audit stack appears open" is **stale**. In the last ~18 months, at least four purpose-built compliance-layer products have launched into exactly this gap, riding the mandatory-registration reform:

| Product | What it is | Pricing | Fit for 5–50 workers |
|---|---|---|---|
| **Checkbase** ([checkbase.com.au](https://www.checkbase.com.au/pricing)) | "Compliance-first, not CRM… the evidence layer under whatever rostering tool you already use." Staff document tracking, participant files, audit-log, certification-audit evidence-pack export, auditor portal. Explicitly targets **1–50 staff providers** | $149/mo (≤20 participants), $291/mo (≤75), $583/mo (≤250), billed yearly; self-serve, no lock-in | **Direct head-on competitor** — ~80% of the proposed product minus the AI voice-note layer and mock-audit reports |
| **FormaOS** ([formaos.com.au](https://www.formaos.com.au/pricing)) | "Compliance OS": Practice Standards pre-built, **24-hour SIRS countdown timers, Commission notification workflow, one-click audit evidence packs**, AU-hosted, immutable audit log | $297/mo (10 users), $797/mo (25 users), $1,800/mo unlimited | Direct competitor at identical price point. Notably: solo bootstrapped founder in Adelaide since 2022, whose [customer-stories page](https://www.formaos.com.au/customer-stories) admits the case studies are "illustrative scenarios… not anonymised customer histories" — a signal that even a strong solo-built product is struggling to convert in this market |
| **Willow AI** ([heywillow.ai](https://heywillow.ai/)) | AI "compliance intelligence layer" over existing systems; recruiting compliance consultants into a tiered [partner program](https://heywillow.ai/partners/overview) | "Most customers from around $15k per year and up" | Priced above the 5–50 segment, but actively locking up the consultant channel |
| **RomeoHR** ([romeohr.com](https://romeohr.com/audit-and-compliance)) | All-in-one workforce platform; invoice-linked audit packs, AI cross-checks for missing notes/overdue incident reports | Quote-based | Bundles compliance with operations |

Consultants have also productised:
- **Centro Assist** ([centroassist.com.au](https://www.centroassist.com.au/ess-subscription)) — cloud QMS with 50+ audit-ready policies, registers, internal-audit tools, 250+ obligations mapped. Core module **$1,900 + GST/year**; "hundreds of providers."
- **NDISCompliant** ([ndiscompliant.com.au](https://ndiscompliant.com.au/blog/best-ndis-software-providers)) — 74-document audit-mapped SIL kit plus a **free AI notes rewriter** as a lead magnet; heavy SEO content machine.
- **Provider+ / Provider Path** — consulting + mock audits at $2,500–$7,000 per engagement; Provider Path's [terms](https://providerpath.com.au/terms-and-conditions/) explicitly disclaim audit outcomes.

### The operational platforms

All now claim "compliance," but they do the *operational* job, not the *certification-evidence* job — NDISCompliant's buyer's guide makes the distinction explicitly: "most NDIS software platforms do not provide the actual policy documents, procedures, and registers required for a certification audit."

- **ShiftCare** — $9/$15/$25 per staff/mo (5-staff min); incident management gated to Premium; now shipping AI features (note-completeness checks, handover summaries) ([pricing](https://shiftcare.com/pricing)).
- **Brevity** — incident register in all tiers from ~$4.49/client/mo; ISO 27001-certified ([pricing](https://www.brevity.com.au/pricing/)).
- **SupportAbility** — **30-staff minimum**, annual up-front billing — poor fit below ~30 staff ([pricing](https://www.supportability.com.au/subscriptions/)).
- **Astalty** — $64/standard user + $30/support worker/mo; "stay audit-ready every single day"; 1,400+ NDIS businesses ([pricing](https://astalty.com.au/pricing)).
- **Lumary** (Salesforce enterprise), **Careview**, **GoodHuman**, **Flowlogic**, **VisiCase** ($1,500 setup + $25/user/mo, 10-user min), **MYP**, **iinsight** — mid/large or niche.

### Gap analysis — what remains genuinely open

1. **Nobody connects the worker layer to the audit layer.** Worker-note AI apps stop at the note. Evidence-layer tools (Checkbase, FormaOS) track documents but don't *generate* evidence from daily work. The proposed mechanic — voice note → compliant note → auto-populated incident register → notification draft → evidence pack — has no direct equivalent found in 21 searches.
2. **Mock-audit reports as a productised deliverable** — consultants charge $3,000–$7,000; no software subscription found that ships a quarterly mock-audit report.
3. **The sub-$150/mo to ~$300/mo band for micro providers (5–15 workers)** is contested only by Checkbase Essential.
4. **$299/mo is market-plausible** (Checkbase $291, FormaOS $297) and **$999 setup is cheap** relative to consultants ($2,500–$7,000) — arguably underpriced.

## 2. Buyer reality: inbound channels

- **ndipreneur:** 20,000+ professionals, ~14,000-member moderated Facebook group; education-first, anti-exploitative culture; has a **formal sponsorship and partnership channel** advertising "unparalleled access to over 11,500 NDIS providers" ([sponsorship](https://ndipreneur.au/sponsorship-opportunities/)). The route in is paid sponsorship + genuine educational contribution.
- **Whole Warrior Network:** state-based Facebook groups that **explicitly permit promotion** — members "connect, share experiences, and promote their services"; their newsletter explicitly welcomes "software or service suppliers" for collaboration and has itself recommended software systems to members ([wholewarriorsolutions.com.au](https://www.wholewarriorsolutions.com.au/wholewarriornetwork.html), [April 2026 newsletter](https://www.wholewarriornetwork.com.au/newsletters/whole-warrior-insider/posts/whole-warrior-network-insider-april-2026-edition)).
- **Proof vendors acquire customers this way:** Astalty bootstrapped to 1,400+ provider organisations largely through sector communities, word-of-mouth, and podcast presence ([The Profitable NDIS Provider episode](https://profitablendisprovider.podbean.com/e/s6-ep-64-stop-treating-symptoms-and-use-software-to-solve-the-core-problem/)). NDISCompliant runs the free-tool-as-lead-magnet play.
- **Caution:** *participant-facing* NDIS Facebook groups have a documented vendor-spam backlash ([DHD Consultancy](https://www.dhdconsultancy.com.au/post/the-facebook-groups-monster-how-social-media-created-an-ugly-beast-in-the-ndis)). B2B provider groups are more tolerant, but value-first conduct matters.
- **Expos:** mostly participant-facing; booths $600–$7,900. Low priority.
- **Consultant partnerships:** validated and active — so active that Willow AI is racing to lock up the channel with a founding-partner program. Precedents: Inficurex's 15–25% recurring-commission affiliate program, MyCareSpace cross-promoting Centro Assist. **Consultants will refer and white-label — the question is whether you sign them before Willow and Checkbase do.**

## 3. Regulatory / liability check

**"The tool failed my audit" risk — real but manageable.** Consultancies explicitly disclaim audit outcomes. However, under the **Australian Consumer Law**, business customers buying services under $100,000 are "consumers": guarantees of due care/skill and fitness for purpose **cannot be excluded**; blanket disclaimers are unenforceable. Standard mitigation: cap liability to resupply under ACL s64A + professional indemnity / tech E&O insurance ([Lawzana](https://lawzana.com/articles/australia/your-australian-b2b-saas-contract-compliance-checklist-1268), [SLB Legal](https://www.slblegal.com.au/selling-saas-into-australia-key-contract-and-legal-requirements)).

**The sharpest edge is the 24-hour reportable-incident logic.** Penalties for late notification are severe: Lifestyle Solutions fined $2.5M including $500k for 1,811 late incident reports; Oak Tasmania $1.1M for 474 contraventions ([2026 compliance buyer's guide](https://www.beyondhimalayatech.com.au/blog/the-2026-ndis-compliance-software-buyers-guide-for-australian-providers)). Design implication: the system must be *decision support*, not decision-maker — bias to "when in doubt, this may be reportable," require named human confirmation with timestamps. ShiftCare explicitly states it "does not submit reports directly to the NDIS Commission" — the safe posture is drafting the notification, not lodging it.

**Privacy.** Participant records are **sensitive/health information** under the Privacy Act 1988: APP 11 security obligations, APP 8 cross-border disclosure liability, Notifiable Data Breaches scheme ([NDISCompliant guide](https://ndiscompliant.com.au/blog/ndis-digital-record-keeping-guide)). No absolute AU-residency mandate in the Privacy Act itself, but AU hosting is the unambiguous market norm. **The AI layer is the trap:** sending voice audio of participant interactions to an offshore LLM API is an APP 8 problem. Use AU-region inference (AWS Bedrock/Azure OpenAI in Sydney) and put it in the DPA.

**Certification barriers.** ISO 27001 is only *mandated* for direct NDIA API integration — which this product doesn't need. Small providers buy self-serve (Checkbase and FormaOS sell via Stripe with no security review). But competitors weaponise certifications in marketing; a published security page + AU hosting + Essential Eight alignment is sufficient for 5–50-worker buyers initially.

## 4. Market dynamics

**Segment size.** 17,717 registered providers vs 264,970 unregistered (NDIA Q3 2025-26 quarterly report). Realistic 5–50-worker registered slice: 5,000–8,000 organisations; at ~$3.6k/year that's a ~$20–30M serviceable market — small for VC, entirely adequate for a solo developer needing 30–100 customers.

**The tailwind is real and verified — bigger than earlier research assumed:**
- **1 July 2026 (in force now):** mandatory registration for SIL and platform providers; unregistered SIL providers must apply by **1 October 2026** ([ndis.gov.au](https://www.ndis.gov.au/news/11596-crackdown-sales-ndis-businesses-mandatory-registration-set-expand-1-july)).
- **1 July 2027:** mandatory registration expands to **all high-risk supports (personal care, daily living)** — funded in the 2026-27 Budget — with all in-scope providers registered by December 2030 and a target of 90% of NDIS payments flowing to registered providers ([DoHDA timeline](https://www.health.gov.au/resources/publications/securing-the-ndis-for-future-generations-timeline-0?language=en)).
- That means a multi-year wave of thousands of currently unregistered providers building incident registers, training registers, and audit evidence **for the first time**.

**The headwind is also real.** Margins for 15–30-participant providers are 5–12%; sector operating result is negative (−4.7%, StewartBrown FY24 — [report](https://stewartbrown.com.au/images/documents/StewartBrown_-_FY24_Disability_Services_Financial_Benchmark_Report_.pdf)); ~21% of providers exited in the past year; the 2026-27 Pricing Schedule freezes most prices while award wages rise 4.75%; NDIS insolvencies climbing ([RSM report](https://content.rsm.com.au/rs/897-ZGB-534/images/2025-NDIS%20Insolvency%20report.pdf)). Providers are cost-cutting — but compliance spend is **non-discretionary once registration is mandatory**, and $299/mo substitutes for $2,500–$7,000 consultant engagements and the 200–400 staff-hours of audit prep Checkbase quotes. Sell it as spend *replacement*, never as an add-on. Expect churn from customer insolvency regardless of product quality.

## 5. Demand signals

- **Six-plus companies invest in SEO content clusters** targeting "NDIS audit checklist" etc. — NDISCompliant, Willow, SafetyCulture, Inficurex, ClinicComply, ShiftCare ([example](https://heywillow.ai/ndis-audit-checklist)). Companies don't build competing content clusters on zero-traffic keywords.
- NDIS-specialist SEO agencies confirm: compliance keywords are **low-volume but very high intent**, converting at 10–20x generic terms, with meaningful organic enquiry at the 6–9-month mark ([ndiswebsitedesigns.com.au](https://ndiswebsitedesigns.com.au/seo-for-ndis-businesses.php)).
- **Consultants currently solve it with spreadsheets and document kits**: 74-document template kits, $500–$5,000 policy packs. Checkbase's founding premise is literally "why do so many NDIS providers run their compliance on spreadsheets?"
- Auditors reconcile the incident register against Commission notifications; incident management is "one of the most common audit failures" — the pain the product addresses is the pain auditors actually test.

## 6. Honest comparison: outsider credibility

- **Winners are insiders or insider-paired.** Astalty = ex-provider director (8 years) + engineer; "built by people working inside the sector" is their core message, and it worked ([origin story](https://astalty.com.au/articles/origins-of-astalty)). Willow markets itself as "built by operators."
- **The cautionary tale is FormaOS**: a technically impressive compliance OS built solo since 2022 by a non-industry engineer — bootstrapped, feature-rich — whose customer-stories page still contains only "illustrative scenarios," not real customers. That is precisely the trajectory a solo outsider dev risks: great product, no trust, no distribution.
- Compliance is an *interpretive* domain where buyers want to know a person who has sat through audits stands behind the logic.

**Conclusion: a consultant partnership is near-mandatory** — at minimum (a) a named ex-auditor/consultant who reviews and endorses the register logic and mock-audit format, and (b) 1–3 registration consultants on revenue share who bring clients. This fixes credibility, content authority, and distribution simultaneously — and it's urgent, because Willow is signing exactly these partners now.

---

## Verdict: **GO-WITH-CHANGES**

**Reasoning.** The demand thesis is verified and stronger than assumed: mandatory registration is law-in-motion, incident management is the most commonly failed audit area with seven-figure penalties for notification failures, and providers currently pay consultants $2.5k–$7k plus $3k–$15k+ audit costs per cycle to solve this with spreadsheets. Willingness-to-pay at ~$299/mo is corroborated by three competitors priced at $149–$797/mo.

But the core premise "provider-level audit stack is open" is no longer true — Checkbase, FormaOS, Willow, Centro Assist and RomeoHR are all in-market as of mid-2026, and Willow is locking up the consultant channel. A straight GO on the original plan (solo outsider, self-branded compliance authority) would likely reproduce FormaOS's outcome: good product, no customers.

**Required changes:**
1. **Lead with the audit stack, not AI notes.** AI note apps are commoditising fast. Voice notes are the *evidence-capture moat* inside the compliance product, not the headline.
2. **Partner with compliance consultants before launch** — one named ex-auditor validating the register logic; 1–3 registration consultants reselling on 15–25% recurring revenue share.
3. **Position the $999 setup as a "registration/audit readiness package"** competing against $2.5k–$7k consultants — and consider raising it.
4. **Liability-harden the incident logic**: decision-support framing, notify-by-default bias, mandatory human sign-off, ACL-compliant terms, professional indemnity + tech E&O insurance, AU hosting including AU-region AI inference, documented breach-response plan.
5. **Time the go-to-market to the July 2027 high-risk-supports registration wave** — a far larger cohort than SIL — while using late-2026 SIL registrants as first design partners.

## Sharpest wedge / positioning

**"Your workers talk after every shift; your audit evidence writes itself."**

Target: **unregistered personal-care and daily-living providers who must register from 1 July 2027, plus newly-registered SIL providers facing their first mid-term audit** — 5–25 workers, no quality manager, currently on spreadsheets.

Differentiation in one line each:
- vs **Checkbase/FormaOS** (evidence trackers): they track documents you upload; this *generates* the evidence — nothing to remember to upload.
- vs **worker-note AI apps** ($49/mo): they stop at the note; the provider still fails the audit.
- vs **consultants/document kits**: templates are static; auditors reconcile registers against reality — this keeps registers contemporaneous automatically, and the quarterly mock-audit report replaces a $3k–$7k engagement.

## First 10 customers without cold calling

1. **Sign one consultant credibility partner (weeks 1–4).** Approach 5–10 registration/audit consultants with: free lifetime licence, "Reviewed by [name], ex-NDIS Quality Auditor" co-branding, 20% recurring revenue share. **Expected: 3–5 customers** from the consultants' active registration pipelines.
2. **Two free tools as lead magnets (weeks 2–8).** (a) A free *reportable-incident classifier* — answer 6 questions, get "likely reportable within 24 hours / 5 days / not reportable" with the Rules citation; (b) a free *audit-readiness scorecard*. Both are SEO plays on validated long-tail queries. **Expected: 2–3 customers** over 3–6 months.
3. **ndipreneur sponsorship + one compliance workshop (months 1–3).** "What auditors actually reconcile in your incident register." **Expected: 2–3 customers.**
4. **Whole Warrior Network groups (ongoing).** Promotion explicitly allowed; answer compliance questions with substance; pursue the newsletter's open invitation to software suppliers. **Expected: 1–2 customers.**
5. **Podcast guesting (months 2–4).** Pitch the July-2027 registration wave angle — newsworthy, not salesy. **Expected: 1–2 customers.**
6. **Two design partners at 50% for 12 months** in exchange for a named case study and audit-outcome data. Real customer stories are precisely what FormaOS lacks.

## Top 5 risks with mitigations

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | **Competitor consolidation** — Checkbase owns the same segment with a head start; Willow is signing the consultant channel; ShiftCare/Astalty can bundle "good-enough" compliance | High | Move fast on consultant partnerships (the channel is the scarce asset, not the code); differentiate on evidence *generation*; target the 2027 wave cohort before it becomes anyone's install base |
| 2 | **Incident-classification liability** — a mis-screened reportable incident leads to Commission penalties; ACL guarantees can't be disclaimed for sub-$100k B2B sales | High | Decision-support design with mandatory human confirmation and notify-by-default bias; ex-auditor review of the rules engine; liability capped to resupply (s64A); PI + tech E&O cover; immutable confirmation log |
| 3 | **Outsider credibility gap** (the FormaOS trajectory) | High | Named consultant/ex-auditor endorsement on every asset; sell audit *outcomes* via early case studies; let partners front sales conversations |
| 4 | **Customer fragility** — 5–12% margins, 21% annual provider exits; buyers may default to $500 template kits | Medium | Price as replacement for consultant/audit-prep spend with an explicit ROI page; monthly billing, no lock-in; the mock-audit report as the recurring-value artifact templates can't produce |
| 5 | **Privacy/AI processing failure** — voice recordings of participant interactions are sensitive health information | Medium | AU-region hosting *and* AU-region LLM inference from day one; encryption, MFA, RBAC; documented NDB response plan; published security page and DPA |
