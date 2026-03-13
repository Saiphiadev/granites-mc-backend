/**
 * Granites MC — Data injection layer
 * Fetches real Odoo data via API and injects into TailAdmin pages.
 * This file is appended to each relevant page without modifying TailAdmin's core.
 *
 * Pages connected:
 *   /app/crm           → Dashboard (index.html)
 *   /app/crm/clients   → Liste Clients (basic-tables.html)
 *   /app/crm/client     → Fiche Client (profile.html)
 *   /app/crm/calendrier → Calendrier (calendar.html)
 *   /app/crm/nouveau    → Nouveau Client (form-elements.html)
 *   /app/crm/pipeline   → Pipeline CRM (bar-chart.html)
 *   /app/crm/stats      → Statistiques (line-chart.html)
 *   /app/crm/login      → Connexion (signin.html)
 */

// ApexCharts CDN is loaded via <script> tag in HTML (before this file)

const GMC_API = window.location.origin;

const GMC = {
  // ══════════════════════════════════════════════════════════════
  //  UTILITIES
  // ══════════════════════════════════════════════════════════════
  formatNumber(n) {
    return new Intl.NumberFormat('fr-CA').format(n);
  },
  formatMoney(n) {
    if (!n) return '—';
    return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
  },
  scoreBadge(score) {
    const s = (score || '').toUpperCase();
    const cls = s === 'A' ? 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-500'
              : s === 'B' ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400'
              : s === 'C' ? 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-500'
              : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400';
    return `<span class="inline-flex rounded-full px-2 py-0.5 text-theme-xs font-medium ${cls}">${score || '—'}</span>`;
  },

  // Wait for ApexCharts then call fn
  whenApexReady(fn, retries = 20) {
    if (typeof ApexCharts !== 'undefined') { fn(); return; }
    if (retries <= 0) { console.warn('ApexCharts never loaded'); return; }
    setTimeout(() => GMC.whenApexReady(fn, retries - 1), 300);
  },

  // Destroy ApexCharts instance on element
  destroyChart(el) {
    if (!el) return;
    try {
      if (window.Apex && window.Apex._chartInstances) {
        window.Apex._chartInstances.forEach(inst => {
          if (inst.el === el) { try { inst.destroy(); } catch(e){} }
        });
      }
      const id = el.getAttribute('id');
      if (id) {
        try { const c = ApexCharts.getChartByID(id); if (c) c.destroy(); } catch(e) {}
      }
    } catch(e) {}
    el.innerHTML = '';
  },

  // ══════════════════════════════════════════════════════════════
  //  1. DASHBOARD (index.html → /app/crm)
  // ══════════════════════════════════════════════════════════════
  async initDashboard() {
    try {
      const [clientsRes, statsRes, pipelineRes] = await Promise.all([
        fetch(`${GMC_API}/api/crm/clients`),
        fetch(`${GMC_API}/api/crm/stats`),
        fetch(`${GMC_API}/api/crm/pipeline`),
      ]);
      const clientsData = await clientsRes.json();
      const stats = await statsRes.json();
      const pipeline = await pipelineRes.json();
      const clients = clientsData.clients || [];

      // KPI metrics
      const total = clients.length;
      const scoreA = clients.filter(c => (c.x_score_client || '').toUpperCase() === 'A').length;
      const territoires = [...new Set(clients.map(c => c.territoire).filter(Boolean))].length;
      const avecVentes = clients.filter(c => (c.x_ventes_total || 0) > 0).length;

      const metricValues = document.querySelectorAll('.text-title-sm');
      if (metricValues[0]) metricValues[0].textContent = GMC.formatNumber(total);
      if (metricValues[1]) metricValues[1].textContent = GMC.formatNumber(scoreA);

      const metricLabels = document.querySelectorAll('.text-sm.text-gray-500');
      if (metricLabels[0]) metricLabels[0].textContent = 'Clients actifs';
      if (metricLabels[1]) metricLabels[1].textContent = 'Score A (VIP)';

      const badges = document.querySelectorAll('[class*="rounded-full"][class*="text-sm"][class*="font-medium"]');
      if (badges[0]) badges[0].innerHTML = `${territoires} terr.`;
      if (badges[1]) badges[1].innerHTML = `${avecVentes} ventes`;

      // Charts
      GMC.renderDashboardCharts(clients);

      // Top clients table
      GMC.updateRecentOrdersTable(clients);

      // Demographic section → territory breakdown
      GMC.updateDemographicSection(clients);

      // Statistics section — update with pipeline revenue
      if (stats.pipeline_revenue) {
        const statItems = document.querySelectorAll('.text-title-sm');
        // Target, Revenue, Today labels
      }

    } catch (err) {
      console.error('GMC Dashboard init error:', err);
    }
  },

  renderDashboardCharts(clients) {
    GMC.whenApexReady(() => {
      setTimeout(() => {
        // Territory bar chart → chartOne
        const terrCounts = {};
        clients.forEach(c => {
          const t = c.territoire || 'Non assigné';
          terrCounts[t] = (terrCounts[t] || 0) + 1;
        });
        const terrLabels = Object.keys(terrCounts).sort((a, b) => terrCounts[b] - terrCounts[a]);
        const terrValues = terrLabels.map(l => terrCounts[l]);

        const chartEl = document.getElementById('chartOne');
        if (chartEl) {
          GMC.destroyChart(chartEl);
          new ApexCharts(chartEl, {
            chart: { id: 'gmc-terr', type: 'bar', height: 310, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
            series: [{ name: 'Clients', data: terrValues }],
            xaxis: { categories: terrLabels, labels: { style: { fontSize: '11px', colors: '#667085' } } },
            yaxis: { labels: { style: { fontSize: '11px', colors: '#667085' } } },
            colors: ['#c07a4a'],
            plotOptions: { bar: { borderRadius: 4, columnWidth: '55%' } },
            dataLabels: { enabled: false },
            grid: { borderColor: '#e4e7ec', strokeDashArray: 4 },
          }).render();
        }

        // Score donut → chartTwo
        const scoreCounts = { A: 0, B: 0, C: 0, Autre: 0 };
        clients.forEach(c => {
          const s = (c.x_score_client || '').toUpperCase();
          if (scoreCounts.hasOwnProperty(s)) scoreCounts[s]++;
          else scoreCounts['Autre']++;
        });
        const scoreLabels = Object.keys(scoreCounts).filter(k => scoreCounts[k] > 0);
        const scoreValues = scoreLabels.map(l => scoreCounts[l]);
        const scoreColors = { A: '#059669', B: '#3b82f6', C: '#f59e0b', Autre: '#98a2b3' };

        const chartEl2 = document.getElementById('chartTwo');
        if (chartEl2) {
          GMC.destroyChart(chartEl2);
          new ApexCharts(chartEl2, {
            chart: { id: 'gmc-scores', type: 'donut', height: 280, fontFamily: 'Outfit, sans-serif' },
            series: scoreValues,
            labels: scoreLabels.map(l => 'Score ' + l),
            colors: scoreLabels.map(l => scoreColors[l] || '#98a2b3'),
            legend: { position: 'bottom', fontSize: '13px' },
            dataLabels: { enabled: true, style: { fontSize: '13px', fontWeight: 600 } },
            plotOptions: { pie: { donut: { size: '55%' } } },
          }).render();
        }
      }, 2500);
    });
  },

  updateRecentOrdersTable(clients) {
    const topClients = [...clients]
      .filter(c => c.x_ventes_total > 0)
      .sort((a, b) => (b.x_ventes_total || 0) - (a.x_ventes_total || 0))
      .slice(0, 5);

    const tables = document.querySelectorAll('table tbody');
    if (tables.length > 0) {
      const tbody = tables[tables.length - 1];
      tbody.innerHTML = topClients.map(c => `
        <tr class="border-b border-gray-100 dark:border-gray-800">
          <td class="px-5 py-4 sm:px-6">
            <div class="flex items-center gap-3">
              <div>
                <a href="/app/crm/client?id=${c.id}" class="font-medium text-gray-800 text-theme-sm dark:text-white/90 hover:underline">${c.name || '—'}</a>
                <span class="text-gray-500 text-theme-xs block">${c.email || ''}</span>
              </div>
            </div>
          </td>
          <td class="px-5 py-4 sm:px-6 text-gray-500 text-theme-sm dark:text-gray-400">${c.territoire || '—'}</td>
          <td class="px-5 py-4 sm:px-6 text-gray-500 text-theme-sm dark:text-gray-400">${GMC.formatMoney(c.x_ventes_total)}</td>
          <td class="px-5 py-4 sm:px-6">${GMC.scoreBadge(c.x_score_client)}</td>
        </tr>
      `).join('');
    }

    const theads = document.querySelectorAll('table thead');
    if (theads.length > 0) {
      const thead = theads[theads.length - 1];
      const ths = thead.querySelectorAll('th');
      ['Client', 'Territoire', 'Ventes totales', 'Score'].forEach((l, i) => { if (ths[i]) ths[i].textContent = l; });
    }

    document.querySelectorAll('h4').forEach(h4 => {
      if (h4.textContent.includes('Recent Orders') || h4.textContent.includes('Top Clients')) h4.textContent = 'Top Clients';
    });
  },

  updateDemographicSection(clients) {
    document.querySelectorAll('h4').forEach(h4 => {
      if (h4.textContent.includes('Demographic')) h4.textContent = 'Répartition par territoire';
    });
    document.querySelectorAll('span').forEach(span => {
      if (span.textContent.includes('Number of customer based on country')) span.textContent = 'Nombre de clients par territoire';
    });
  },

  // ══════════════════════════════════════════════════════════════
  //  2. LISTE CLIENTS (basic-tables.html → /app/crm/clients)
  // ══════════════════════════════════════════════════════════════
  async initClientsTable() {
    try {
      const res = await fetch(`${GMC_API}/api/crm/clients`);
      const data = await res.json();
      const clients = data.clients || [];

      const table = document.querySelector('table');
      if (!table) return;

      const thead = table.querySelector('thead');
      if (thead) {
        thead.innerHTML = `<tr>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Client</th>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Territoire</th>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Score</th>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Ville</th>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Téléphone</th>
          <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Ventes</th>
        </tr>`;
      }

      const tbody = table.querySelector('tbody');
      if (tbody) {
        tbody.innerHTML = clients.map(c => `
          <tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-white/5 cursor-pointer" onclick="window.location='/app/crm/client?id=${c.id}'">
            <td class="px-5 py-4">
              <div>
                <p class="font-medium text-gray-800 text-theme-sm dark:text-white/90">${c.name || '—'}</p>
                <span class="text-gray-500 text-theme-xs">${c.email || ''}</span>
              </div>
            </td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.territoire || '—'}</td>
            <td class="px-5 py-4">${GMC.scoreBadge(c.x_score_client)}</td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.city || '—'}</td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.phone || '—'}</td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${GMC.formatMoney(c.x_ventes_total)}</td>
          </tr>
        `).join('');
      }

      // Hide second table if present
      const allTables = document.querySelectorAll('table');
      if (allTables.length > 1) {
        allTables[1].closest('.rounded-2xl, .border, section, div.overflow-hidden')?.remove();
      }

    } catch (err) {
      console.error('GMC Clients Table init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  3. FICHE CLIENT (profile.html → /app/crm/client?id=X)
  // ══════════════════════════════════════════════════════════════
  async initClientProfile() {
    const params = new URLSearchParams(window.location.search);
    const clientId = params.get('id');
    if (!clientId) {
      document.querySelector('main')?.insertAdjacentHTML('afterbegin',
        '<div class="p-6 text-center text-gray-500">Sélectionnez un client depuis la <a href="/app/crm/clients" class="text-brand-500 underline">liste</a>.</div>');
      return;
    }

    try {
      const res = await fetch(`${GMC_API}/api/crm/clients/${clientId}`);
      const client = await res.json();

      // Update profile name
      const nameEl = document.querySelector('h3.text-title-sm, h4.text-title-sm');
      if (nameEl) nameEl.textContent = client.name || '—';

      // Update subtitle/role
      document.querySelectorAll('.text-sm.text-gray-500').forEach(el => {
        if (el.closest('.flex.flex-col.items-center')) {
          el.textContent = [client.x_type_client, client.territoire].filter(Boolean).join(' — ') || 'Client';
        }
      });

      // Build client info section
      const mainContent = document.querySelector('main .mx-auto');
      if (mainContent) {
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 mt-6';

        const fields = [
          ['Email', client.email],
          ['Téléphone', client.phone],
          ['Ville', client.city],
          ['Territoire', client.territoire],
          ['Score', client.x_score_client],
          ['Type', client.x_type_client],
          ['Ventes totales', GMC.formatMoney(client.x_ventes_total)],
          ['Heures ouverture', client.x_hours],
          ['Site web', client.website],
        ].filter(([,v]) => v);

        detailsDiv.innerHTML = `
          <h4 class="text-lg font-semibold text-gray-800 dark:text-white/90 mb-4">Informations du client</h4>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            ${fields.map(([label, val]) => `<div><span class="text-sm text-gray-500">${label}</span><p class="font-medium text-gray-800 dark:text-white/90">${val || '—'}</p></div>`).join('')}
          </div>
          ${client.x_competiteurs ? `<div class="mt-4"><span class="text-sm text-gray-500">Compétiteurs</span><p class="font-medium text-gray-800 dark:text-white/90">${client.x_competiteurs}</p></div>` : ''}
          ${client.x_notes_ia ? `<div class="mt-4"><span class="text-sm text-gray-500">Notes IA</span><p class="text-gray-600 dark:text-gray-300 text-sm whitespace-pre-line">${client.x_notes_ia}</p></div>` : ''}
          ${client.x_notes_terrain ? `<div class="mt-4"><span class="text-sm text-gray-500">Notes terrain</span><p class="text-gray-600 dark:text-gray-300 text-sm whitespace-pre-line">${client.x_notes_terrain}</p></div>` : ''}
        `;
        mainContent.appendChild(detailsDiv);

        // Show leads if present
        if (client.leads && client.leads.length > 0) {
          const leadsDiv = document.createElement('div');
          leadsDiv.className = 'rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 mt-6';
          leadsDiv.innerHTML = `
            <h4 class="text-lg font-semibold text-gray-800 dark:text-white/90 mb-4">Opportunités (${client.leads.length})</h4>
            <div class="overflow-x-auto">
              <table class="min-w-full">
                <thead><tr>
                  <th class="px-4 py-2 text-start text-sm text-gray-500">Nom</th>
                  <th class="px-4 py-2 text-start text-sm text-gray-500">Étape</th>
                  <th class="px-4 py-2 text-start text-sm text-gray-500">Revenu</th>
                  <th class="px-4 py-2 text-start text-sm text-gray-500">Probabilité</th>
                </tr></thead>
                <tbody>${client.leads.map(l => `
                  <tr class="border-b border-gray-100 dark:border-gray-800">
                    <td class="px-4 py-3 text-sm text-gray-800 dark:text-white/90">${l.name || '—'}</td>
                    <td class="px-4 py-3 text-sm text-gray-500">${l.stage_name || '—'}</td>
                    <td class="px-4 py-3 text-sm text-gray-500">${GMC.formatMoney(l.expected_revenue)}</td>
                    <td class="px-4 py-3 text-sm text-gray-500">${l.probability || 0}%</td>
                  </tr>
                `).join('')}</tbody>
              </table>
            </div>
          `;
          mainContent.appendChild(leadsDiv);
        }

        // Show activities if present
        if (client.activities && client.activities.length > 0) {
          const actDiv = document.createElement('div');
          actDiv.className = 'rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 mt-6';
          actDiv.innerHTML = `
            <h4 class="text-lg font-semibold text-gray-800 dark:text-white/90 mb-4">Activités récentes (${client.activities.length})</h4>
            <div class="space-y-3">${client.activities.slice(0, 10).map(a => `
              <div class="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-white/5">
                <div class="flex-1">
                  <p class="text-sm font-medium text-gray-800 dark:text-white/90">${a.summary || a.type || 'Activité'}</p>
                  <p class="text-xs text-gray-500">${a.date || ''} — ${a.state || ''}</p>
                  ${a.note ? `<p class="text-xs text-gray-400 mt-1">${a.note.substring(0, 200)}</p>` : ''}
                </div>
              </div>
            `).join('')}</div>
          `;
          mainContent.appendChild(actDiv);
        }
      }

    } catch (err) {
      console.error('GMC Client Profile init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  4. CALENDRIER (calendar.html → /app/crm/calendrier)
  // ══════════════════════════════════════════════════════════════
  async initCalendar() {
    try {
      const res = await fetch(`${GMC_API}/api/calendar/events?limit=200`);
      const data = await res.json();
      const events = data.events || [];

      // TailAdmin calendar uses FullCalendar (rendered by bundle.js in Alpine)
      // We inject our events after FullCalendar initializes
      setTimeout(() => {
        // Find the calendar container
        const calEl = document.getElementById('calendar');
        if (!calEl) return;

        // Build event list sidebar
        const sidebar = document.querySelector('.xl\\:w-\\[280px\\], .calendar-sidebar');

        // Replace the hardcoded event list
        const eventListContainer = document.querySelector('[class*="space-y"]');
        if (eventListContainer && eventListContainer.closest('[class*="xl:w-"]')) {
          const upcoming = events
            .filter(e => new Date(e.start) >= new Date())
            .sort((a, b) => new Date(a.start) - new Date(b.start))
            .slice(0, 10);

          eventListContainer.innerHTML = upcoming.length === 0
            ? '<p class="text-sm text-gray-500">Aucun événement à venir</p>'
            : upcoming.map(e => {
              const d = new Date(e.start);
              const dateStr = d.toLocaleDateString('fr-CA', { day: 'numeric', month: 'short' });
              const timeStr = e.allday ? 'Journée' : d.toLocaleTimeString('fr-CA', { hour: '2-digit', minute: '2-digit' });
              return `
                <div class="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5">
                  <div class="w-2 h-2 mt-2 rounded-full bg-brand-500 shrink-0"></div>
                  <div class="flex-1">
                    <p class="text-sm font-medium text-gray-800 dark:text-white/90">${e.name}</p>
                    <p class="text-xs text-gray-500">${dateStr} — ${timeStr}</p>
                    ${e.location ? `<p class="text-xs text-gray-400">${e.location}</p>` : ''}
                  </div>
                </div>
              `;
            }).join('');
        }

        // Try to add events to FullCalendar if it's initialized
        // FullCalendar instance is typically stored in Alpine data
        const fcEvents = events.map(e => ({
          title: e.name,
          start: e.start,
          end: e.stop || e.start,
          allDay: e.allday || false,
          extendedProps: { location: e.location, description: e.description },
        }));

        // Attempt to find FullCalendar instance
        if (window.__FULL_CALENDAR__) {
          window.__FULL_CALENDAR__.removeAllEvents();
          window.__FULL_CALENDAR__.addEventSource(fcEvents);
        }

      }, 3000); // Wait for FullCalendar to init

      // Update section labels
      document.querySelectorAll('h5, h4, h3').forEach(el => {
        if (el.textContent.includes('Upcoming Events')) el.textContent = 'Événements à venir';
        if (el.textContent.includes('Events')) el.textContent = 'Événements';
      });

    } catch (err) {
      console.error('GMC Calendar init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  5. NOUVEAU CLIENT (form-elements.html → /app/crm/nouveau)
  // ══════════════════════════════════════════════════════════════
  async initNewClientForm() {
    try {
      // Fetch territories for dropdown
      const terrRes = await fetch(`${GMC_API}/api/crm/territories`);
      const terrData = await terrRes.json();
      const territories = terrData.territories || [];

      // Replace the form content with CRM fields
      const formContainer = document.querySelector('form') || document.querySelector('.grid.grid-cols-1.gap-6');
      const mainContent = document.querySelector('main .mx-auto .grid, main .mx-auto');
      if (!mainContent) return;

      // Clear default form content
      mainContent.innerHTML = `
        <div class="rounded-2xl border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-white/[0.03]">
          <h4 class="text-lg font-semibold text-gray-800 dark:text-white/90 mb-6">Créer un nouveau client</h4>
          <form id="gmc-new-client-form" class="space-y-5">
            <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nom de l'entreprise *</label>
                <input type="text" name="name" required class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="Ex: Cuisines ABC inc.">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email</label>
                <input type="email" name="email" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="info@example.com">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Téléphone</label>
                <input type="tel" name="phone" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="(819) 555-1234">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Ville</label>
                <input type="text" name="city" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="Sherbrooke">
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Territoire</label>
                <select name="territoire_id" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                  <option value="">— Sélectionner —</option>
                  ${territories.map(t => `<option value="${t.id}">${t.name}</option>`).join('')}
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Type de client</label>
                <select name="x_type_client" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                  <option value="">— Sélectionner —</option>
                  <option value="Fabricant">Fabricant</option>
                  <option value="Détaillant">Détaillant</option>
                  <option value="Designer">Designer</option>
                  <option value="Entrepreneur">Entrepreneur</option>
                  <option value="Particulier">Particulier</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Score</label>
                <select name="x_score_client" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white">
                  <option value="">— Sélectionner —</option>
                  <option value="A">A — VIP</option>
                  <option value="B">B — Régulier</option>
                  <option value="C">C — Occasionnel</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Site web</label>
                <input type="url" name="website" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="https://example.com">
              </div>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Notes</label>
              <textarea name="comment" rows="3" class="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-900 dark:text-white" placeholder="Notes internes..."></textarea>
            </div>
            <div class="flex items-center gap-3">
              <button type="submit" class="rounded-lg bg-brand-500 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-600 transition">
                Créer le client
              </button>
              <span id="gmc-form-status" class="text-sm text-gray-500"></span>
            </div>
          </form>
        </div>
      `;

      // Form submission handler
      document.getElementById('gmc-new-client-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const statusEl = document.getElementById('gmc-form-status');
        statusEl.textContent = 'Création en cours...';
        statusEl.className = 'text-sm text-gray-500';

        const payload = {
          name: formData.get('name'),
          email: formData.get('email') || undefined,
          phone: formData.get('phone') || undefined,
          city: formData.get('city') || undefined,
          website: formData.get('website') || undefined,
          x_type_client: formData.get('x_type_client') || undefined,
          x_score_client: formData.get('x_score_client') || undefined,
          comment: formData.get('comment') || undefined,
        };

        try {
          const res = await fetch(`${GMC_API}/api/admin/create-partner`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          const result = await res.json();

          if (result.partner_id) {
            statusEl.textContent = `Client créé avec succès ! (ID: ${result.partner_id})`;
            statusEl.className = 'text-sm text-success-600';
            // Redirect to profile after 1.5s
            setTimeout(() => {
              window.location.href = `/app/crm/client?id=${result.partner_id}`;
            }, 1500);
          } else {
            statusEl.textContent = `Erreur: ${result.detail || 'Impossible de créer le client'}`;
            statusEl.className = 'text-sm text-error-600';
          }
        } catch (err) {
          statusEl.textContent = 'Erreur de connexion au serveur';
          statusEl.className = 'text-sm text-error-600';
        }
      });

    } catch (err) {
      console.error('GMC New Client Form init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  6. PIPELINE CRM (bar-chart.html → /app/crm/pipeline)
  // ══════════════════════════════════════════════════════════════
  async initPipeline() {
    try {
      const [pipelineRes, statsRes, repsRes] = await Promise.all([
        fetch(`${GMC_API}/api/crm/pipeline?limit=100`),
        fetch(`${GMC_API}/api/crm/stats`),
        fetch(`${GMC_API}/api/crm/reps`),
      ]);
      const pipeline = await pipelineRes.json();
      const stats = await statsRes.json();
      const reps = await repsRes.json();
      const leads = pipeline.leads || [];

      // Pipeline by stage — bar chart
      const stageCounts = {};
      const stageRevenue = {};
      leads.forEach(l => {
        const stage = l.stage_name || 'Non défini';
        stageCounts[stage] = (stageCounts[stage] || 0) + 1;
        stageRevenue[stage] = (stageRevenue[stage] || 0) + (l.expected_revenue || 0);
      });
      const stageLabels = Object.keys(stageCounts);
      const stageCountValues = stageLabels.map(l => stageCounts[l]);
      const stageRevenueValues = stageLabels.map(l => Math.round(stageRevenue[l]));

      // KPI cards at top
      const mainContent = document.querySelector('main .mx-auto');
      if (mainContent) {
        // Add KPI section before charts
        const kpiDiv = document.createElement('div');
        kpiDiv.className = 'grid grid-cols-1 gap-4 md:grid-cols-4 mb-6';
        kpiDiv.innerHTML = `
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Opportunités</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${leads.length}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Revenu pipeline</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${GMC.formatMoney(stats.pipeline_revenue || 0)}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Représentants</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${(reps.reps || []).length}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Étapes</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${stageLabels.length}</p>
          </div>
        `;
        mainContent.insertBefore(kpiDiv, mainContent.firstChild);
      }

      // Replace bar charts with pipeline data
      GMC.whenApexReady(() => {
        setTimeout(() => {
          // Chart 1 — Opportunities by stage (bar)
          const chartEl1 = document.getElementById('chartOne') || document.querySelector('[id^="chart"]');
          if (chartEl1) {
            GMC.destroyChart(chartEl1);
            new ApexCharts(chartEl1, {
              chart: { id: 'pipeline-stages', type: 'bar', height: 350, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
              series: [{ name: 'Opportunités', data: stageCountValues }],
              xaxis: { categories: stageLabels, labels: { style: { fontSize: '11px', colors: '#667085' }, rotate: -45 } },
              colors: ['#c07a4a'],
              plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
              dataLabels: { enabled: true },
              grid: { borderColor: '#e4e7ec', strokeDashArray: 4 },
              title: { text: 'Opportunités par étape', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }

          // Chart 2 — Revenue by stage (bar)
          const chartEl2 = document.getElementById('chartTwo') || document.querySelectorAll('[id^="chart"]')[1];
          if (chartEl2) {
            GMC.destroyChart(chartEl2);
            new ApexCharts(chartEl2, {
              chart: { id: 'pipeline-revenue', type: 'bar', height: 350, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
              series: [{ name: 'Revenu ($)', data: stageRevenueValues }],
              xaxis: { categories: stageLabels, labels: { style: { fontSize: '11px', colors: '#667085' }, rotate: -45 } },
              yaxis: { labels: { formatter: v => GMC.formatMoney(v) } },
              colors: ['#059669'],
              plotOptions: { bar: { borderRadius: 4, columnWidth: '60%' } },
              dataLabels: { enabled: true, formatter: v => GMC.formatMoney(v), style: { fontSize: '10px' } },
              grid: { borderColor: '#e4e7ec', strokeDashArray: 4 },
              title: { text: 'Revenu par étape', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }

          // Chart 3 — Revenue by rep (horizontal bar) if third chart exists
          const chartEl3 = document.getElementById('chartThree') || document.querySelectorAll('[id^="chart"]')[2];
          if (chartEl3 && reps.reps && reps.reps.length > 0) {
            const repNames = reps.reps.map(r => r.name);
            const repRevenues = reps.reps.map(r => Math.round(r.pipeline_revenue || 0));
            GMC.destroyChart(chartEl3);
            new ApexCharts(chartEl3, {
              chart: { id: 'rep-revenue', type: 'bar', height: 350, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
              series: [{ name: 'Pipeline ($)', data: repRevenues }],
              xaxis: { categories: repNames },
              yaxis: { labels: { formatter: v => GMC.formatMoney(v) } },
              colors: ['#3b82f6'],
              plotOptions: { bar: { borderRadius: 4, horizontal: true, columnWidth: '55%' } },
              dataLabels: { enabled: true, formatter: v => GMC.formatMoney(v), style: { fontSize: '10px' } },
              title: { text: 'Pipeline par représentant', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }
        }, 2500);
      });

      // Update page section titles
      document.querySelectorAll('h3, h4, h2').forEach(el => {
        if (el.textContent.includes('Bar Chart')) el.textContent = 'Pipeline CRM';
      });

    } catch (err) {
      console.error('GMC Pipeline init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  7. STATISTIQUES (line-chart.html → /app/crm/stats)
  // ══════════════════════════════════════════════════════════════
  async initStats() {
    try {
      const [statsRes, clientsRes, repsRes] = await Promise.all([
        fetch(`${GMC_API}/api/crm/stats`),
        fetch(`${GMC_API}/api/crm/clients`),
        fetch(`${GMC_API}/api/crm/reps`),
      ]);
      const stats = await statsRes.json();
      const clientsData = await clientsRes.json();
      const repsData = await repsRes.json();
      const clients = clientsData.clients || [];
      const reps = repsData.reps || [];

      // KPI section
      const mainContent = document.querySelector('main .mx-auto');
      if (mainContent) {
        const kpiDiv = document.createElement('div');
        kpiDiv.className = 'grid grid-cols-1 gap-4 md:grid-cols-4 mb-6';
        kpiDiv.innerHTML = `
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Total clients</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${stats.total_clients || 0}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Total leads</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${stats.total_leads || 0}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Revenu pipeline</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${GMC.formatMoney(stats.pipeline_revenue || 0)}</p>
          </div>
          <div class="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03]">
            <p class="text-sm text-gray-500 mb-1">Activités récentes</p>
            <p class="text-2xl font-bold text-gray-800 dark:text-white">${stats.recent_activities_count || 0}</p>
          </div>
        `;
        mainContent.insertBefore(kpiDiv, mainContent.firstChild);
      }

      // Charts with real data
      GMC.whenApexReady(() => {
        setTimeout(() => {
          // Chart 1 — Score distribution (donut)
          const chartEl1 = document.getElementById('chartOne') || document.querySelector('[id^="chart"]');
          if (chartEl1 && stats.clients_by_score) {
            const labels = Object.keys(stats.clients_by_score);
            const values = Object.values(stats.clients_by_score);
            const colors = { A: '#059669', B: '#3b82f6', C: '#f59e0b' };
            GMC.destroyChart(chartEl1);
            new ApexCharts(chartEl1, {
              chart: { id: 'stat-scores', type: 'donut', height: 350, fontFamily: 'Outfit, sans-serif' },
              series: values,
              labels: labels.map(l => `Score ${l}`),
              colors: labels.map(l => colors[l] || '#98a2b3'),
              legend: { position: 'bottom' },
              dataLabels: { enabled: true },
              title: { text: 'Répartition par score', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }

          // Chart 2 — Pipeline by stage (bar)
          const chartEl2 = document.getElementById('chartTwo') || document.querySelectorAll('[id^="chart"]')[1];
          if (chartEl2 && stats.pipeline_by_stage) {
            const stageLabels = Object.keys(stats.pipeline_by_stage);
            const stageValues = Object.values(stats.pipeline_by_stage);
            GMC.destroyChart(chartEl2);
            new ApexCharts(chartEl2, {
              chart: { id: 'stat-pipeline', type: 'bar', height: 350, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
              series: [{ name: 'Leads', data: stageValues }],
              xaxis: { categories: stageLabels },
              colors: ['#c07a4a'],
              plotOptions: { bar: { borderRadius: 4 } },
              title: { text: 'Pipeline par étape', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }

          // Chart 3 — Rep performance (if chart exists)
          const chartEl3 = document.getElementById('chartThree') || document.querySelectorAll('[id^="chart"]')[2];
          if (chartEl3 && reps.length > 0) {
            GMC.destroyChart(chartEl3);
            new ApexCharts(chartEl3, {
              chart: { id: 'stat-reps', type: 'bar', height: 350, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
              series: [
                { name: 'Leads', data: reps.map(r => r.lead_count || 0) },
                { name: 'Pipeline ($k)', data: reps.map(r => Math.round((r.pipeline_revenue || 0) / 1000)) },
              ],
              xaxis: { categories: reps.map(r => r.name) },
              colors: ['#c07a4a', '#059669'],
              plotOptions: { bar: { borderRadius: 4 } },
              title: { text: 'Performance par représentant', style: { fontSize: '14px', fontWeight: 600 } },
            }).render();
          }
        }, 2500);
      });

      // Update page titles
      document.querySelectorAll('h3, h4, h2').forEach(el => {
        if (el.textContent.includes('Line Chart')) el.textContent = 'Statistiques CRM';
      });

    } catch (err) {
      console.error('GMC Stats init error:', err);
    }
  },

  // ══════════════════════════════════════════════════════════════
  //  8. CONNEXION (signin.html → /app/crm/login)
  // ══════════════════════════════════════════════════════════════
  async initLogin() {
    try {
      // Replace login form
      const form = document.querySelector('form');
      if (!form) return;

      // Update form labels
      const labels = form.querySelectorAll('label');
      labels.forEach(l => {
        if (l.textContent.includes('Email')) l.textContent = 'Courriel';
        if (l.textContent.includes('Password')) l.textContent = 'Mot de passe';
      });

      // Update submit button
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.textContent = 'Se connecter';

      // Update links
      form.querySelectorAll('a').forEach(a => {
        if (a.textContent.includes('Sign Up') || a.textContent.includes('Inscription')) {
          a.href = '/app/crm';
          a.textContent = 'Retour au CRM';
        }
      });

      // Add status message area
      const statusDiv = document.createElement('div');
      statusDiv.id = 'gmc-login-status';
      statusDiv.className = 'text-sm text-center mt-3';
      form.appendChild(statusDiv);

      // Handle form submission
      form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = form.querySelector('input[type="email"]')?.value;
        const statusEl = document.getElementById('gmc-login-status');
        if (!email) {
          statusEl.textContent = 'Veuillez entrer votre courriel';
          statusEl.className = 'text-sm text-center mt-3 text-error-600';
          return;
        }
        statusEl.textContent = 'Connexion en cours...';
        statusEl.className = 'text-sm text-center mt-3 text-gray-500';

        try {
          const res = await fetch(`${GMC_API}/api/crm/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
          });
          // The login endpoint uses query param
          const res2 = await fetch(`${GMC_API}/api/crm/auth/login?email=${encodeURIComponent(email)}`, { method: 'POST' });
          const result = await res2.json();

          if (result.user) {
            statusEl.textContent = `Bienvenue, ${result.user.name} !`;
            statusEl.className = 'text-sm text-center mt-3 text-success-600';
            // Store user info
            localStorage.setItem('gmc_user', JSON.stringify(result.user));
            localStorage.setItem('gmc_stats', JSON.stringify(result.stats));
            setTimeout(() => { window.location.href = '/app/crm'; }, 1000);
          } else {
            statusEl.textContent = result.detail || 'Courriel non reconnu';
            statusEl.className = 'text-sm text-center mt-3 text-error-600';
          }
        } catch (err) {
          statusEl.textContent = 'Erreur de connexion';
          statusEl.className = 'text-sm text-center mt-3 text-error-600';
        }
      });

      // Update page text
      document.querySelectorAll('h1, h2, h3, h4, p').forEach(el => {
        const t = el.textContent;
        if (t.includes('Sign In Page')) el.textContent = 'Connexion CRM';
        if (t.includes('Sign in to your account')) el.textContent = 'Connectez-vous au CRM Granites MC';
        if (t.includes('Start for free')) el.textContent = '';
        if (t.includes("Don't have an account")) el.textContent = '';
      });

    } catch (err) {
      console.error('GMC Login init error:', err);
    }
  },
};

// ══════════════════════════════════════════════════════════════
//  AUTO-DETECT PAGE AND INITIALIZE
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;

  if (path.includes('/app/crm/clients')) {
    GMC.initClientsTable();
  } else if (path.includes('/app/crm/client') && !path.includes('clients')) {
    GMC.initClientProfile();
  } else if (path.includes('/app/crm/calendrier')) {
    GMC.initCalendar();
  } else if (path.includes('/app/crm/nouveau')) {
    GMC.initNewClientForm();
  } else if (path.includes('/app/crm/pipeline')) {
    GMC.initPipeline();
  } else if (path.includes('/app/crm/stats')) {
    GMC.initStats();
  } else if (path.includes('/app/crm/login')) {
    GMC.initLogin();
  } else if (path === '/app/crm' || path === '/app/crm/') {
    GMC.initDashboard();
  }
});
