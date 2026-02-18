(function () {
    'use strict';

    var currentRange = '30d';

    function init() {
        var rangeSelect = document.getElementById('time-range');
        if (rangeSelect) {
            rangeSelect.addEventListener('change', function () {
                currentRange = rangeSelect.value;
                loadAnalytics();
            });
        }

        var exportBtn = document.getElementById('export-btn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportCSV);
        }

        loadAnalytics();
    }

    function loadAnalytics() {
        fetch('/dashboard/analytics-data?range=' + currentRange)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                renderKPIs(data.kpis);
                renderBarChart(data.candidates_over_time);
                renderDepartments(data.by_department);
                renderFunnel(data.funnel);
                renderSkills(data.top_skills);
                renderHires(data.recent_hires);
            })
            .catch(function (err) {
                console.error('[Analytics] Failed to load data:', err);
            });
    }

    // ── KPI Cards ──────────────────────────────────────────────────────────────
    function renderKPIs(kpis) {
        setText('kpi-total', kpis.total_candidates);
        setText('kpi-avg-score', kpis.avg_match_score > 0 ? kpis.avg_match_score + '%' : '—');
        setText('kpi-shortlisted', kpis.shortlisted_count);
        setText('kpi-hired', kpis.hired_count);

        var rangeLabel = { '7d': 'last 7 days', '30d': 'last 30 days', '90d': 'last 90 days' }[currentRange] || 'selected period';
        setText('kpi-total-sub', 'in ' + rangeLabel);
        setText('kpi-avg-sub', 'across scored candidates');
        setText('kpi-shortlisted-sub', 'invited or above');
        setText('kpi-hired-sub', 'marked as hired');
    }

    // ── Bar Chart (Candidates Over Time) ──────────────────────────────────────
    function renderBarChart(data) {
        var wrap = document.getElementById('app-chart');
        var empty = document.getElementById('app-chart-empty');

        // Remove old SVG/canvas if any
        var old = wrap.querySelector('svg');
        if (old) old.remove();

        var nonZero = data.filter(function (d) { return d.count > 0; });
        if (!data.length || !nonZero.length) {
            if (empty) empty.style.display = '';
            return;
        }
        if (empty) empty.style.display = 'none';

        var maxCount = Math.max.apply(null, data.map(function (d) { return d.count; })) || 1;
        var barW = 28;
        var gap = 10;
        var chartH = 140;
        var labelH = 28;
        var totalW = data.length * (barW + gap) - gap;
        var svgH = chartH + labelH;

        var svgNS = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(svgNS, 'svg');
        svg.setAttribute('viewBox', '0 0 ' + totalW + ' ' + svgH);
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', svgH);
        svg.style.overflow = 'visible';

        data.forEach(function (d, i) {
            var x = i * (barW + gap);
            var barH = Math.max(3, Math.round((d.count / maxCount) * chartH));
            var y = chartH - barH;

            // Bar
            var rect = document.createElementNS(svgNS, 'rect');
            rect.setAttribute('x', x);
            rect.setAttribute('y', y);
            rect.setAttribute('width', barW);
            rect.setAttribute('height', barH);
            rect.setAttribute('rx', 4);
            rect.setAttribute('fill', d.count > 0 ? 'var(--color-primary)' : 'var(--color-elevated)');
            rect.setAttribute('opacity', d.count > 0 ? '0.85' : '0.3');
            svg.appendChild(rect);

            // Count label above bar (only if > 0)
            if (d.count > 0) {
                var countTxt = document.createElementNS(svgNS, 'text');
                countTxt.setAttribute('x', x + barW / 2);
                countTxt.setAttribute('y', y - 4);
                countTxt.setAttribute('text-anchor', 'middle');
                countTxt.setAttribute('font-size', '10');
                countTxt.setAttribute('fill', 'var(--color-text-low)');
                countTxt.textContent = d.count;
                svg.appendChild(countTxt);
            }

            // X-axis label
            var txt = document.createElementNS(svgNS, 'text');
            txt.setAttribute('x', x + barW / 2);
            txt.setAttribute('y', chartH + 18);
            txt.setAttribute('text-anchor', 'middle');
            txt.setAttribute('font-size', '10');
            txt.setAttribute('fill', 'var(--color-text-disabled)');
            txt.textContent = d.label;
            svg.appendChild(txt);
        });

        wrap.appendChild(svg);
    }

    // ── Department Breakdown ───────────────────────────────────────────────────
    function renderDepartments(data) {
        var container = document.getElementById('dept-breakdown');
        var empty = document.getElementById('dept-empty');

        // Clear previous rows (keep empty placeholder)
        Array.from(container.children).forEach(function (el) {
            if (el !== empty) el.remove();
        });

        if (!data || !data.length) {
            if (empty) empty.style.display = '';
            return;
        }
        if (empty) empty.style.display = 'none';

        var maxCount = data[0].count || 1;

        data.forEach(function (d) {
            var pct = Math.round((d.count / maxCount) * 100);
            var row = document.createElement('div');
            row.className = 'analytics-hbar-row';
            row.innerHTML =
                '<div class="analytics-hbar-label">' + escHtml(d.dept) + '</div>' +
                '<div class="analytics-hbar-track">' +
                '<div class="analytics-hbar-fill" style="width:' + pct + '%"></div>' +
                '</div>' +
                '<span class="analytics-hbar-count">' + d.count + '</span>';
            container.appendChild(row);
        });
    }

    // ── Hiring Funnel ─────────────────────────────────────────────────────────
    function renderFunnel(funnel) {
        var container = document.getElementById('funnel-chart');
        var empty = document.getElementById('funnel-empty');

        Array.from(container.children).forEach(function (el) {
            if (el !== empty) el.remove();
        });

        if (!funnel || funnel.total === 0) {
            if (empty) empty.style.display = '';
            return;
        }
        if (empty) empty.style.display = 'none';

        var steps = [
            { label: 'Applied', count: funnel.total, color: 'var(--color-primary)' },
            { label: 'AI Scored', count: funnel.scored, color: '#3b82f6' },
            { label: 'Shortlisted', count: funnel.shortlisted, color: 'var(--color-warning)' },
            { label: 'Invited', count: funnel.invited, color: '#a855f7' },
            { label: 'Hired', count: funnel.hired, color: 'var(--color-success)' },
        ];

        var maxCount = funnel.total || 1;

        steps.forEach(function (step) {
            var pct = Math.round((step.count / maxCount) * 100);
            var row = document.createElement('div');
            row.className = 'analytics-funnel-row';
            row.innerHTML =
                '<div class="analytics-funnel-label">' + escHtml(step.label) + '</div>' +
                '<div class="analytics-funnel-track">' +
                '<div class="analytics-funnel-fill" style="width:' + pct + '%;background:' + step.color + '"></div>' +
                '</div>' +
                '<span class="analytics-funnel-count">' + step.count + '</span>';
            container.appendChild(row);
        });
    }

    // ── Top Skills ────────────────────────────────────────────────────────────
    function renderSkills(skills) {
        var container = document.getElementById('skills-demand');
        var empty = document.getElementById('skills-empty');

        Array.from(container.children).forEach(function (el) {
            if (el !== empty) el.remove();
        });

        if (!skills || !skills.length) {
            if (empty) empty.style.display = '';
            return;
        }
        if (empty) empty.style.display = 'none';

        var maxCount = skills[0].count || 1;

        skills.forEach(function (s) {
            var intensity = Math.max(0.35, s.count / maxCount);
            var pill = document.createElement('span');
            pill.className = 'analytics-skill-pill';
            pill.style.opacity = intensity;
            pill.innerHTML = escHtml(s.skill) + ' <span class="analytics-skill-count">' + s.count + '</span>';
            container.appendChild(pill);
        });
    }

    // ── Recent Hires Table ────────────────────────────────────────────────────
    function renderHires(hires) {
        var tbody = document.getElementById('hires-tbody');
        var emptyRow = document.getElementById('hires-empty-row');

        // Clear non-empty rows
        Array.from(tbody.querySelectorAll('tr:not(#hires-empty-row)')).forEach(function (r) { r.remove(); });

        if (!hires || !hires.length) {
            if (emptyRow) emptyRow.style.display = '';
            return;
        }
        if (emptyRow) emptyRow.style.display = 'none';

        hires.forEach(function (h) {
            var scoreClass = h.match_score >= 90 ? 'green' : h.match_score >= 70 ? 'amber' : 'red';
            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' + escHtml(h.name) + '</td>' +
                '<td>' + escHtml(h.job_title) + '</td>' +
                '<td>' + escHtml(h.dept || '—') + '</td>' +
                '<td><span class="result-score ' + scoreClass + '" style="font-size:0.8rem;padding:2px 8px;">' + h.match_score + '</span></td>' +
                '<td>' + escHtml(h.hired_on) + '</td>';
            tbody.appendChild(tr);
        });
    }

    // ── Export CSV ────────────────────────────────────────────────────────────
    function exportCSV() {
        fetch('/dashboard/analytics-data?range=' + currentRange)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                var rows = [['Section', 'Label', 'Value']];

                rows.push(['KPI', 'Total Candidates', data.kpis.total_candidates]);
                rows.push(['KPI', 'Avg Match Score', data.kpis.avg_match_score + '%']);
                rows.push(['KPI', 'Shortlisted', data.kpis.shortlisted_count]);
                rows.push(['KPI', 'Hired', data.kpis.hired_count]);

                data.candidates_over_time.forEach(function (d) {
                    rows.push(['Over Time', d.label, d.count]);
                });

                data.by_department.forEach(function (d) {
                    rows.push(['By Department', d.dept, d.count]);
                });

                rows.push(['Funnel', 'Applied', data.funnel.total]);
                rows.push(['Funnel', 'AI Scored', data.funnel.scored]);
                rows.push(['Funnel', 'Shortlisted', data.funnel.shortlisted]);
                rows.push(['Funnel', 'Invited', data.funnel.invited]);
                rows.push(['Funnel', 'Hired', data.funnel.hired]);

                data.top_skills.forEach(function (s) {
                    rows.push(['Top Skills', s.skill, s.count]);
                });

                var csv = rows.map(function (r) {
                    return r.map(function (cell) {
                        return '"' + String(cell).replace(/"/g, '""') + '"';
                    }).join(',');
                }).join('\n');

                var blob = new Blob([csv], { type: 'text/csv' });
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'quickhire-analytics-' + currentRange + '.csv';
                a.click();
                URL.revokeObjectURL(url);
            });
    }

    // ── Helpers ───────────────────────────────────────────────────────────────
    function setText(id, val) {
        var el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    function escHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
