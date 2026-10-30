/**
 * HarmonicRAG — Documents & Knowledge Base Controller
 * Manages document listing, uploads (PDF, MD, TXT), text notes ingestion, and deletion.
 */

class DocumentManager {
    constructor() {
        this.tableBody = document.getElementById("documents-table-body");
        this.fileInput = document.getElementById("file-upload-input");
        this.btnTriggerUpload = document.getElementById("btn-trigger-upload");
        this.btnRefresh = document.getElementById("btn-refresh-docs");
        this.dropzone = document.getElementById("dropzone");
        this.ingestAlert = document.getElementById("ingest-alert");

        // Paste Modal
        this.pasteModal = document.getElementById("paste-modal");
        this.btnOpenPaste = document.getElementById("btn-open-paste-modal");
        this.btnClosePaste = document.getElementById("btn-close-paste");
        this.btnCancelPaste = document.getElementById("btn-cancel-paste");
        this.pasteForm = document.getElementById("paste-form");

        this.init();
    }

    init() {
        if (this.btnRefresh) {
            this.btnRefresh.addEventListener("click", () => this.loadDocuments());
        }

        if (this.btnTriggerUpload && this.fileInput) {
            this.btnTriggerUpload.addEventListener("click", () => this.fileInput.click());
            this.fileInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.uploadFile(e.target.files[0]);
                }
            });
        }

        // Drag & Drop
        if (this.dropzone) {
            this.dropzone.addEventListener("click", () => this.fileInput.click());
            this.dropzone.addEventListener("dragover", (e) => {
                e.preventDefault();
                this.dropzone.classList.add("dragover");
            });
            this.dropzone.addEventListener("dragleave", () => {
                this.dropzone.classList.remove("dragover");
            });
            this.dropzone.addEventListener("drop", (e) => {
                e.preventDefault();
                this.dropzone.classList.remove("dragover");
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    this.uploadFile(e.dataTransfer.files[0]);
                }
            });
        }

        // Paste Modal Events
        if (this.btnOpenPaste && this.pasteModal) {
            this.btnOpenPaste.addEventListener("click", () => {
                this.pasteModal.classList.remove("hidden");
            });
        }
        if (this.btnClosePaste && this.pasteModal) {
            this.btnClosePaste.addEventListener("click", () => {
                this.pasteModal.classList.add("hidden");
            });
        }
        if (this.btnCancelPaste && this.pasteModal) {
            this.btnCancelPaste.addEventListener("click", () => {
                this.pasteModal.classList.add("hidden");
            });
        }

        if (this.pasteForm) {
            this.pasteForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.submitPastedText();
            });
        }

        this.loadDocuments();
    }

    async loadDocuments() {
        try {
            const resp = await fetch("/api/documents");
            if (!resp.ok) throw new Error("Failed to load documents");
            const data = await resp.json();

            // Update stats
            document.getElementById("stat-doc-count").textContent = data.total_count;
            document.getElementById("stat-chunk-count").textContent = data.total_chunks;
            const badge = document.getElementById("badge-doc-count");
            if (badge) badge.textContent = data.total_count;

            this.renderTable(data.documents);
        } catch (err) {
            if (this.tableBody) {
                this.tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4" style="color:var(--status-error);">${err.message}</td></tr>`;
            }
        }
    }

    renderTable(docs) {
        if (!this.tableBody) return;
        this.tableBody.innerHTML = "";

        if (!docs || docs.length === 0) {
            this.tableBody.innerHTML = `<tr><td colspan="8" class="text-center py-4">No documents indexed yet. Upload a PDF or markdown treatise.</td></tr>`;
            return;
        }

        docs.forEach(doc => {
            const tr = document.createElement("tr");

            // Format pill
            let pillClass = "pill-md";
            if (doc.file_type === "pdf") pillClass = "pill-pdf";
            else if (doc.file_type === "notes") pillClass = "pill-notes";

            const dateStr = doc.created_at ? new Date(doc.created_at).toLocaleDateString() : "--";

            tr.innerHTML = `
                <td><strong>${this.escapeHTML(doc.title)}</strong><br><small style="color:var(--text-muted); font-family:var(--font-mono); font-size:0.75rem;">${doc.id}</small></td>
                <td>${this.escapeHTML(doc.author || 'Unknown')}</td>
                <td><span class="status-pill ${pillClass}">${doc.file_type.toUpperCase()}</span></td>
                <td>${doc.page_count || 1}</td>
                <td><strong>${doc.chunk_count}</strong></td>
                <td><span class="status-pill pill-pass">${doc.status}</span></td>
                <td>${dateStr}</td>
                <td>
                    <button class="btn btn-sm btn-outline btn-reindex" data-id="${doc.id}" title="Re-index document">Reindex</button>
                    <button class="btn btn-sm btn-outline btn-delete" data-id="${doc.id}" style="color:var(--status-error);" title="Delete document">Delete</button>
                </td>
            `;

            // Attach action listeners
            tr.querySelector(".btn-reindex").addEventListener("click", () => this.reindexDoc(doc.id));
            tr.querySelector(".btn-delete").addEventListener("click", () => this.deleteDoc(doc.id));

            this.tableBody.appendChild(tr);
        });
    }

    async uploadFile(file) {
        const formData = new FormData();
        formData.append("file", file);

        this.showAlert(`Ingesting ${file.name}... Extracting text, preserving pages, and generating embeddings.`, "info");

        try {
            const resp = await fetch("/api/documents/upload", {
                method: "POST",
                body: formData
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || "Upload failed");
            }

            const doc = await resp.json();
            this.showAlert(`Successfully ingested "${doc.title}" (${doc.chunk_count} chunks, ${doc.page_count} pages).`, "success");
            this.loadDocuments();
        } catch (err) {
            this.showAlert(`Failed to ingest document: ${err.message}`, "error");
        } finally {
            if (this.fileInput) this.fileInput.value = "";
        }
    }

    async submitPastedText() {
        const title = document.getElementById("paste-title").value.trim();
        const author = document.getElementById("paste-author").value.trim();
        const content = document.getElementById("paste-content").value.trim();

        if (!title || !content) return;

        this.showAlert(`Ingesting text notes "${title}"...`, "info");
        try {
            const resp = await fetch("/api/documents/text", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title, author, content })
            });

            if (!resp.ok) {
                const errData = await resp.json().catch(() => ({}));
                throw new Error(errData.detail || "Ingestion failed");
            }

            const doc = await resp.json();
            this.showAlert(`Notes ingested successfully: ${doc.title} (${doc.chunk_count} chunks).`, "success");
            this.pasteModal.classList.add("hidden");
            this.pasteForm.reset();
            this.loadDocuments();
        } catch (err) {
            this.showAlert(`Text ingestion error: ${err.message}`, "error");
        }
    }

    async deleteDoc(docId) {
        if (!confirm(`Are you sure you want to delete document ${docId} and purge all its indexed vectors?`)) return;

        try {
            const resp = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
            if (!resp.ok) throw new Error("Delete failed");
            this.showAlert(`Document ${docId} removed from knowledge base.`, "success");
            this.loadDocuments();
        } catch (err) {
            this.showAlert(`Delete failed: ${err.message}`, "error");
        }
    }

    async reindexDoc(docId) {
        try {
            const resp = await fetch(`/api/documents/${docId}/reindex`, { method: "POST" });
            if (!resp.ok) throw new Error("Re-index failed");
            this.showAlert(`Document ${docId} successfully re-indexed into ChromaDB and BM25.`, "success");
            this.loadDocuments();
        } catch (err) {
            this.showAlert(`Re-index error: ${err.message}`, "error");
        }
    }

    showAlert(message, type = "info") {
        if (!this.ingestAlert) return;
        this.ingestAlert.className = `ingest-alert ${type}`;
        this.ingestAlert.textContent = message;
        this.ingestAlert.classList.remove("hidden");
        setTimeout(() => {
            this.ingestAlert.classList.add("hidden");
        }, 5000);
    }

    escapeHTML(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
}

window.documentManager = new DocumentManager();
