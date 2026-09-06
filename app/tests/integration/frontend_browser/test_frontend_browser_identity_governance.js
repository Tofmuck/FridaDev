'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const { openBrowserPage } = require('./helpers/browser_test_helpers.js');

test('identity governance visibly separates scopes and never edits readonly historical keys', async () => {
  await openBrowserPage({ pathSuffix: '/admin.css' }, async (page) => {
    const origin = new URL(page.url()).origin;
    await page.setContent('<main><div id="meta"></div><div id="items"></div></main>');
    await page.addScriptTag({ url: `${origin}/admin_ui_common.js` });
    await page.addScriptTag({ url: `${origin}/hermeneutic_admin/render_identity_governance.js` });
    await page.evaluate(() => {
      window.FridaHermeneuticIdentityGovernance.renderIdentityGovernance(
        document.getElementById('meta'),
        document.getElementById('items'),
        {
          governance_version: 'v1',
          editable_count: 1,
          readonly_count: 3,
          active_judge_v2_count: 1,
          active_auxiliary_count: 1,
          active_legacy_compatibility_count: 1,
          legacy_inactive_count: 1,
          items: [
            { key: 'IDENTITY_MUTABLE_MAX_CHARS', label: 'Mutable max chars', category: 'active_judge_v2_readonly', active_scope: 'mutable_identity_judge_v2_add_only', editable: false },
            { key: 'CONTEXT_HINTS_MAX_ITEMS', label: 'Context hints max items', category: 'active_auxiliary_editable', active_scope: 'dialogic_context_hints', editable: true, value_type: 'int', current_value: 2 },
            { key: 'IDENTITY_DECAY_FACTOR', label: 'Identity decay factor', category: 'active_legacy_compatibility_readonly', active_scope: 'legacy_identity_weight_decay', editable: false },
            { key: 'IDENTITY_MIN_CONFIDENCE', label: 'Minimum confidence', category: 'legacy_inactive_readonly', active_scope: 'inactive_legacy', editable: false },
          ],
        },
      );
    });

    const text = await page.locator('#items').innerText();
    assert.match(text, /Juge mutable V2 actif/);
    assert.match(text, /Auxiliaire runtime actif/);
    assert.match(text, /Compatibilite legacy active/);
    assert.match(text, /Legacy inactif/);
    assert.equal(await page.locator('form[data-identity-governance-key]').count(), 1);
    assert.equal(await page.locator('[data-identity-governance-key="IDENTITY_MIN_CONFIDENCE"] form').count(), 0);
  });
});
