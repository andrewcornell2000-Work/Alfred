# Report 7: GO/NO-GO Deep-Dive — AI Voice-to-Report Service for Small Security Guard Companies

**Concept under validation:** guard finishes a patrol/shift, sends a voice note (no app install), AI converts it into a branded, timestamped, client-ready Daily Activity Report or incident report PDF with an audit trail, automatically delivered to the security company's client and archived. Pricing ~$999 setup + $149–299/month flat per company. Zero integrations. Founder: Australia-based solo developer, sales-averse.
**Method:** 23 searches across competitors, buyers, workflow, market size, demand signals, and risks.

**Verdict up front: GO-WITH-CHANGES.** The exact wedge is still unoccupied in Australia and the US, pricing is validated by incumbents, and the pain is real and documented. But two premises from earlier research need revision: (1) "nobody is doing AI voice-to-report for security" is no longer true globally — the window is open but closing; (2) WhatsApp-first needs an SMS/mobile-web fallback in AU/US, where WhatsApp reaches only ~30–49% of the population.

---

## 1. Competitive sweep

| Player | What they do | Voice AI? | App/hardware needed | Pricing | Threat level |
|---|---|---|---|---|---|
| [FieldOps (SenSec)](https://fieldops.sensec.ai/) | Full "system of record"; guards file **voice reports in any language**, AI normalises into audit-grade DARs | **Yes — closest concept match** | Own mobile app | ~US$80–450/site/mo + US$2,000 onboarding | High conceptually; but EU/GDPR-focused, platform-scale, app-based |
| [MIRA (Untrite)](https://untrite.com/mira/) | Voice-to-report, "court-ready documentation in seconds", SIA (UK) compliance | Yes | Platform | Quote-based | Medium; UK-centric |
| [Patrol 6](https://patrol6.com/) | AI body cameras that auto-generate shift reports from audio/video | Yes | **Hardware (bodycams)** | Hardware + SaaS | Low for the 5–30 guard segment (capex) |
| [Trackforce/TrackTik ReportPro AI](https://www.trackforce.com/reportpro-ai/) | "AI Enhance" turns guards' rough **typed** notes into polished reports; AI edits fully audit-logged ([help doc](https://support.tracktik.com/hc/en-us/articles/35460923009687-Understand-and-use-ReportPro-AI)) | Text-polish only, **no voice** | TrackTik app | Enterprise per-officer (~$15–25/officer/mo) | Medium-high — proof incumbents are moving; voice is their obvious next step |
| [Silvertrac](https://www.silvertracsoftware.com/detailed-security-activity-reporting) | Audio attachments + OS-level talk-to-text; **no AI report writing** | No | Own app | **$249/mo (10 devices) + $842–1,404 mandatory setup, 12-mo contracts** | Price-shape validation confirmed |
| [OfficerReports "OfficerIntelligence"](https://officerreports.com/ai-security-guard-software.html) | AI **summarises** existing DAR data for managers | Summarisation only | Own app | Quote | Low-medium |
| [GuardMetrics "AI Refine"](https://guardmetrics.com/security-guard-management-software-features-guardmetrics/) | AI grammar/clarity polish on incident reports | Text-polish | Own app + NFC checkpoints | Consultative | Low |
| [THERMS](https://www.therms.io/) | Client-ready reports, no AI writer | No | Own app | $45/mo (5 users) → $155/mo (30) — the budget anchor | Price pressure from below |
| [Novagems](https://novagems.com/security-guard-management-software/), Guardso, [Belfry](https://www.belfrysoftware.com/plans), [Celayix](https://www.celayix.com/) | Form-based reporting, scheduling, GPS; Belfry is VC-backed ($12M) with a huge SEO content operation | No voice AI found | Own apps | Per-user | Belfry = biggest medium-term threat (ships daily, owns the SERP) |
| [GuardSync AI](https://guardsync.ai/) (**Australia**) | QR-scan, **no-app** AI incident reporting; "end-of-shift and monthly reports generated automatically and delivered to clients"; claims 500+ sites AU/NZ | AI categorisation/summaries (QR + form, not voice-note-first) | No app (QR + browser) | ~$350/mo strata, ~$4,200/yr sites ([strata page](https://guardsync.ai/features/strata)) | **Highest local relevance** — validates no-app + AI + AU pricing, but is venue/strata/event-led, not guard-company-DAR-led |
| [Community Wolf](https://docs.communitywolf.com/docs/getting-started) (South Africa) | **WhatsApp-native guard ops** — "the hardware you need is already on site: a phone" | WhatsApp agents | **No app** | Quote | Proof the WhatsApp-native model works for guarding |

Also relevant: an entire cohort of **WhatsApp-voice-note-to-report startups in construction** — [Sifu](https://www.getsifu.ai/), [SendStatus](https://sendstatus.co/), [Jask Reporter](https://jaskreporter.com/), [Fieldcast](https://www.mobile2b.com/en/solutions/fieldcast), [clockin](https://www.clockin.ai/features/voice-to-report) — proving the "no new app, workers keep using WhatsApp, AI writes the branded PDF" mechanic is commercially replicable. Nobody has planted this flag in security guarding in AU/US.

**Bottom line:** incumbents' AI is *text-polish and summarisation inside their own apps*. The specific combination — voice note in a messaging channel the guard already has → branded client-ready PDF with audit trail → auto-delivered to the end client — is not offered by any of the ten named incumbents. The whitespace is real but measured in quarters, not years.

## 2. Buyer reality

**Where small security firm owners congregate:**
- **r/securityguards** — guards, not owners, but the definitive source of report-writing pain ("One guard wrote a 9-page thesis… reports missing critical details, overly wordy" — [Resolver](https://www.resolver.com/blog/physical-security-incident-reports/)).
- **Skool communities:** [Security Insider Strategies](https://www.skool.com/security-insider-strategies-4585) — run by Chris Anderson, *founder of Silvertrac* (note the channel conflict); [SNAP Academy](https://www.skool.com/snap-academy-3877) (free, for guard business owners).
- **[Security Owners Group](https://www.securityownersgroup.com/about)** — paid peer group for owners.
- **Associations:** [ASIAL](https://asial.com.au/Web/Web/About-Us/About-Us.aspx) is the AU peak body claiming ~85% of the industry, with a [member directory searchable by state, service, and company size](https://asial.com.au/Web/Member-Resources/Membership-Directory.aspx) — a ready-made target list. US: CALSAGA and state associations; ISC West/GSX skew to buyers/integrators.
- **Licensing registers are genuinely usable in Australia:** NSW's [public security register](https://verify.licence.nsw.gov.au/home/security) lists Master licence holders (security *businesses*), searchable, **Excel download**, and a [free public API](https://api.nsw.gov.au/Product/Index/24). Victoria Police maintains an equivalent [public register](https://www.police.vic.gov.au/register-licence-registration-and-permit-holders). Commercial lists exist ([poidata: 867 AU / 11,324 US listings](https://www.poidata.io/index.php/report/security-guard-service/australia)).
- **How they buy:** peer recommendation, association channels, content/SEO; case studies are "the most commercially valuable content asset" ([The Marketing Juice](https://themarketingjuice.com/digital-marketing-for-security-companies/)). Self-serve trials work at this price point (THERMS, Novagems prove it).

## 3. Workflow & objection check

**How guards report today at small firms:** handwritten/paper DARs remain common ("messy, handwritten DARs" is Silvertrac's own anti-positioning); unstructured **WhatsApp group chats are explicitly the status quo** competitors position against: Nexarisi sells against "Incidents managed over WhatsApp… a group chat that no one can search, audit, or use as evidence" ([source](https://nexarisi.com/industries/security/)); FieldOps against "the gap between supervisor memory, WhatsApp threads and Excel reconciliation." **The raw material already flows through messaging apps; nobody turns it into the contractual deliverable.**

**Messaging-channel reality (important correction):** WhatsApp reaches only ~**49% of Australians** and ~**30–33% of Americans** ([Exploding Topics](https://explodingtopics.com/blog/messaging-apps-stats), [Sinch](https://sinch.com/blog/whatsapp-in-the-us-potential/)). Mitigating nuance: guard workforces skew heavily migrant/diaspora, where WhatsApp share is far higher. **Conclusion: WhatsApp + SMS/MMS voice-memo + a no-login mobile-web record button must all work from day one.** GuardSync's QR-scan-to-browser pattern shows an app-free alternative capture path that works in Australia.

**What clients demand:** timestamped, contemporaneous, retrievable records. Australian strata/WHS obligations require incident records kept in retrievable form (WHS records ~5 years; "a text message thread does not meet this standard" — [GuardSync strata page](https://guardsync.ai/industries/strata), [SCA WHS guidance](https://inside.strata.community/strata-scheme-whs-responsibilities/)). Insurers require documented incident records for claims. **This is a tailwind: the product output *is* the compliance artifact.**

**BYOD/privacy/union:** Guards using personal phones is normal and insurer-sanctioned ([El Dorado Insurance](https://www.eldoradoinsurance.com/security-industry-news/byod-strategies-should-your-security-guards-use-personal-phones-on-the-job/)). Friction points are GPS-tracking apps and MDM invasiveness. A send-a-voice-note flow is *less* invasive than any guard-tour app — no install, no tracking — which is a sales argument, not an objection. No union blockers surfaced.

## 4. Market size + economics

- **Australia:** 6,727 investigation & security services businesses ([IBISWorld](https://www.ibisworld.com/australia/number-of-businesses/investigation-and-security-services/572/)); ~42% have 1–19 employees ([Australian Institute of Criminology](https://www.aic.gov.au/publications/tandi/tandi374)). Serviceable segment (5–30 guards with DAR obligations): roughly **1,500–2,500 firms**.
- **US:** ~6,800–11,300 firms; ~80% of contract firms have 1–9 employees ([BJS](https://www.ojp.gov/pdffiles1/bjs/grants/232781.pdf)). Serviceable band: **2,500–4,000 firms**.
- **Contract values:** AU static guarding bills $38–55+/hr + GST; one 12-hour/night site ≈ **$15–20k/month of revenue**. **$149–299/month is 0.3–1% of a small firm's revenue — immaterial as a cost, material as a retention lever** (poor reporting is a top reason clients switch providers; the client report is "the single biggest retention lever" — [Pulse](https://pulserevops.com/tech-stacks/tk335)).
- **Turnover confirmed:** 77% sector-wide, 100–300% at many firms. Every app-based competitor must re-onboard its user base 1–3× per year; "nothing to install, nothing to retrain" compounds in value with churn. **The strongest structural argument for the product.**

## 5. Demand signals

- **Fiverr/Upwork:** no physical-security report channel there (gigs are cybersecurity). Neutral — also means no gig-economy substitute exists.
- **SEO/template lead magnet: validated by incumbent behaviour.** Silvertrac, Belfry, Novagems, THERMS, SafetyCulture and paid template packs all farm the "DAR template / how to write" keyword cluster — companies don't sustain content like that unless it converts ([Silvertrac](https://www.silvertracsoftware.com/extra/7-things-every-daily-activity-report-should-include), [Belfry](https://www.belfrysoftware.com/blog/security-daily-activity-report-example)). Head terms are crowded; winnable space is long-tail + Australia-specific (almost all current content is US) + voice/AI variants where no content exists yet.
- Hard search-volume numbers weren't retrievable via web search — verify with a keyword tool before committing the SEO budget.

## 6. Risks

**(a) Liability of AI-written reports.** The Axon Draft One controversy is the roadmap: King County's Prosecuting Attorney banned AI-assisted police report narratives, citing hallucinations and that the tool "does not keep a draft of what it produces or what the officer fixed" ([King County memo](https://pceinc.org/wp-content/uploads/2025/01/20240920-Email-to-Police-Chiefs-re-Axon-Draft-One-King-County-Prosecuting-Attorney-Dan-Clark.pdf), [EFF via Ars Technica](https://arstechnica.com/tech-policy/2025/07/cops-favorite-ai-tool-automatically-deletes-evidence-of-when-ai-was-used/)). Private-security DARs are lower-stakes, but incident reports do end up before courts and insurers. The industry-accepted mitigation already exists: TrackTik logs every AI change with original-vs-enhanced side-by-side. **Design the provenance chain — original audio + verbatim transcript + AI draft + guard-confirmed final, all retained — as a headline feature.** It converts the biggest risk into the sharpest differentiator: your report comes with the evidence attached.

**(b) Hallucination.** Mitigations: transcription-and-structuring, not free generation; guard confirms via one-tap reply before the PDF is sent; low-confidence audio flagged, never guessed; audio kept as source of truth.

**(c) Incumbents adding voice AI.** Trackforce is one product cycle away; Belfry ships daily. Defence: they are structurally committed to *their apps and per-user pricing* — the no-app, flat-fee, done-for-you wedge targets the segment beneath their model. Speed matters; the window is quarters, not years.

**(d) Customer churn.** Flat per-company pricing insulates against a customer losing one site; the real risk is small firms failing or being acquired. The $999 setup front-loads revenue; the second vertical (commercial cleaning proof-of-service — CrewProof, ProTeams, CleanProof, Swept exist, so it's *more* crowded) comes only after security has 10+ referenceable customers.

**(e) Channel/platform dependency.** WhatsApp Business API policy/pricing changes; moderate penetration. Mitigation: multi-channel capture from day one; the branded PDF and archive — not the messaging channel — are the durable asset.

---

## Verdict: **GO-WITH-CHANGES**

**Why go:** contractually mandated deliverable + documented pain + validated price shape (Silvertrac $249/mo + $842–1,404 setup) + cost that is ~0.3–1% of customer revenue + structural moat aligned with 77–300% guard turnover + reachable buyers via registries, associations, communities + no incumbent offering voice-note-to-client-ready-report in AU/US.

**Required changes:**
1. **Drop "WhatsApp-first" as the identity; adopt "no-app, any-channel" capture** — WhatsApp + SMS voice memo + QR/link-to-browser recorder.
2. **Make the audit trail the product, not a feature.** "Court-ready with the evidence attached" pre-empts the exact critique that got AI police reports banned.
3. **Move fast and stay a service, not a platform.** The defensible ground is done-for-you setup + flat fee + zero-training. Do not drift into scheduling/GPS/payroll.
4. **Start Australia-first** (registries, ASIAL, local case studies), expand to US via SEO + communities once 5–10 AU case studies exist.

## Sharpest wedge / positioning

> **"Your guard sends a voice note. Your client gets a branded, timestamped, court-ready report — before the guard's shift ends. No app to install, no forms to build, no training that dies when a guard quits. Flat monthly fee. We set everything up for you."**

Positioned *against* form-builder apps: "Guard software assumes your guards will learn an app. With 100–300% turnover, they won't. We work with the phone habit they already have."

## First 10 customers without cold calling

1. **The demo IS the product (customers 1–3).** Publish a demo number: any security company owner sends a voice note describing last night's shift, and gets back *their own branded PDF DAR* within minutes. Convert with founding-customer pricing (setup fee waived for the first 3 AU firms in exchange for a case study).
2. **Artifact-led outreach from public registries (customers 2–6).** Pull the NSW Master Licence register (Excel export/API) and the Victoria Police register; filter to guarding/mobile-patrol firms. Send each a *made thing*, not a pitch: a professionally branded DAR template in their livery with a one-line note ("made this for you — if you'd like the voice-note version, send a voice memo to this number").
3. **Be the report-writing helper in communities (customers 4–8).** r/securityguards, owner Facebook groups, SNAP Academy, and (carefully) Security Insider Strategies. Answer DAR/incident-report questions, give away the template pack, never pitch.
4. **Template lead-magnet SEO cluster (compounding inbound).** Free downloadable DAR + incident-report templates, AU-specific (a gap — existing template content is American), each page ending in the voice-note demo CTA.
5. **Association and adjacent-professional channels (customers 6–10).** ASIAL supplier presence; security-industry insurance brokers who advise small firms on documentation; guest spots on security-business podcasts ("AI reports and your liability: what the Axon controversy means for guarding companies" — useful, timely, self-qualifying).

## Top 5 risks with mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Incumbent adds voice-AI | Own the below-app segment: flat fee, no per-user pricing, done-for-you setup, no-app capture. Ship AU-specific compliance features. Target 10 customers within two quarters of launch. |
| 2 | AI report challenged in court / by an insurer | Full provenance chain retained; AI-assist labelled; transcription-first architecture; guard one-tap confirmation before delivery. |
| 3 | Hallucination damages a customer relationship | Structure-don't-invent prompting; low-confidence segments flagged for human input; supervisor review option; audio always attached. |
| 4 | Channel dependency & reach | Multi-channel capture (WhatsApp + SMS/MMS + QR/link recorder); the archive and branded PDF are the durable product. |
| 5 | Small-firm customer churn / failure | $999 setup front-loads revenue; flat pricing survives site losses; annual-prepay discount; expand to cleaning proof-of-service only after 10+ referenceable security customers. |
