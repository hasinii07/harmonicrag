/**
 * HarmonicRAG — Automated Evaluation Dashboard Controller
 * Runs six-category benchmark suite, displays genuine metrics, and category filtering.
 */

class EvaluationController {
    constructor() {
        this.btnRun = document.getElementById("btn-run-evaluation");
        this.btnLabel = document.getElementById("eval-btn-label");
        this.tableBody = document.getElementById("evaluation-table-body");
        this.filterTabs = document.querySelectorAll(".filter-tab");
        this.currentCategory = "ALL";
        this.currentReport = null;

        this.init();
    }

    init() {
        if (this.btnRun) {
            this.btnRun.addEventListener("click", () => this.runSuite());
        }

        this.filterTabs.forEach(tab => {
            tab.addEventListener("click", () => {
                this.filterTabs.forEach(t => t.classList.remove("active"));
                tab.classList.add("active");
                this.currentCategory = tab.dataset.category;
                this.renderTable();
            });
        });

        this.loadLatestResults();
    }

    async loadLatestResults() {
        try {
            const resp = await fetch("/api/evaluation/results");
            if (!resp.ok) return;
            const data = await resp.json();
            this.currentReport = data;
            this.renderMetrics(data);
            this.renderTable();
        } catch (err) {
            console.log("No previous evaluation results found.");
        }
    }

    async runSuite() {
        if (this.btnRun) this.btnRun.disabled = true;
        if (this.btnLabel) this.btnLabel.textContent = "Executing 12 Benchmark Tests...";

        try {
            const resp = await fetch("/api/evaluation/run", { method: "POST" });
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || "Evaluation execution failed");
            }

            const data = await resp.json();
            this.currentReport = data;
            this.renderMetrics(data);
            this.renderTable();
        } catch (err) {
            alert(`Evaluation Suite Error: ${err.message}`);
        } finally {
            if (this.btnRun) this.btnRun.disabled = false;
            if (this.btnLabel) this.btnLabel.textContent = "Run Benchmark Suite";
        }
    }

    renderMetrics(report) {
        document.getElementById("eval-pass-rate").textContent = `${report.pass_rate_pct}%`;
        document.getElementById("eval-pass-counts").textContent = `${report.passed_tests} / ${report.total_tests} passed`;
        document.getElementById("eval-retrieval-rate").textContent = `${report.retrieval_success_rate_pct}%`;
        document.getElementById("eval-citation-prec").textContent = `${report.citation_precision_pct}%`;
        document.getElementById("eval-citation-cov").textContent = `${report.citation_coverage_pct}%`;
        document.getElementById("eval-abstain-rate").textContent = `${report.abstention_performance_pct}%`;
        document.getElementById("eval-avg-latency").textContent = `${report.avg_latency_ms} ms`;
    }

    renderTable() {
        if (!this.tableBody || !this.currentReport) return;
        this.tableBody.innerHTML = "";

        let cases = this.currentReport.cases || [];
        if (this.currentCategory !== "ALL") {
            cases = cases.filter(c => c.category === this.currentCategory);
        }

        if (cases.length === 0) {
            this.tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No test cases match filter.</td></tr>`;
            return;
        }

        cases.forEach(c => {
            const tr = document.createElement("tr");
            const isPass = c.status === "pass";
            const pillClass = isPass ? "pill-pass" : "pill-fail";
            const statusLabel = isPass ? "PASS" : "FAIL";
            const latency = Math.round(c.retrieval_latency_ms + c.generation_latency_ms);

            const citStr = c.citations && c.citations.length 
                ? c.citations.map(cit => `<span style="display:block; font-size:0.75rem; color:var(--text-secondary);">${this.escapeHTML(cit)}</span>`).join("")
                : '<span style="color:var(--text-muted); font-size:0.75rem;">None</span>';

            tr.innerHTML = `
                <td><span class="status-pill ${pillClass}">${statusLabel}</span></td>
                <td><code>${c.test_id}</code></td>
                <td><strong style="color:var(--accent-gold);">${c.category}</strong>: ${c.category_name}</td>
                <td>
                    <div style="font-weight:600; color:var(--text-primary);">${this.escapeHTML(c.question)}</div>
                    ${c.failure_reason ? `<div style="color:var(--status-error); font-size:0.78rem; margin-top:4px;">❌ ${this.escapeHTML(c.failure_reason)}</div>` : ''}
                </td>
                <td><code style="font-size:0.75rem;">${this.escapeHTML(c.criteria)}</code></td>
                <td>${citStr}</td>
                <td>${latency} ms</td>
            `;

            this.tableBody.appendChild(tr);
        });
    }

    escapeHTML(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
}

window.evaluationController = new EvaluationController();
