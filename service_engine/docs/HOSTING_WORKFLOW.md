# Hosting Workflow — Where the crawlable support pages live

The engine produces crawlable support pages (`pages/*.html`) + `sitemap.xml`. STEP 6 (publish &
make crawlable) is manual and needs a decided host. This document compares the options and gives the
MVP recommendation.

> Safety reminder: hosting/publishing makes pages **discoverable and crawlable**. It does **not**
> guarantee indexing, rankings, or AI mentions. Keep all page/sales copy aligned with
> `docs/CLIENT_SAFE_NOTES.md`.

---

## Option A — Host on the client's own website
**How:** publish pages under the client's domain (e.g. `client.com/ai-answers/...`).

- **Pros:** strongest entity/brand association (same domain as the brand); best trust; pages inherit
  the client's existing crawl authority; no third-party disclosure needed.
- **Cons:** requires client CMS access / dev cooperation; slower turnaround; client may resist
  publishing AI-answer pages; we don't control uptime or URL structure.
- **SEO / AI visibility:** best — first-party content on the brand's own domain is the cleanest
  signal for associating brand ↔ keyword.
- **Operational complexity:** high (per-client access, varying CMS).
- **Client trust:** high (their domain, their control).
- **Risk:** medium — client edits/removes pages; brand-safety review must pass before publishing on
  their domain.
- **Best use case:** clients who are hands-on and want the asset on their own site.

## Option B — Host on an SEOeStore-owned support domain/subdomain
**How:** one SEOeStore property (e.g. `ai-visibility.seoestore-domain.com`) with a folder per client.

- **Pros:** full operational control; fast, repeatable publishing; consistent templates/sitemaps;
  no client dependency; easy to demo.
- **Cons:** third-party domain → weaker first-party entity signal than Option A; many clients on one
  domain can dilute topical focus; must clearly label as an SEOeStore property.
- **SEO / AI visibility:** moderate — real, crawlable pages, but association is "mentioned-on-a-
  third-party-site" rather than first-party.
- **Operational complexity:** low once set up (we own it).
- **Client trust:** medium — transparent, but not the client's own domain.
- **Risk:** medium — a shared property hosting many brands can look thin/templated if over-scaled;
  manage volume and quality.
- **Best use case:** the default for fast, controlled MVP delivery.

## Option C — Host inside a client-specific subfolder (on the SEOeStore property)
**How:** a variant of B with strict per-client isolation: `…/clients/<client-slug>/<order-id>/…`.

- **Pros:** clean separation per client/order (mirrors our output structure); easy to hand a client
  their own folder/URL; simple to delist one client without touching others.
- **Cons:** same third-party-domain limitation as B; subfolders on a shared domain still share the
  domain's reputation.
- **SEO / AI visibility:** moderate (same as B), with cleaner per-client structure.
- **Operational complexity:** low — maps 1:1 to `outputs/<client-slug>/<order-id>/`.
- **Client trust:** medium.
- **Risk:** low-medium.
- **Best use case:** running many orders on the SEOeStore property without cross-client mixing.

## Option D — Dedicated microsite / content property per client
**How:** a standalone small site (own domain) per client/niche.

- **Pros:** strong topical focus per brand; looks like an independent resource; flexible.
- **Cons:** a domain per client = cost + setup + maintenance; slowest; risks looking like a
  manufactured network if reused at scale (quality/PBN-perception risk).
- **SEO / AI visibility:** potentially strong per brand, but only with genuine, non-templated
  content; otherwise low-value.
- **Operational complexity:** high (domains, hosting, upkeep).
- **Client trust:** medium-high (dedicated property) but raises "why a separate site?" questions.
- **Risk:** high if scaled carelessly (network/quality perception).
- **Best use case:** premium/bespoke engagements only.

---

## Recommendation for the MVP (first paid orders)

**Primary: Option C — an SEOeStore-owned support subdomain with a per-client/per-order subfolder.**
It mirrors our `outputs/<client-slug>/<order-id>/` structure exactly, gives full operational control
and fast turnaround, keeps clients cleanly isolated, and is easy to demo and to delist. Label it
transparently as an SEOeStore AI-visibility support property.

**Offer Option A as an upgrade** for clients who want the pages on their own domain (best first-party
association) — same generated files, published to their CMS, after the brand-safety review.

**Avoid Option D at MVP** (cost/complexity + network-perception risk); revisit only for premium work.

### MVP guardrails (whichever option)
- One subfolder per `client-slug/order-id`; publish the order's `sitemap.xml`; complete
  `submission_checklist.md`.
- Keep pages genuinely useful (real tested questions + real captured answers); do not mass-produce
  near-duplicate pages across clients.
- Run the QA gate (`docs/QA_GATE.md`) and the client-safe review before publishing.
- Set `website` in the client input to the chosen host base so generated URLs/sitemap match where
  pages will actually live.
