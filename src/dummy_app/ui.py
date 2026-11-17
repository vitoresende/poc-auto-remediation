DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sentry Dummy App — Auto-Remediation Agent PoC</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen font-sans">
  <div class="max-w-7xl mx-auto px-6 py-8">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-800">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-medium mb-2">
          Package 1 (1.1, 1.2 &amp; 1.3) • Sentry + GitHub Auto-Remediation PoC
        </div>
        <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-white">
          Sentry Error &amp; PII Generator (Dummy App)
        </h1>
        <p class="text-slate-400 text-sm mt-1">
          Trigger realistic runtime exceptions containing PII (CPF, SSN, Credit Card, Password, Bearer JWT, Email) and export JSON fixtures automatically.
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button
          onclick="triggerAllScenarios()"
          class="px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm shadow-lg shadow-emerald-900/30 transition cursor-pointer"
        >
          ⚡ Trigger All Scenarios (Generate 4 Fixtures)
        </button>
      </div>
    </header>

    <!-- Sentry Configuration Bar -->
    <section class="mt-6 bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <span id="sentry-dot" class="w-3 h-3 rounded-full bg-amber-400 animate-pulse"></span>
        <div>
          <div class="text-sm font-medium text-white" id="sentry-status-label">
            Checking Sentry SDK status...
          </div>
          <div class="text-xs text-slate-400">
            <code>send_default_pii=True</code> • <code>include_local_variables=True</code> • Fixtures saved in <code>fixtures/</code>
          </div>
        </div>
      </div>
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 flex-1 max-w-xl">
        <input
          id="dsn-input"
          type="text"
          placeholder="Paste your SENTRY_DSN (https://key@o0.ingest.sentry.io/0) or leave blank for local offline mode"
          class="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
        />
        <button
          onclick="updateSentryDsn()"
          class="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-medium text-slate-200 transition cursor-pointer"
        >
          Update DSN
        </button>
      </div>
    </section>

    <!-- Scenarios Grid -->
    <section class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Scenario 1 -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="px-2.5 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 text-xs font-mono">
              TypeError (NoneType Subscript)
            </span>
            <span class="text-xs text-slate-500 font-mono">checkout_service.py</span>
          </div>
          <h2 class="text-base font-semibold text-white">1. Checkout Without Coupon (NoneType Discount)</h2>
          <p class="text-xs text-slate-400 mt-1">
            Simulates an order where <code>discount: null</code> causes a crash when indexing <code>discount["percentage"]</code>.
          </p>
          <div class="mt-3 text-xs text-slate-300 bg-slate-950/80 border border-slate-800/80 rounded-lg p-2.5 font-mono space-y-1">
            <div><span class="text-amber-400">Injected PII:</span> CPF, Credit Card PAN, CVV, Email, Bearer JWT</div>
            <div><span class="text-indigo-400">Fixture:</span> fixtures/sentry_discount_none_bug.json</div>
          </div>
        </div>
        <button
          onclick="triggerScenario('discount-bug')"
          class="mt-4 w-full py-2.5 px-4 rounded-lg bg-rose-600/90 hover:bg-rose-500 text-white font-medium text-sm transition cursor-pointer"
        >
          🐞 Trigger Error #1 (Checkout Discount)
        </button>
      </div>

      <!-- Scenario 2 -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="px-2.5 py-0.5 rounded bg-orange-500/15 text-orange-300 border border-orange-500/30 text-xs font-mono">
              ZeroDivisionError
            </span>
            <span class="text-xs text-slate-500 font-mono">checkout_service.py</span>
          </div>
          <h2 class="text-base font-semibold text-white">2. Installment Plan Division by Zero</h2>
          <p class="text-xs text-slate-400 mt-1">
            Simulates a one-click checkout payload passing <code>installments: 0</code>, raising <code>ZeroDivisionError</code>.
          </p>
          <div class="mt-3 text-xs text-slate-300 bg-slate-950/80 border border-slate-800/80 rounded-lg p-2.5 font-mono space-y-1">
            <div><span class="text-amber-400">Injected PII:</span> CPF, SSN, Full Card Number, Bearer Token, Full Name</div>
            <div><span class="text-indigo-400">Fixture:</span> fixtures/sentry_zero_division_installments.json</div>
          </div>
        </div>
        <button
          onclick="triggerScenario('zero-division')"
          class="mt-4 w-full py-2.5 px-4 rounded-lg bg-orange-600/90 hover:bg-orange-500 text-white font-medium text-sm transition cursor-pointer"
        >
          🐞 Trigger Error #2 (ZeroDivisionError)
        </button>
      </div>

      <!-- Scenario 3 -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="px-2.5 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30 text-xs font-mono">
              TypeError (float + str)
            </span>
            <span class="text-xs text-slate-500 font-mono">auth_billing_service.py</span>
          </div>
          <h2 class="text-base font-semibold text-white">3. Recurring Billing Unparsed String Fee</h2>
          <p class="text-xs text-slate-400 mt-1">
            Adds <code>base_plan_price (float) + gateway_fee_override ("14.90")</code> with live credentials in scope.
          </p>
          <div class="mt-3 text-xs text-slate-300 bg-slate-950/80 border border-slate-800/80 rounded-lg p-2.5 font-mono space-y-1">
            <div><span class="text-amber-400">Injected PII:</span> Plaintext Password, API Secret Key, SSN, CPF, JWT</div>
            <div><span class="text-indigo-400">Fixture:</span> fixtures/sentry_type_mismatch_billing.json</div>
          </div>
        </div>
        <button
          onclick="triggerScenario('type-mismatch')"
          class="mt-4 w-full py-2.5 px-4 rounded-lg bg-purple-600/90 hover:bg-purple-500 text-white font-medium text-sm transition cursor-pointer"
        >
          🐞 Trigger Error #3 (TypeError + Credentials)
        </button>
      </div>

      <!-- Scenario 4 -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
        <div>
          <div class="flex items-center justify-between gap-2 mb-2">
            <span class="px-2.5 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 text-xs font-mono">
              AttributeError + 35 Breadcrumbs
            </span>
            <span class="text-xs text-slate-500 font-mono">auth_billing_service.py</span>
          </div>
          <h2 class="text-base font-semibold text-white">4. Multi-Level Call Stack &amp; Breadcrumb Flood</h2>
          <p class="text-xs text-slate-400 mt-1">
            3 nested function calls + 35 redundant polling breadcrumbs before crashing on <code>settlement_code.upper()</code>.
          </p>
          <div class="mt-3 text-xs text-slate-300 bg-slate-950/80 border border-slate-800/80 rounded-lg p-2.5 font-mono space-y-1">
            <div><span class="text-amber-400">PII + Noise:</span> 35 polling logs + CPF, SSN, Credit Card &amp; Token</div>
            <div><span class="text-indigo-400">Fixture:</span> fixtures/sentry_breadcrumb_flood_settlement.json</div>
          </div>
        </div>
        <button
          onclick="triggerScenario('breadcrumb-flood')"
          class="mt-4 w-full py-2.5 px-4 rounded-lg bg-cyan-600/90 hover:bg-cyan-500 text-white font-medium text-sm transition cursor-pointer"
        >
          🐞 Trigger Error #4 (Call Stack + Breadcrumb Flood)
        </button>
      </div>
    </section>

    <!-- Live Inspector & Fixtures List -->
    <section class="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Saved Fixtures Panel -->
      <div class="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-sm font-semibold text-white">📂 Captured Fixtures (Package 1.3)</h3>
          <button onclick="loadFixtures()" class="text-xs text-indigo-400 hover:underline cursor-pointer">Refresh</button>
        </div>
        <p class="text-xs text-slate-400 mb-3">
          Click a fixture file to inspect the raw Sentry payload containing unsanitized PII:
        </p>
        <ul id="fixtures-list" class="space-y-2 text-xs font-mono text-slate-300">
          <li class="text-slate-500">No fixtures generated yet.</li>
        </ul>
      </div>

      <!-- Event JSON Viewer -->
      <div class="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
        <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
          <div>
            <h3 class="text-sm font-semibold text-white" id="inspector-title">
              🔍 Sentry Payload Inspector (Raw Event with PII)
            </h3>
            <p class="text-xs text-slate-400" id="inspector-subtitle">
              Trigger a scenario above to inspect the exact JSON payload captured by the Sentry SDK.
            </p>
          </div>
          <span id="event-badge" class="hidden px-2.5 py-1 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-mono"></span>
        </div>
        <pre
          id="json-viewer"
          class="flex-1 bg-slate-950 border border-slate-800 rounded-lg p-4 text-xs font-mono text-emerald-300 overflow-x-auto max-h-[520px] overflow-y-auto"
        >// Waiting for error trigger...</pre>
      </div>
    </section>
  </div>

  <script>
    async function refreshStatus() {
      const res = await fetch('/api/config/sentry');
      const data = await res.json();
      const dot = document.getElementById('sentry-dot');
      const label = document.getElementById('sentry-status-label');
      if (data.remote_sentry_enabled) {
        dot.className = 'w-3 h-3 rounded-full bg-emerald-400';
        label.textContent = `Connected to Sentry Cloud (${data.masked_dsn}) + Saving Local Fixtures`;
      } else {
        dot.className = 'w-3 h-3 rounded-full bg-amber-400';
        label.textContent = 'Local Offline Sandbox Mode Active (Generating full Sentry SDK events in fixtures/ without cloud upload)';
      }
    }

    async function updateSentryDsn() {
      const dsn = document.getElementById('dsn-input').value.trim();
      const res = await fetch('/api/config/sentry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sentry_dsn: dsn })
      });
      await res.json();
      await refreshStatus();
    }

    async function loadFixtures() {
      const res = await fetch('/api/fixtures');
      const data = await res.json();
      const list = document.getElementById('fixtures-list');
      if (!data.fixtures || data.fixtures.length === 0) {
        list.innerHTML = '<li class="text-slate-500">No fixtures generated yet.</li>';
        return;
      }
      list.innerHTML = data.fixtures.map(f => `
        <li>
          <button
            onclick="viewFixture('${f.name}')"
            class="w-full text-left px-3 py-2 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 flex items-center justify-between transition cursor-pointer"
          >
            <span class="truncate text-indigo-300">${f.name}</span>
            <span class="text-slate-500 text-[10px] ml-2">${(f.size_bytes / 1024).toFixed(1)} KB</span>
          </button>
        </li>
      `).join('');
    }

    async function viewFixture(filename) {
      const res = await fetch(`/api/fixtures/${encodeURIComponent(filename)}`);
      const data = await res.json();
      document.getElementById('inspector-title').textContent = `📄 Fixture: fixtures/${filename}`;
      document.getElementById('inspector-subtitle').textContent = `Event ID: ${data.event_id || 'N/A'} • Transaction: ${data.transaction || 'N/A'}`;
      const badge = document.getElementById('event-badge');
      badge.classList.remove('hidden');
      badge.textContent = `event_id: ${data.event_id || 'N/A'}`;
      document.getElementById('json-viewer').textContent = JSON.stringify(data, null, 2);
    }

    async function triggerScenario(slug) {
      document.getElementById('inspector-subtitle').textContent = `Triggering scenario ${slug}...`;
      const res = await fetch(`/api/scenarios/${slug}?user_email=jane.doe@enterprise.io&session_token=tok_live_9988776655`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiY3BmIjoiMTIzLjQ1Ni43ODktMDAiLCJlbWFpbCI6ImphbmUuZG9lQGVudGVycHJpc2UuaW8ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c',
          'X-Customer-CPF': '123.456.789-00',
          'X-Api-Key': 'api_key_mock_51NzPiiSecretKey987654321'
        }
      });
      const result = await res.json();
      const badge = document.getElementById('event-badge');
      badge.classList.remove('hidden');
      badge.textContent = `event_id: ${result.sentry_event_id || 'captured'}`;
      document.getElementById('inspector-title').textContent = `🚨 Captured Exception: ${result.exception_type}`;
      document.getElementById('inspector-subtitle').textContent = `Saved to: ${result.saved_fixture || 'fixtures/'} • Sent to Remote Sentry: ${result.sent_to_remote_sentry ? 'Yes' : 'Local Offline Mode'}`;
      document.getElementById('json-viewer').textContent = JSON.stringify(result.sentry_payload_preview || result, null, 2);
      await loadFixtures();
    }

    async function triggerAllScenarios() {
      const slugs = ['discount-bug', 'zero-division', 'type-mismatch', 'breadcrumb-flood'];
      for (const slug of slugs) {
        await triggerScenario(slug);
      }
    }

    refreshStatus();
    loadFixtures();
  </script>
</body>
</html>
"""
