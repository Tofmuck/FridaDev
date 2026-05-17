'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require('playwright');

const WEB_DIR = path.resolve(__dirname, '../../../../web');

function contentTypeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === '.html') return 'text/html; charset=utf-8';
  if (ext === '.js') return 'application/javascript; charset=utf-8';
  if (ext === '.css') return 'text/css; charset=utf-8';
  if (ext === '.png') return 'image/png';
  return 'application/octet-stream';
}

async function createStaticWebServer() {
  const server = http.createServer(async (req, res) => {
    const requestUrl = new URL(req.url || '/', 'http://127.0.0.1');
    const pathname = requestUrl.pathname === '/' ? '/index.html' : requestUrl.pathname;
    const normalized = path.normalize(decodeURIComponent(pathname)).replace(/^(\.\.[/\\])+/, '');
    const filePath = path.resolve(WEB_DIR, normalized.replace(/^[/\\]+/, ''));

    if (!filePath.startsWith(`${WEB_DIR}${path.sep}`) && filePath !== WEB_DIR) {
      res.writeHead(403);
      res.end('Forbidden');
      return;
    }

    try {
      const body = await fs.readFile(filePath);
      res.writeHead(200, { 'Content-Type': contentTypeFor(filePath) });
      res.end(body);
    } catch (error) {
      res.writeHead(error && error.code === 'ENOENT' ? 404 : 500);
      res.end('Not found');
    }
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  return {
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise((resolve) => server.close(resolve)),
  };
}

async function openBrowserPage({ pathSuffix = '/', mockScript, afterPage = null }, runTest) {
  const server = await createStaticWebServer();
  let browser = null;

  try {
    browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ locale: 'fr-FR' });
    const pageErrors = [];
    page.on('pageerror', (error) => {
      pageErrors.push(error);
    });

    await page.route('https://fonts.googleapis.com/**', (route) =>
      route.fulfill({ status: 200, contentType: 'text/css', body: '' }));
    await page.route('https://fonts.gstatic.com/**', (route) =>
      route.fulfill({ status: 204, body: '' }));

    if (mockScript) {
      await page.addInitScript(mockScript);
    }
    await page.goto(`${server.baseUrl}${pathSuffix}`, { waitUntil: 'domcontentloaded' });
    if (typeof afterPage === 'function') {
      await afterPage(page);
    }
    await runTest(page);
    assert.deepEqual(pageErrors.map((error) => error.message), []);
  } finally {
    if (browser) {
      await browser.close();
    }
    await server.close();
  }
}

async function readDownloadText(download) {
  const filePath = await download.path();
  return fs.readFile(filePath, 'utf8');
}

async function assertTextContains(locator, expectedText) {
  const text = await locator.textContent();
  assert.match(String(text || ''), new RegExp(escapeRegExp(expectedText)));
}

function escapeRegExp(value) {
  return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

module.exports = {
  assertTextContains,
  openBrowserPage,
  readDownloadText,
};
