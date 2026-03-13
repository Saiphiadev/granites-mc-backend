/**
 * Granites MC — Data injection layer
 * Fetches real Odoo data via API and injects into TailAdmin pages.
 * This file is appended to each relevant page without modifying TailAdmin's core.
 */
const GMC_API = window.location.origin;

const GMC = {
  // ── Utility ──────────────────────────────────────────────────
  formatNumber(n) {
    return new Intl.NumberFormat('fr-CA').format(n);
  },
  formatMoney(n) {
    if (!n) return '—';
    return new Intl.NumberFormat('fr-CA', { style: 'currency', currency: 'CAD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
  },

  // ── Dashboard (index.html) ──────────────────────────────────
  async initDashboard() {
    try {
      const res = await fetch(`${GMC_API}/api/crm/clients`);
      const data = await res.json();
      const clients = data.clients || [];

      // KPI metrics
      const total = clients.length;
      const scoreA = clients.filter(c => (c.x_score_client || '').toUpperCase() === 'A').length;
      const territoires = [...new Set(clients.map(c => c.territoire).filter(Boolean))].length;
      const avecVentes = clients.filter(c => (c.x_ventes_total || 0) > 0).length;

      // Update metric cards (1st = Customers, 2nd = Orders)
      const metricValues = document.querySelectorAll('.text-title-sm');
      if (metricValues[0]) metricValues[0].textContent = GMC.formatNumber(total);
      if (metricValues[1]) metricValues[1].textContent = GMC.formatNumber(scoreA);

      // Update metric labels
      const metricLabels = document.querySelectorAll('.text-sm.text-gray-500');
      if (metricLabels[0]) metricLabels[0].textContent = 'Clients actifs';
      if (metricLabels[1]) metricLabels[1].textContent = 'Score A (VIP)';

      // Update percentage badges
      const badges = document.querySelectorAll('[class*="rounded-full"][class*="text-sm"][class*="font-medium"]');
      if (badges[0]) badges[0].innerHTML = `${territoires} terr.`;
      if (badges[1]) badges[1].innerHTML = `${avecVentes} ventes`;

      // Update page title
      const pageTitle = document.querySelector('h3.text-lg, h3.text-title-sm');
      // Update charts if ApexCharts is available
      GMC.renderDashboardCharts(clients);

      // Update recent orders table with top clients
      GMC.updateRecentOrdersTable(clients);

      // Update demographic section
      GMC.updateDemographicSection(clients);

    } catch (err) {
      console.error('GMC Dashboard init error:', err);
    }
  },

  renderDashboardCharts(clients) {
    // Wait for ApexCharts to be available and for bundle.js charts to render first
    if (typeof ApexCharts === 'undefined') {
      setTimeout(() => GMC.renderDashboardCharts(clients), 500);
      return;
    }

    // Small delay to let bundle.js charts initialize, then destroy & replace
    setTimeout(() => {
      // Territory bar chart — replace chartOne (monthly sales)
      const terrCounts = {};
      clients.forEach(c => {
        const t = c.territoire || 'Non assigné';
        terrCounts[t] = (terrCounts[t] || 0) + 1;
      });
      const terrLabels = Object.keys(terrCounts).sort((a, b) => terrCounts[b] - terrCounts[a]);
      const terrValues = terrLabels.map(l => terrCounts[l]);

      const chartEl = document.getElementById('chartOne');
      if (chartEl) {
        // Destroy any existing ApexCharts instance
        if (window.Apex && window.Apex._chartInstances) {
          window.Apex._chartInstances.forEach(inst => {
            if (inst.el === chartEl) inst.destroy();
          });
        }
        // Also try ApexCharts.getChartByID
        try {
          const existing = ApexCharts.getChartByID('chartOne');
          if (existing) existing.destroy();
        } catch(e) {}

        chartEl.innerHTML = '';
        const chart = new ApexCharts(chartEl, {
          chart: { id: 'gmc-terr', type: 'bar', height: 310, toolbar: { show: false }, fontFamily: 'Outfit, sans-serif' },
          series: [{ name: 'Clients', data: terrValues }],
          xaxis: { categories: terrLabels, labels: { style: { fontSize: '11px', colors: '#667085' } } },
          yaxis: { labels: { style: { fontSize: '11px', colors: '#667085' } } },
          colors: ['#c07a4a'],
          plotOptions: { bar: { borderRadius: 4, columnWidth: '55%' } },
          dataLabels: { enabled: false },
          grid: { borderColor: '#e4e7ec', strokeDashArray: 4 },
        });
        chart.render();
      }

      // Score donut chart — replace chartTwo (monthly target donut)
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
        try {
          const existing2 = ApexCharts.getChartByID('chartTwo');
          if (existing2) existing2.destroy();
        } catch(e) {}

        chartEl2.innerHTML = '';
        const chart2 = new ApexCharts(chartEl2, {
          chart: { id: 'gmc-scores', type: 'donut', height: 280, fontFamily: 'Outfit, sans-serif' },
          series: scoreValues,
          labels: scoreLabels.map(l => 'Score ' + l),
          colors: scoreLabels.map(l => scoreColors[l] || '#98a2b3'),
          legend: { position: 'bottom', fontSize: '13px' },
          dataLabels: { enabled: true, style: { fontSize: '13px', fontWeight: 600 } },
          plotOptions: { pie: { donut: { size: '55%' } } },
        });
        chart2.render();
      }
    }, 1500); // Wait for bundle.js to finish rendering
  },

  updateRecentOrdersTable(clients) {
    // Sort by ventes and take top 5
    const topClients = [...clients]
      .filter(c => c.x_ventes_total > 0)
      .sort((a, b) => (b.x_ventes_total || 0) - (a.x_ventes_total || 0))
      .slice(0, 5);

    // Find the "Recent Orders" table body
    const tables = document.querySelectorAll('table tbody');
    if (tables.length > 0) {
      const tbody = tables[tables.length - 1]; // Last table is Recent Orders
      tbody.innerHTML = topClients.map(c => `
        <tr class="border-b border-gray-100 dark:border-gray-800">
          <td class="px-5 py-4 sm:px-6">
            <div class="flex items-center gap-3">
              <div>
                <p class="font-medium text-gray-800 text-theme-sm dark:text-white/90">${c.name || '—'}</p>
                <span class="text-gray-500 text-theme-xs">${c.email || ''}</span>
              </div>
            </div>
          </td>
          <td class="px-5 py-4 sm:px-6 text-gray-500 text-theme-sm dark:text-gray-400">${c.territoire || '—'}</td>
          <td class="px-5 py-4 sm:px-6 text-gray-500 text-theme-sm dark:text-gray-400">${GMC.formatMoney(c.x_ventes_total)}</td>
          <td class="px-5 py-4 sm:px-6">
            <span class="inline-flex rounded-full px-2 py-0.5 text-theme-xs font-medium
              ${(c.x_score_client || '').toUpperCase() === 'A' ? 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-500' :
                (c.x_score_client || '').toUpperCase() === 'B' ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400' :
                'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'}">
              Score ${c.x_score_client || '—'}
            </span>
          </td>
        </tr>
      `).join('');
    }

    // Update table headers
    const theads = document.querySelectorAll('table thead');
    if (theads.length > 0) {
      const thead = theads[theads.length - 1];
      const ths = thead.querySelectorAll('th');
      const labels = ['Client', 'Territoire', 'Ventes totales', 'Score'];
      ths.forEach((th, i) => {
        if (labels[i]) th.textContent = labels[i];
      });
    }

    // Update section title
    const sectionTitles = document.querySelectorAll('h4');
    sectionTitles.forEach(h4 => {
      if (h4.textContent.includes('Recent Orders')) h4.textContent = 'Top Clients';
    });
  },

  updateDemographicSection(clients) {
    // Update "Customers Demographic" title
    const demoTitle = document.querySelector('h4');
    // Find the demographic section and update it
    const allH4 = document.querySelectorAll('h4');
    allH4.forEach(h4 => {
      if (h4.textContent.includes('Demographic')) {
        h4.textContent = 'Répartition par territoire';
      }
    });

    // Update subtitle
    const allSpans = document.querySelectorAll('span');
    allSpans.forEach(span => {
      if (span.textContent.includes('Number of customer based on country')) {
        span.textContent = 'Nombre de clients par territoire';
      }
    });
  },

  // ── Clients Table (basic-tables.html) ───────────────────────
  async initClientsTable() {
    try {
      const res = await fetch(`${GMC_API}/api/crm/clients`);
      const data = await res.json();
      const clients = data.clients || [];

      // Find the first table
      const table = document.querySelector('table');
      if (!table) return;

      // Update thead
      const thead = table.querySelector('thead');
      if (thead) {
        thead.innerHTML = `
          <tr>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Client</th>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Territoire</th>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Score</th>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Ville</th>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Téléphone</th>
            <th class="px-5 py-3 font-medium text-gray-500 text-start text-theme-xs dark:text-gray-400">Type</th>
          </tr>`;
      }

      // Update tbody
      const tbody = table.querySelector('tbody');
      if (tbody) {
        tbody.innerHTML = clients.map(c => `
          <tr class="border-b border-gray-100 dark:border-gray-800">
            <td class="px-5 py-4">
              <a href="/app/crm/client?id=${c.id}" class="flex items-center gap-3">
                <div>
                  <p class="font-medium text-gray-800 text-theme-sm dark:text-white/90">${c.name || '—'}</p>
                  <span class="text-gray-500 text-theme-xs">${c.email || ''}</span>
                </div>
              </a>
            </td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.territoire || '—'}</td>
            <td class="px-5 py-4">
              <span class="inline-flex rounded-full px-2 py-0.5 text-theme-xs font-medium
                ${(c.x_score_client || '').toUpperCase() === 'A' ? 'bg-success-50 text-success-700 dark:bg-success-500/15 dark:text-success-500' :
                  (c.x_score_client || '').toUpperCase() === 'B' ? 'bg-blue-50 text-blue-700 dark:bg-blue-500/15 dark:text-blue-400' :
                  (c.x_score_client || '').toUpperCase() === 'C' ? 'bg-warning-50 text-warning-700 dark:bg-warning-500/15 dark:text-warning-500' :
                  'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'}">
                ${c.x_score_client || '—'}
              </span>
            </td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.city || '—'}</td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.phone || '—'}</td>
            <td class="px-5 py-4 text-gray-500 text-theme-sm dark:text-gray-400">${c.x_type_client || '—'}</td>
          </tr>
        `).join('');
      }

      // Update page title
      document.querySelectorAll('h2, h3, nav').forEach(el => {
        if (el.textContent.includes('Basic')) el.textContent = el.textContent.replace('Basic', 'Liste des');
      });

    } catch (err) {
      console.error('GMC Clients Table init error:', err);
    }
  },

  // ── Client Profile (profile.html) ──────────────────────────
  async initClientProfile() {
    const params = new URLSearchParams(window.location.search);
    const clientId = params.get('id');
    if (!clientId) return;

    try {
      const res = await fetch(`${GMC_API}/api/crm/client/${clientId}`);
      const client = await res.json();

      // Update profile name
      const nameEl = document.querySelector('h3.text-title-sm, h4.text-title-sm');
      if (nameEl) nameEl.textContent = client.name || '—';

      // Update subtitle/role
      const roleEls = document.querySelectorAll('.text-sm.text-gray-500');
      roleEls.forEach(el => {
        if (el.closest('.flex.flex-col.items-center') || el.closest('.profile-header')) {
          el.textContent = [client.x_type_client, client.territoire].filter(Boolean).join(' — ') || 'Client';
        }
      });

      // Update info cards
      const metaItems = document.querySelectorAll('.text-theme-sm');
      metaItems.forEach(el => {
        const text = el.textContent.trim();
        // Replace placeholder social links / info with client data
      });

      // Build client info section
      const profileContent = document.querySelector('.grid.grid-cols-1, .profile-content, main .p-5');
      if (profileContent) {
        // Add client details after existing profile header
        const detailsDiv = document.createElement('div');
        detailsDiv.className = 'rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.03] md:p-6 mt-6';
        detailsDiv.innerHTML = `
          <h4 class="text-lg font-semibold text-gray-800 dark:text-white/90 mb-4">Informations du client</h4>
          <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div><span class="text-sm text-gray-500">Email</span><p class="font-medium text-gray-800 dark:text-white/90">${client.email || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Téléphone</span><p class="font-medium text-gray-800 dark:text-white/90">${client.phone || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Ville</span><p class="font-medium text-gray-800 dark:text-white/90">${client.city || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Territoire</span><p class="font-medium text-gray-800 dark:text-white/90">${client.territoire || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Score</span><p class="font-medium text-gray-800 dark:text-white/90">${client.x_score_client || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Type</span><p class="font-medium text-gray-800 dark:text-white/90">${client.x_type_client || '—'}</p></div>
            <div><span class="text-sm text-gray-500">Ventes totales</span><p class="font-medium text-gray-800 dark:text-white/90">${GMC.formatMoney(client.x_ventes_total)}</p></div>
            <div><span class="text-sm text-gray-500">Heures ouverture</span><p class="font-medium text-gray-800 dark:text-white/90">${client.x_hours || '—'}</p></div>
          </div>
          ${client.x_competiteurs ? `<div class="mt-4"><span class="text-sm text-gray-500">Compétiteurs</span><p class="font-medium text-gray-800 dark:text-white/90">${client.x_competiteurs}</p></div>` : ''}
          ${client.x_notes_ia ? `<div class="mt-4"><span class="text-sm text-gray-500">Notes IA</span><p class="text-gray-600 dark:text-gray-300 text-sm whitespace-pre-line">${client.x_notes_ia}</p></div>` : ''}
        `;
        // Insert after first child of main content
        const mainContent = document.querySelector('main .mx-auto');
        if (mainContent) mainContent.appendChild(detailsDiv);
      }

    } catch (err) {
      console.error('GMC Client Profile init error:', err);
    }
  }
};

// ── Auto-detect page and initialize ──────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;
  if (path.includes('/app/crm/clients')) {
    GMC.initClientsTable();
  } else if (path.includes('/app/crm/client') && !path.includes('clients')) {
    GMC.initClientProfile();
  } else if (path === '/app/crm' || path === '/app/crm/') {
    GMC.initDashboard();
  }
});
