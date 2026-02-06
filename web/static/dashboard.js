/* Buffet Shao — Interactive Dashboard */

const DARK_LAYOUT = {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: '#e5e7eb', size: 12 },
    margin: { l: 40, r: 20, t: 30, b: 30 },
    xaxis: { gridcolor: '#1f2937', zerolinecolor: '#374151' },
    yaxis: { gridcolor: '#1f2937', zerolinecolor: '#374151' },
};

const PLOTLY_CONFIG = {
    displayModeBar: false,
    responsive: true,
};

/* ── Comparison Chart ── */
function renderComparisonChart(quotes) {
    if (!quotes || quotes.length === 0) return;

    const symbols = quotes.map(q => q.symbol);
    const changes = quotes.map(q => q.change_pct || 0);
    const colors = changes.map(c => c >= 0 ? '#00C853' : '#FF1744');

    const data = [{
        type: 'bar',
        x: symbols,
        y: changes,
        marker: { color: colors },
        text: changes.map(c => (c >= 0 ? '+' : '') + c.toFixed(2) + '%'),
        textposition: 'auto',
        textfont: { color: '#e5e7eb', size: 11 },
    }];

    const layout = {
        ...DARK_LAYOUT,
        yaxis: { ...DARK_LAYOUT.yaxis, title: 'Change %' },
    };

    Plotly.newPlot('comparison-chart', data, layout, PLOTLY_CONFIG);
}

/* ── Sector Chart ── */
async function renderSectorChart() {
    try {
        const resp = await fetch('/api/sectors');
        const sectors = await resp.json();
        if (!sectors || sectors.length === 0) return;

        const names = sectors.map(s => s.sector || s.name || 'Unknown');
        const changes = sectors.map(s => {
            let c = s.changesPercentage || 0;
            if (typeof c === 'string') c = parseFloat(c.replace('%', ''));
            return c;
        });
        const colors = changes.map(c => c >= 0 ? '#00C853' : '#FF1744');

        const data = [{
            type: 'bar',
            x: names,
            y: changes,
            marker: { color: colors },
            text: changes.map(c => (c >= 0 ? '+' : '') + c.toFixed(2) + '%'),
            textposition: 'auto',
            textfont: { color: '#e5e7eb', size: 10 },
        }];

        const layout = {
            ...DARK_LAYOUT,
            xaxis: { ...DARK_LAYOUT.xaxis, tickangle: -30, tickfont: { size: 10 } },
            yaxis: { ...DARK_LAYOUT.yaxis, title: 'Change %' },
        };

        Plotly.newPlot('sector-chart', data, layout, PLOTLY_CONFIG);
    } catch (e) {
        console.error('Sector chart error:', e);
    }
}

/* ── News Feed ── */
async function renderNewsFeed() {
    try {
        const resp = await fetch('/api/news');
        const articles = await resp.json();
        const container = document.getElementById('news-feed');

        if (!articles || articles.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-sm">No recent news.</p>';
            return;
        }

        container.innerHTML = articles.slice(0, 8).map(a => {
            const sentiment = a.sentiment;
            let sentimentBadge = '';
            if (sentiment !== null && sentiment !== undefined) {
                const cls = sentiment > 0.2 ? 'text-bull' : sentiment < -0.2 ? 'text-bear' : 'text-gray-400';
                const label = sentiment > 0.2 ? 'Bullish' : sentiment < -0.2 ? 'Bearish' : 'Neutral';
                sentimentBadge = `<span class="${cls} text-xs">${label}</span>`;
            }

            const url = a.url ? `<a href="${a.url}" target="_blank" class="text-brand text-xs hover:underline">Read</a>` : '';

            return `
                <div class="flex items-start gap-3 p-3 bg-gray-800 rounded-lg">
                    <div class="flex-1 min-w-0">
                        <div class="text-sm font-medium truncate">${a.title || 'Untitled'}</div>
                        <div class="text-gray-500 text-xs mt-1 line-clamp-2">${a.description || a.snippet || ''}</div>
                        <div class="flex items-center gap-3 mt-2">
                            <span class="text-gray-600 text-xs">${a.source || ''}</span>
                            ${sentimentBadge}
                            ${url}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('News feed error:', e);
    }
}

/* ── Watchlist Refresh ── */
async function refreshWatchlist() {
    try {
        const resp = await fetch('/api/quotes');
        const quotes = await resp.json();
        renderComparisonChart(quotes);

        const grid = document.getElementById('watchlist-grid');
        grid.innerHTML = quotes.map(q => {
            const changeClass = q.change_pct >= 0 ? 'text-bull' : 'text-bear';
            const sign = q.change_pct >= 0 ? '+' : '';
            return `
                <div class="bg-gray-800 rounded-lg p-3 text-center">
                    <div class="font-semibold text-sm">${q.symbol}</div>
                    <div class="text-lg font-mono">$${(q.price || 0).toFixed(2)}</div>
                    <div class="${changeClass} text-sm font-mono">${sign}${(q.change_pct || 0).toFixed(2)}%</div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Watchlist refresh error:', e);
    }
}

/* ── Refresh All ── */
async function refreshAll() {
    await Promise.all([
        refreshWatchlist(),
        renderSectorChart(),
        renderNewsFeed(),
    ]);
    document.getElementById('last-update').textContent =
        'Updated ' + new Date().toLocaleTimeString();
}

/* ── Init ── */
document.addEventListener('DOMContentLoaded', () => {
    renderComparisonChart(quotesData);
    renderSectorChart();
    renderNewsFeed();
    document.getElementById('last-update').textContent =
        'Updated ' + new Date().toLocaleTimeString();

    // Auto-refresh every 60 seconds
    setInterval(refreshAll, 60000);
});
