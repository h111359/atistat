# Product Context

## Product

- ATISTAT workspace delivers a static bilingual marketing and project-portfolio website for Bulgarian construction and investment company ATISTAT EOOD. 
- Primary audience comprises property owners, investors, corporate clients, architects, and partners evaluating ATISTAT services or initiating contact. 
- Product scope covers company positioning, professional experience, service process, selected projects, trust content, and direct contact channels. 
- Core commercial offering spans residential construction, renovation and reconstruction, construction-project development, and real-estate investment. 

## Concepts

- ATISTAT positions construction professionalism and investment vision as its central value proposition. 
- Company mission emphasizes professionally planned, high-quality, responsibly managed construction and investment projects with long-term value. 
- Founder Hristin Haralanov's professional path anchors company experience and connects ATISTAT with Correct Project and Engineering Systems. 
- Project records pair a project name with a service classification, featured image, static route, and WordPress project identifier.
- Localization model uses Bulgarian and English static page variants linked by visible BG and EN controls. 
- Homepage trust model uses experience duration, project count, project portfolio evidence, ЗАЩО АТИСТАТ differentiation, service process steps, and FAQ responses.
- Direct-contact model offers phone, email, office map, WhatsApp, Viber, and Facebook/LinkedIn footer links without an on-site submission form.
- Portfolio timeline merges thirteen milestones: three company records (Корект Проект 2006, Инженерни Системи 2008, ATISTAT 2024) and ten projects (EOS Matrix 2007, Montekanal 2011, EMA 2015, Elemag 2021, Apartment Louis Ayer 2024, UBB Interlease 2025, Apartment Arcadia 2025, Bebelan 2025, Power Properties 2025, and British School of Sofia 2026).

## Requirements

- MUST: Preserve Bulgarian and English core content routes with visible language navigation. 
- MUST: Present company identity, mission, experience, services, portfolio evidence, and contact information.
- MUST: Support responsive navigation and project browsing across desktop and mobile layouts. 
- MUST: Support keyboard operation for timeline selection and expose navigation state through accessible attributes. 
- MUST: Honor reduced-motion preferences by disabling reveal movement and transitions.
- MUST: Prioritize the above-fold homepage hero image and defer below-fold imagery.
- MUST NOT: Require third-party JavaScript libraries or a build pipeline for core front-end interactions. 
- OPTIONAL: Outbound integrations may connect visitors to a map, messaging, social profiles, and related-company sites. 
- MUST: Expose real-project timeline panels and responsive cards as keyboard-operable controls that open localized project information.

## Solution

- Site is a static export of rendered WordPress pages plus REST, oEmbed, robots, and sitemap snapshots.
- Root HTML route family stores primary, localized, query-style, and noindex AI insight pages as independent documents.
- Six project directories each store default, Bulgarian, English, and query-style static page variants. 
- Shared theme stylesheet defines green, ink, cream, and paper design tokens, local Bookman Cyrillic typography, responsive grids, timeline presentation, contact layout, and reduced-motion behavior.
- Shared vanilla JavaScript controls mobile-nav state, intersection-based reveal animation, desktop timeline selection, partner-card outbound actions, and touch sketch toggles.
- External services are limited to a Google Maps iframe and outbound WhatsApp, Facebook, LinkedIn, Correct Project, and Engineering Systems destinations.
- Primary Bulgarian homepage extends the shared theme with document-local CSS for hero actions, differentiation cards, FAQ, a selected-projects gallery dialog, a CTA contact block, and a floating Viber action.
- A partners section with Инженерни Системи, Корект Проект, and Адрео logo-links appears between the Services and Why sections on all BG and EN homepage copies.
- Experience attribution secondary lines appear in the desktop panels and mobile cards of four timeline project entries (EOS Matrix, Montekanal, Elemag, and UBB Interlease) identifying the associated partner company.
- Service feature bullet lists with green checkmark style appear before the numbered process steps in each of the four service article elements across all five homepage documents.
- All five homepage documents carry meta description, Open Graph, Twitter Card, and JSON-LD Organization structured-data blocks with language-appropriate values and per-document canonical og:url.
- Language switcher option controls meet 44x44 CSS pixel tap target size and mark the active language with aria-current=page and a non-color-only green background chip indicator.
- Elemag hero sketch and Montekanal about sketch captions each use a three-span vertical structure (label, project name, service classification) with an aria-label on the parent anchor element.
- Main site navigation includes a Partners section anchor link across all five homepage documents.
- Gallery-only projects (Apartment Arcadia, Apartment Louis Ayer, Bebelan, Power Properties) use lightweight line-art timeline assets generated from their first submitted photograph and stored in wp-content/uploads/2026/07/ with ASCII filenames.
- Official white Viber icon is stored locally as viber-icon.png in wp-content/themes/atistat/assets/images/ and served on ATISTAT green controls without alteration across all five root homepage documents.
- English Why/FAQ sections are faithful translations of the Bulgarian source-of-truth sections and inherit CSS rules defined in main.css; Why/FAQ document-local styles in index.html are promoted to the shared stylesheet.
- Apartment Arcadia uses arcadia-timeline.webp across all six timeline documents; its desktop marker is fully grayscale at rest and in color on hover, keyboard focus, and active selection, while mobile stacked-card imagery remains in color.
- Workspace has no README, scripts directory, dependency manifest, or build configuration; tests/test_static_site.py and tests/fixtures/interaction_harness.html provide Python unittest static checks and Chrome interaction smoke coverage.
- Adreo partner logo-link uses wp-content/uploads/2026/07/adreo.png; BG-localized documents carry alt='Адрео', EN-localized documents carry alt='Adreo'.
- Across index.html, index-bg.html, index-en.html, index.html?lang=bg.html, index.html?lang=en.html, and opit/index.html, the Experience section presents the unchanged selected evidence panel before its localized instruction and a compact thirteen-milestone desktop rail above 860px; the desktop rail keeps about five complete milestones, inline Previous/Next controls, boundary hiding, edge fades, free panning, proximity snapping, active-tab centering, and automatic tab activation while using smaller milestone imagery and endpoint labels; at 860px and below, a static approximately three-up 13-link navigation rail appears above the unchanged 13-card list, remains useful without JavaScript, and is enhanced with focus-only Arrow navigation, explicit Enter/Space/click activation, card-container focus, reduced-motion-aware scrolling, edge state, and activation-only persistent current state.
- Timeline interaction classifies ten real projects as full-surface native dialog controls, Correct Project and Engineering Systems as external links, and ATISTAT as selectable navigation content without a destination action.
- Gallery-eligible projects (Elemag, Montekanal, UBB Interlease, Apartment Arcadia, Apartment Louis Ayer, Bebelan, Power Properties) retain noninteractive four-image mosaic previews from bounded 160x160 WebP assets in desktop panels and responsive cards; full-surface native project controls open the reusable filtered dialog with original project-scoped image sets and restore focus after close.
- opit/index.html is synchronized with the English homepage timeline and dialog content, including thirteen milestones, ten project launchers, and ten localized project records.
- Across index.html, index-bg.html, index-en.html, query-style BG and EN documents, and opit/index.html, Selected Projects presents seven localized image-led cards in approved order; fixed-crop imagery pairs with five localized project facts and internal native dialog actions, while card articles remain programmatic in-page targets; shared native dialog retains ten localized project records, with EOS Matrix, EMA, and British School of Sofia available only from the timeline.

## File Structure

.gitignore - Ignores Python bytecode and local environment directories.
ai-critique.html - Standalone noindex Bulgarian technical audit and implementation-prompt report.
index*.html - Contains 15 primary, localized, query-route, HTML files at workspace root.
opit/
  index.html - English experience-route snapshot that reproduces the core homepage.
proekti/
  */ - Contains 30 static page variants across six project directories, with five default, BG, EN, or query-route files per project.
robots.txt - WordPress-style crawler directives and sitemap location.
wp-content/
  themes/atistat/assets/
    css/ - Contains two byte-identical copies of the shared responsive theme stylesheet.
    fonts/ - Contains two local Bookman Cyrillic font files.
    images/ - Contains four homepage and partner-brand images.
    js/ - Contains two byte-identical copies of the dependency-free interaction script.
  uploads/2026/07/ - Contains six WebP project images used by the portfolio timeline.
wp-json/
  index.html - Exported WordPress REST route index.
  oembed/1.0/ - Contains 13 generic and project-specific oEmbed snapshots.
  wp/v2/at_project/ - Contains six exported project JSON records.
wp-sitemap* - Contains five XML and XSL sitemap index, route-list, and presentation files.

## References

### Primary Bulgarian Homepage
Location: index.html
Summary: Defines current public-facing Bulgarian company narrative, conversion sections, project timeline, service processes, and contact integrations.

## Issues

- Default fade styling hides marked content when JavaScript is unavailable or fails before reveal initialization. Source: main.css sets fade opacity to zero globally while main.js performs reveal activation.
- Six project page families expose only project name and service classification without project narrative, facts, galleries, or outcome evidence. Source: proekti page content and exported project records remain minimal.
- English project pages localize navigation and footer labels but retain Bulgarian project titles and service descriptions. Source: proekti project index-en.html variants contain Bulgarian main content.
- Header and footer inline logos repeat the same eight HTML identifiers within the primary homepage. Source: index.html contains two occurrences each of svg1, namedview1, defs1, layer3, g1, layer2, text1, and text2.
- index-bg.html diverges from index.html by approximately 400 lines because index.html carries an inline CSS block and additional sections not replicated in index-bg.html; each implementation pass widens this divergence further. Source: diff between index.html and index-bg.html.
- Viber viber:// URI scheme produces no action on desktop browsers where Viber is not installed; all Viber link elements must include a descriptive title or aria-label to inform desktop users. Source: Viber URI scheme behavior.
- Timeline markup is duplicated across six HTML documents, so future milestone or interaction changes can drift unless parity assertions and shared-asset identity tests remain enforced. Source: index.html, index-bg.html, index-en.html, index.html?lang=bg.html, index.html?lang=en.html, opit/index.html, and tests/test_static_site.py.
- The automated interaction harness uses Chrome and cannot fully prove native-scrollbar rendering or physical wide-touch behavior across browser and device combinations; those states require manual cross-browser and wide-touch verification. Source: tests/test_static_site.py and tests/fixtures/interaction_harness.html.
- The analysis convention and analyze prompt require exactly three Proposed Solution level-three subsections but name only High-Level Concept and Execution Steps, leaving the third heading undefined. Source: .aib_brain/conventions/analysis-convention.md and .aib_brain/prompts/aib-analyze.md.
- The analyze prompt objective calls for a Decisions section in the plan, while the normative plan convention permits exactly Goal, Constraints, Success criteria, and Plan as top-level sections. Source: .aib_brain/prompts/aib-analyze.md and .aib_brain/conventions/plan-convention.md.
- The Q-block convention requires a recommended multiple-choice option, while the Decision Register convention prohibits steering an unresolved ask Decision Point; analysis alternatives must remain neutral even when the generated questionnaire carries a recommendation. Source: .aib_brain/conventions/q-block-convention.md and .aib_brain/conventions/analysis-convention.md.
- The full-resolution gallery dialog payload remains approximately 52.5 MiB across 32 unoptimized PNG and JPEG files; bounded WebP thumbnails prevent normal-page mosaics from loading those originals, but users who open the Selected Projects dialog on slow connections can still experience significant download time; full-dialog image optimization remains deferred per stakeholder constraints. Source: gallery dialog markup across the six Experience documents.
- The responsive marker rail reuses milestone imagery above the stacked card list, so visible markers may initiate image requests earlier than the former responsive layout; lazy loading and browser cache reuse limit but do not eliminate this payload shift. Source: responsive rail markup across the six Experience documents.
