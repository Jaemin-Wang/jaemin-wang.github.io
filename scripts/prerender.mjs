// Reuse each page's browser renderer so static and interactive content stay identical.
// Only trusted repository scripts run here; this is not an untrusted-code sandbox.
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

export const root = fileURLToPath(new URL('../', import.meta.url));
export const pages = ['', 'ko/'].flatMap(prefix =>
  ['index', 'research', 'publications', 'people', 'news'].map(name => `${prefix}${name}.html`));
const escapeText = value => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Locate the existing data containers, including their nested div/section elements.
// Scripts are deliberately excluded from this scan.
function containers(html) {
  const body = html.slice(0, html.indexOf('<script>'));
  const result = new Map();
  for (const match of body.matchAll(/<(div|section)\b[^>]*\bid="([^"]+)"[^>]*>/g)) {
    const tag = match[1];
    const tokens = new RegExp(`<\\/?${tag}\\b[^>]*>`, 'g');
    tokens.lastIndex = match.index + match[0].length;
    let depth = 1;
    let end;
    while ((end = tokens.exec(body))) {
      depth += end[0].startsWith('</') ? -1 : 1;
      if (depth === 0) break;
    }
    if (depth) throw new Error(`Unclosed container: ${match[2]}`);
    const start = match.index + match[0].length;
    result.set(match[2], {
      start, end: end.index, openingStart: match.index, opening: match[0],
      original: body.slice(start, end.index),
      dataset: { prerendered: match[0].includes('data-prerendered="true"') ? 'true' : undefined },
      classList: { toggle() {} },
      get innerHTML() { return this.content ?? this.original; },
      set innerHTML(value) { this.content = String(value); },
      set textContent(value) { this.content = escapeText(value); },
    });
  }
  return result;
}

export async function renderPage(page, { failFetch = false } = {}) {
  const html = await readFile(path.join(root, page), 'utf8');
  const elements = containers(html);
  const errors = [];
  const pending = [];
  const context = vm.createContext({
    window: {},
    document: {
      getElementById(id) {
        if (!elements.has(id)) throw new Error(`Unknown container: ${id}`);
        return elements.get(id);
      },
      // Event binding is performed by the real browser, not during static rendering.
      querySelectorAll() { return []; },
    },
    console: { error: error => errors.push(error) },
    fetch: async url => {
      if (failFetch) throw new Error('Simulated unavailable JSON');
      const filename = path.resolve(root, path.dirname(page), url);
      if (path.dirname(filename) !== path.join(root, 'data') || !filename.endsWith('.json')) {
        throw new Error(`Unexpected data URL: ${url}`);
      }
      const data = JSON.parse(await readFile(filename, 'utf8'));
      return { ok: true, json: async () => data };
    },
    pending,
  });
  for (const script of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) {
    const source = script[1].replace(/^(\s*)(load\w+\(\));\s*$/gm, '$1pending.push($2);');
    vm.runInContext(source, context, { filename: page, timeout: 5000 });
  }
  if (!pending.length) throw new Error(`No render entry points found: ${page}`);
  await Promise.all(pending);
  if (errors.length && !failFetch) throw new AggregateError(errors, `Rendering failed: ${page}`);

  let output = html;
  const changed = [...elements.values()].filter(element => element.content !== undefined);
  for (const element of changed.sort((a, b) => b.start - a.start)) {
    const opening = element.opening.includes('data-prerendered=')
      ? element.opening : element.opening.replace(/>$/, ' data-prerendered="true">');
    output = output.slice(0, element.openingStart) + opening + element.content + output.slice(element.end);
  }
  return output.replace(/[ \t]+$/gm, '');
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const check = process.argv.includes('--check');
  // Render everything before writing: malformed JSON must not produce a partial build.
  const rendered = await Promise.all(pages.map(async page => [page, await renderPage(page)]));
  let stale = false;
  for (const [page, html] of rendered) {
    const filename = path.join(root, page);
    if (html === await readFile(filename, 'utf8')) continue;
    if (check) {
      console.error(`Stale generated content: ${page}`);
      stale = true;
    } else {
      await writeFile(filename, html);
      console.log(`Rendered ${page}`);
    }
  }
  if (stale) {
    console.error('Run node scripts/prerender.mjs and commit the updated HTML with your data changes.');
    process.exitCode = 1;
  } else {
    console.log(`Verified ${pages.length} pages.`);
  }
}
