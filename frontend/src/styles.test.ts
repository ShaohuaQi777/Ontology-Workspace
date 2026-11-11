import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath, URL as NodeURL } from 'node:url';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

const cssPath = fileURLToPath(new NodeURL('./styles.css', import.meta.url));
let stylesheet: HTMLStyleElement;
let fixture: HTMLDivElement;

beforeEach(() => {
  stylesheet = document.createElement('style');
  // The product's real stylesheet is loaded, never a mock import or CSS fixture.
  stylesheet.textContent = existsSync(cssPath) ? readFileSync(cssPath, 'utf8') : '';
  document.head.append(stylesheet);
  fixture = document.createElement('div');
  document.body.append(fixture);
});
afterEach(() => {
  stylesheet.remove();
  fixture.remove();
});

function element(tag: string, className: string, parent: HTMLElement = fixture): HTMLElement {
  const node = document.createElement(tag);
  node.className = className;
  parent.append(node);
  return node;
}

// These tests exercise resulting styles on real semantic DOM elements. jsdom
// cannot prove viewport geometry, media-query activation or keyboard focus;
// those require the separate desktop/mobile browser review, not source matching.
describe('data intake shipped CSS contract', () => {
  it('keeps breadcrumb navigation inline instead of consuming a full source-table row',()=>{const nav=element('div','breadcrumb');const button=element('button','row-button',nav);expect(getComputedStyle(button).width).toBe('auto')});
  it('loads the shipped stylesheet', () => {
    expect(existsSync(cssPath)).toBe(true);
    expect(stylesheet.sheet?.cssRules.length).toBeGreaterThan(0);
  });

  it('uses a shrinkable middle between the two desktop workspace panels', () => {
    const shell = element('div', 'intake-shell');
    const main = element('main', 'intake-main', shell);
    const grid = element('section', 'workbench-grid', main);
    const nav = element('nav', 'dataset-nav', grid);
    const detail = element('section', 'detail-panel', grid);
    const inspector = element('aside', 'evidence', grid);
    expect(getComputedStyle(grid).display).toBe('grid');
    expect(getComputedStyle(grid).gridTemplateColumns).toMatch(/^230px\s+minmax\(0,\s*1fr\)\s+280px$/);
    for (const panel of [main, nav, detail, inspector]) {
      expect(getComputedStyle(panel).minWidth).toBe('0');
    }
  });

  it('contains a wide real table in its own horizontal scroll region', () => {
    const container = element('div', 'table-scroll');
    const table = element('table', '', container);
    const row = element('tr', '', element('tbody', '', table));
    element('td', 'mono', row).textContent = 'a-long-source-reference-without-spaces';
    expect(getComputedStyle(container).overflowX).toBe('auto');
    expect(getComputedStyle(container).maxWidth).toBe('100%');
    expect(getComputedStyle(container).minWidth).toBe('0');
  });

  it('keeps native controls readable and actionable', () => {
    const nativeButton = element('button', '');
    const button = element('button', 'button primary');
    const input = element('input', '');
    expect(getComputedStyle(document.body).fontSize).toBe('14px');
    // jsdom does not resolve inherited font shorthand (even on bare controls).
    // Check the parsed, applicable CSSOM declaration rather than CSS source text;
    // actual browser review verifies the resulting inherited font metrics.
    const rules = Array.from(stylesheet.sheet!.cssRules)
      .filter(rule => rule.type === 1) as CSSStyleRule[];
    for (const control of [nativeButton, input]) {
      expect(rules.some(rule => control.matches(rule.selectorText)
        && rule.style.getPropertyValue('font') === 'inherit')).toBe(true);
    }
    expect(getComputedStyle(button).display).not.toBe('none');
    expect(getComputedStyle(button).pointerEvents).not.toBe('none');
    expect(getComputedStyle(button).backgroundColor).toBe('rgb(15, 118, 110)');
  });

  it('bounds a real dialog with viewport height and vertical scrolling', () => {
    const overlay = element('div', 'dialog-overlay');
    const dialog = element('section', 'dialog', overlay);
    dialog.setAttribute('role', 'dialog');
    expect(getComputedStyle(overlay).position).toBe('fixed');
    expect(getComputedStyle(overlay).overflowY).toBe('auto');
    expect(getComputedStyle(dialog).maxHeight).toBe('calc(100dvh - 32px)');
    expect(getComputedStyle(dialog).overflowY).toBe('auto');
  });

  it('keeps business errors and evidence visible rather than hiding them', () => {
    const error = element('p', 'error');
    error.textContent = '当前项目无权限';
    const evidence = element('aside', 'evidence');
    const source = element('dd', 'mono', element('dl', 'inspector-dl', evidence));
    source.textContent = 'source:actual-source-id';
    expect(getComputedStyle(error).color).toBe('rgb(180, 35, 24)');
    for (const node of [error, evidence, source]) {
      expect(getComputedStyle(node).display).not.toBe('none');
      expect(getComputedStyle(node).visibility).not.toBe('hidden');
    }
    expect(getComputedStyle(source).overflowWrap).toBe('anywhere');
  });
});
