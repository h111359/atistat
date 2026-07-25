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
- Portfolio timeline combines three company milestones (Корект Проект 2006, Инженерни Системи 2008, ATISTAT 2024) with six delivered project records: EOS Matrix, Montekanal, EMA, Elemag, UBB Interlease, and British School of Sofia.

## Requirements

- MUST: Preserve Bulgarian and English core content routes with visible language navigation. 
- MUST: Present company identity, mission, experience, services, portfolio evidence, and contact information.
- MUST: Support responsive navigation and project browsing across desktop and mobile layouts. 
- MUST: Support keyboard operation for timeline selection and expose navigation state through accessible attributes. 
- MUST: Honor reduced-motion preferences by disabling reveal movement and transitions.
- MUST: Prioritize the above-fold homepage hero image and defer below-fold imagery.
- MUST NOT: Require third-party JavaScript libraries or a build pipeline for core front-end interactions. 
- OPTIONAL: Outbound integrations may connect visitors to a map, messaging, social profiles, and related-company sites. 

## Solution

- Site is a static export of rendered WordPress pages plus REST, oEmbed, robots, and sitemap snapshots.
- Root HTML route family stores primary, localized, query-style, and noindex AI insight pages as independent documents.
- Six project directories each store default, Bulgarian, English, and query-style static page variants. 
- Shared theme stylesheet defines green, ink, cream, and paper design tokens, local Bookman Cyrillic typography, responsive grids, timeline presentation, contact layout, and reduced-motion behavior.
- Shared vanilla JavaScript controls mobile-nav state, intersection-based reveal animation, desktop timeline selection, partner-card outbound actions, and touch sketch toggles.
- Local media uses WebP project imagery, PNG partner marks, and WOFF2 and TTF font files; version-suffixed CSS and JS copies are byte-identical to canonical assets. 
- External services are limited to a Google Maps iframe and outbound WhatsApp, Facebook, LinkedIn, Correct Project, and Engineering Systems destinations.
- Workspace has no README, automated tests, scripts directory, dependency manifest, or build configuration.
- Primary Bulgarian homepage extends the shared theme with document-local CSS for hero actions, differentiation cards, FAQ, a selected-projects gallery dialog, a CTA contact block, and a floating Viber action.
- Selected-projects gallery opens as a native dialog modal triggered from the Experience section and displays all 7 submitted project image sets as a photo gallery without dedicated project routes.
- A partners section with Инженерни Системи, Корект Проект, and Адрео logo-links appears between the Services and Why sections on all BG and EN homepage copies.
- Homepage timeline includes an ATISTAT entry at 2024 using atistat-logo.png from wp-content/themes/atistat/assets/images/ linked to the site root.
- Homepage timeline renders accessible desktop tabs and alternate stacked mobile cards from the same nine company and project milestones.
- Experience attribution secondary lines appear in the desktop panels and mobile cards of four timeline project entries (EOS Matrix, Montekanal, Elemag, and UBB Interlease) identifying the associated partner company.
- Service feature bullet lists with green checkmark style appear before the numbered process steps in each of the four service article elements across all five homepage documents.
- All five homepage documents carry meta description, Open Graph, Twitter Card, and JSON-LD Organization structured-data blocks with language-appropriate values and per-document canonical og:url.
- Language switcher option controls meet 44x44 CSS pixel tap target size and mark the active language with aria-current=page and a non-color-only green background chip indicator.
- Elemag hero sketch and Montekanal about sketch captions each use a three-span vertical structure (label, project name, service classification) with an aria-label on the parent anchor element.
- Main site navigation includes a Partners section anchor link across all five homepage documents.

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
- Homepage project timeline buttons do not link to the six local project-detail routes, although partner-company milestones have outbound links. Source: index.html contains no proekti route links.
- Six project page families expose only project name and service classification without project narrative, facts, galleries, or outcome evidence. Source: proekti page content and exported project records remain minimal.
- English project pages localize navigation and footer labels but retain Bulgarian project titles and service descriptions. Source: proekti project index-en.html variants contain Bulgarian main content.
- Header and footer inline logos repeat the same eight HTML identifiers within the primary homepage. Source: index.html contains two occurrences each of svg1, namedview1, defs1, layer3, g1, layer2, text1, and text2.
- No automated test suite or build-time verification exists for routes, localization, accessibility, responsive layout, or link integrity. Source: workspace inventory contains no test, script, dependency, or build artifacts.
- index-bg.html diverges from index.html by approximately 400 lines because index.html carries an inline CSS block and additional sections not replicated in index-bg.html; each implementation pass widens this divergence further. Source: diff between index.html and index-bg.html.
- Viber viber:// URI scheme produces no action on desktop browsers where Viber is not installed; all Viber link elements must include a descriptive title or aria-label to inform desktop users. Source: Viber URI scheme behavior.
- Gallery image payload is approximately 52.5 MiB across 32 unoptimized PNG and JPEG files; images are lazy-loaded but users who open the Selected Projects modal on slow connections will experience significant download time; image optimization is deferred per stakeholder constraints.
