# Theme: boostl

## Identity

- **Product name:** Boostl (`lib/brand.ts` → `BRAND_NAME`)
- **Persona:** Maria — local bakery owner with zero marketing expertise; plain language, no jargon
- **Aesthetic:** Warm, approachable small-business SaaS — coral accent on cream background. **Not** dark Stripe/Linear SaaS.
- **Logo component:** `app/components/boostly-logo.tsx` — `BoostlyLogo`, `BoostlyBrandName`; assets from `lib/brand.ts`. Never redraw, distort, or recolour.

## Palette

| Role | Value |
|------|-------|
| Page background | `#FFFBF7` |
| Primary text | `#1a1a1a` |
| Muted text | `#5c5c5c`, `#8c8c8c` |
| Primary accent | gradient `#FF6B4A` → `#FF8F6B` |
| Borders / dividers | `#f0e6df` |
| Positive metrics | `#2D8A56` |
| Cards | white, `rounded-2xl`, light border, subtle shadow |

Platform branding (icons/previews only): Facebook blue, Instagram gradient, TikTok cyan/pink, YouTube red — surrounding UI stays coral/neutral.

## Typography

- `font-sans` from app shell
- Page shell: `min-h-full bg-[#FFFBF7] font-sans text-[#1a1a1a]`
- App content: `max-w-5xl mx-auto px-6`
- Landing: `max-w-6xl`
- Headers: white/`80` + backdrop blur, bottom border `#f0e6df`

## Components

- **Primary CTA:** `rounded-full` or `rounded-2xl` coral gradient, white text, orange shadow
- **Cards:** white, `rounded-2xl`, border `#f0e6df`, subtle shadow
- **Shared UI:** `app/components/boostly-ui.tsx`, `page-ui.tsx`, `components/ui/` (shadcn)
- **Platform icons:** `app/components/platform-icon.tsx` — reuse; no inline SVG duplicates
- **Top bar / nav:** `app/components/boostly-top-bar.tsx`
- **Theme variables:** `app/globals.css` (Tailwind v4)

## Spacing and layout

- Predictable grid; consistent spacing scale
- Logo mark: coral gradient square with white "B", `rounded-lg` or `rounded-xl`
- No horizontal overflow unless intentional (tables, carousels)

## Tone and copy

- Friendly, confident, plain language for non-marketers
- Example: "You've used 8 of 20 generations this month."
- Avoid jargon, enterprise SaaS tone, emoji-heavy UI beyond existing patterns

## Anti-patterns

- Switch to dark mode or generic gray SaaS styling unless explicitly asked
- Stripe / Linear / Toss dark skins from third-party skills
- New colour systems or font families without approval
- Hardcoded random hex in components when tokens exist in `globals.css` / `boostly-ui.tsx`
- Redrawing or resizing the logo outside `boostly-logo.tsx`
- Cross-feature imports for UI reuse — move shared code to `app/components/` or `lib/`

## Project paths

```
C:\Users\Andre\boostly
```

## Notes

- Stack: Next.js App Router, Tailwind CSS v4, shadcn/ui
- Project overrides: `.cursor/rules/boostly-ui.mdc`, `DESIGN.md`, `PRODUCT.md` (Maria persona)
- `between-steps-ux`: `.cursor/skills/between-steps-ux/` — audit create-ad, billing, OAuth flows
- Architecture: thin pages; feature UI in `app/features/*/components/`
