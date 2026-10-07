import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pages, renderPage, root } from './prerender.mjs';

const origin = 'https://aimlab.knu.ac.kr/';
const canonical = page => origin + (page === 'index.html' ? '' : page);
const sitemap = await readFile(path.join(root, 'sitemap.xml'), 'utf8');
const urls = [...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(match => match[1]);
assert.deepEqual(urls.sort(), pages.map(canonical).sort(), 'Sitemap must contain only the 10 canonical pages');
const escapeHtml = text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;')
  .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');

for (const page of pages) {
  const html = await readFile(path.join(root, page), 'utf8');
  const body = html.split('<script>')[0];
  assert.equal(await renderPage(page), html, `${page}: generated content is out of date`);
  assert.equal(await renderPage(page, { failFetch: true }), html, `${page}: failed JSON fetch erases static content`);
  assert.ok(body.includes(`rel="canonical" href="${canonical(page)}"`), `${page}: incorrect canonical`);
  assert.ok(/name="description" content="[^"]+"/.test(body), `${page}: missing description`);
  assert.ok(!/class="(?:loading-state|error-state)"/.test(body), `${page}: placeholder instead of content`);
  assert.ok(body.includes('data-prerendered="true"'), `${page}: no static content`);
  for (const language of ['en', 'ko', 'x-default']) {
    const name = path.basename(page);
    const target = language === 'ko' ? origin + 'ko/' + name : canonical(name);
    assert.ok(body.includes(`hreflang="${language}" href="${target}"`), `${page}: incorrect language alternate`);
  }
  const dataset = path.basename(page, '.html');
  if (dataset !== 'index') {
    const data = JSON.parse(await readFile(path.join(root, 'data', `${dataset}.json`), 'utf8'));
    for (const item of data) {
      const field = { publications: 'title', news: 'title', research: 'theme', people: 'given_name' }[dataset];
      const text = page.startsWith('ko/') && dataset !== 'publications'
        ? (dataset === 'people' ? item.name_kr || item[field] : item[`${field}_kr`] || item[field])
        : item[field];
      if (text) assert.ok(body.includes(escapeHtml(text)), `${page}: missing data item ${text}`);
    }
  }
  if (/people|publications/.test(page)) {
    assert.ok(body.includes('<noscript><style>.panel { display: block; }'), `${page}: tabs inaccessible without JS`);
  }
  console.log(`PASS ${page}: static content, live rendering, failed fetch, canonical and languages`);
}
const robots = await readFile(path.join(root, 'robots.txt'), 'utf8');
assert.ok(robots.includes(`Sitemap: ${origin}sitemap.xml`));
assert.ok(!/Disallow:\s*\/data/.test(robots), 'Do not block data required for rendering');
console.log('PASS sitemap and robots.txt');
