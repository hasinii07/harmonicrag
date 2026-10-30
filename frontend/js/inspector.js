/**
 * HarmonicRAG — RAG Pipeline Inspector
 * Visualizes dense scores, lexical BM25 scores, RRF calculations, and latencies.
 */

class PipelineInspector {
    constructor() {
        this.modal = document.getElementById("inspector-modal");
        this.btnClose = document.getElementById("btn-close-inspector");

        if (this.btnClose) {
            this.btnClose.addEventListener("click", () => this.close());
        }
        if (this.modal) {
            this.modal.addEventListener("click", (e) => {
                if (e.target === this.modal) this.close();
            });
        }
    }

    open(trace, query) {
        if (!this.modal || !trace) return;

        // Populate query
        document.getElementById("insp-query").textContent = query || trace.query || "N/A";
        document.getElementById("insp-tokens").textContent = trace.preprocessed_query || "--";

        // Latencies
        const lat = trace.latencies_ms || {};
        document.getElementById("insp-time-dense").textContent = `${lat.dense_ms || 0} ms`;
        document.getElementById("insp-count-dense").textContent = `${trace.dense_count || 0} results`;

        document.getElementById("insp-time-lex").textContent = `${lat.lexical_ms || 0} ms`;
        document.getElementById("insp-count-lex").textContent = `${trace.lexical_count || 0} results`;

        document.getElementById("insp-time-fuse").textContent = `${lat.fusion_ms || 0} ms`;
        document.getElementById("insp-count-fuse").textContent = `Top ${trace.fused_count || 0} selected`;

        document.getElementById("insp-time-gen").textContent = `${lat.generation_ms || 0} ms`;
        document.getElementById("insp-time-total").textContent = `${lat.total_ms || lat.total_retrieval_ms || 0} ms`;

        // Fused results table
        const tbody = document.getElementById("insp-fused-tbody");
        tbody.innerHTML = "";

        const fusedList = trace.fused_results || [];
        if (fusedList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center py-3">No matching chunks passed the relevance threshold.</td></tr>`;
        } else {
            fusedList.forEach(item => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>#${item.final_rank}</strong></td>
                    <td><code>${this.escapeHTML(item.chunk_id)}</code></td>
                    <td>${this.escapeHTML(item.document_title)}</td>
                    <td>${item.page_number ? `p. ${item.page_number}` : 'N/A'}</td>
                    <td>${item.dense_rank ? `#${item.dense_rank}` : '--'}</td>
                    <td>${item.dense_score !== null && item.dense_score !== undefined ? item.dense_score.toFixed(4) : '--'}</td>
                    <td>${item.lexical_rank ? `#${item.lexical_rank}` : '--'}</td>
                    <td>${item.lexical_score !== null && item.lexical_score !== undefined ? item.lexical_score.toFixed(4) : '--'}</td>
                    <td><strong class="text-accent">${(item.rrf_score || 0).toFixed(6)}</strong></td>
                `;
                tbody.appendChild(tr);
            });
        }

        // Citation Validation Box
        const citBox = document.getElementById("insp-citation-summary");
        const cVal = trace.citation_validation || {};
        const isSuff = trace.is_evidence_sufficient;

        citBox.innerHTML = `
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span>Evidence Sufficiency Status: 
                    <strong style="color: ${isSuff ? 'var(--status-success)' : 'var(--status-error)'}">
                        ${isSuff ? '✓ SUFFICIENT EVIDENCE FOUND' : '✗ INSUFFICIENT EVIDENCE (HONEST ABSTENTION)'}
                    </strong>
                </span>
                <span>Verified Precision: <strong>${Math.round((cVal.precision || 1.0) * 100)}%</strong></span>
            </div>
            <div style="color:var(--text-secondary); font-size:0.84rem;">
                Verified Citations: <strong>${cVal.verified_count || 0}</strong> • 
                Rejected Hallucinations: <strong>${cVal.rejected_count || 0}</strong>
            </div>
        `;

        this.modal.classList.remove("hidden");
    }

    close() {
        if (this.modal) this.modal.classList.add("hidden");
    }

    escapeHTML(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#x27;");
    }
}

window.pipelineInspector = new PipelineInspector();
