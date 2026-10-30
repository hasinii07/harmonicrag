/**
 * HarmonicRAG — Chat Interface Controller
 * Orchestrates questions, streaming/fetch calls, citations, and visualizer events.
 */

class ChatController {
    constructor() {
        this.currentConversationId = null;
        this.messagesContainer = document.getElementById("messages-container");
        this.welcomeScreen = document.getElementById("welcome-screen");
        this.chatForm = document.getElementById("chat-form");
        this.chatInput = document.getElementById("chat-input");
        this.btnSend = document.getElementById("btn-send");
        this.btnNewChat = document.getElementById("btn-new-chat");

        // Drawer
        this.sourceDrawer = document.getElementById("source-drawer");
        this.btnCloseDrawer = document.getElementById("btn-close-source-drawer");

        this.init();
    }

    init() {
        if (this.chatForm) {
            this.chatForm.addEventListener("submit", (e) => {
                e.preventDefault();
                this.handleSendMessage();
            });
        }

        if (this.chatInput) {
            this.chatInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSendMessage();
                }
            });

            // Auto-resize textarea
            this.chatInput.addEventListener("input", () => {
                this.chatInput.style.height = "auto";
                this.chatInput.style.height = Math.min(this.chatInput.scrollHeight, 180) + "px";
            });
        }

        if (this.btnNewChat) {
            this.btnNewChat.addEventListener("click", () => this.startNewChat());
        }
        const mobileNewBtn = document.getElementById("btn-mobile-new");
        if (mobileNewBtn) {
            mobileNewBtn.addEventListener("click", () => this.startNewChat());
        }

        // Example Question Cards
        document.querySelectorAll(".example-card").forEach(card => {
            card.addEventListener("click", () => {
                const question = card.dataset.question;
                if (question) {
                    this.chatInput.value = question;
                    this.handleSendMessage();
                }
            });
        });

        // Close Source Drawer
        if (this.btnCloseDrawer && this.sourceDrawer) {
            this.btnCloseDrawer.addEventListener("click", () => {
                this.sourceDrawer.classList.add("hidden");
            });
            this.sourceDrawer.addEventListener("click", (e) => {
                if (e.target === this.sourceDrawer) {
                    this.sourceDrawer.classList.add("hidden");
                }
            });
        }
    }

    startNewChat() {
        this.currentConversationId = null;
        this.messagesContainer.innerHTML = "";
        this.welcomeScreen.style.display = "block";
        if (window.pianoSynth) {
            window.pianoSynth.closeVisualizer();
            window.pianoSynth.clearKeyHighlights(false);
            window.pianoSynth.currentVisualizerData = null;
            const label = document.getElementById("piano-label");
            if (label) {
                label.textContent = "No active chord selected";
            }
        }
        if (this.chatInput) {
            this.chatInput.value = "";
            this.chatInput.focus();
        }
    }

    async handleSendMessage() {
        const query = this.chatInput.value.trim();
        if (!query) return;

        // Hide welcome screen
        if (this.welcomeScreen) {
            this.welcomeScreen.style.display = "none";
        }

        // Render User Message
        this.appendUserMessage(query);
        this.chatInput.value = "";
        this.chatInput.style.height = "auto";

        // Render Loading Indicator
        const loadingId = this.appendLoadingIndicator();
        this.btnSend.disabled = true;

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: query,
                    conversation_id: this.currentConversationId,
                    include_trace: true
                })
            });

            this.removeMessage(loadingId);

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                throw new Error(errData.detail || `Server returned ${response.status}`);
            }

            const data = await response.json();
            this.currentConversationId = data.conversation_id;

            // Render Assistant Response
            this.appendAssistantMessage(data, query);

            // Refresh recent discussion list in sidebar
            if (window.app) {
                window.app.loadConversations();
            }

        } catch (err) {
            this.removeMessage(loadingId);
            this.appendErrorMessage(err.message || "Failed to communicate with HarmonicRAG backend.");
        } finally {
            this.btnSend.disabled = false;
            this.chatInput.focus();
        }
    }

    appendUserMessage(text) {
        const row = document.createElement("div");
        row.className = "message-row message-user";
        row.innerHTML = `
            <div class="message-bubble">
                <div class="message-text">${this.escapeHTML(text)}</div>
            </div>
        `;
        this.messagesContainer.appendChild(row);
        this.scrollToBottom();
    }

    appendAssistantMessage(data, originalQuery) {
        const row = document.createElement("div");
        row.className = "message-row message-assistant";

        // Misconception HTML
        let misconceptionHTML = "";
        if (data.misconception_correction) {
            misconceptionHTML = `
                <div class="misconception-card">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                    <div>${this.escapeHTML(data.misconception_correction)}</div>
                </div>
            `;
        }

        // Musical Example Box
        let exampleHTML = "";
        if (data.musical_example) {
            exampleHTML = `
                <div class="message-example-box">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;flex-shrink:0;"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
                    <span>${this.escapeHTML(data.musical_example)}</span>
                </div>
            `;
        }

        // Citations Chips
        let citationsHTML = "";
        if (data.citations && data.citations.length > 0) {
            const chips = data.citations.map((c, idx) => `
                <button class="citation-chip" data-idx="${idx}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
                    <span>${this.escapeHTML(c.document_title)}${c.page_number ? ` (p.${c.page_number})` : ''}</span>
                </button>
            `).join("");

            citationsHTML = `
                <div class="citations-container">
                    <span class="citation-label">Evidence Grounding:</span>
                    ${chips}
                </div>
            `;
        } else if (!data.is_evidence_sufficient) {
            citationsHTML = `
                <div class="citations-container" style="color:var(--text-muted); font-size:0.8rem;">
                    <em>No verified instructional citations were matched for this query.</em>
                </div>
            `;
        }

        // Action Buttons
        const hasVisualizer = !!data.visualizer;
        row.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
            </div>
            <div class="message-bubble">
                ${misconceptionHTML}
                <div class="message-direct-answer">${this.escapeHTML(data.direct_answer)}</div>
                <div class="message-explanation">${this.formatMarkdown(data.explanation)}</div>
                ${exampleHTML}
                ${citationsHTML}
                <div class="message-actions">
                    <button class="action-btn btn-copy" title="Copy answer">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        <span>Copy</span>
                    </button>
                    <button class="action-btn btn-inspect" title="Inspect retrieval pipeline">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        <span>Inspect RAG</span>
                    </button>
                    ${hasVisualizer ? `
                    <button class="action-btn action-btn-piano btn-show-piano" title="View musical example on visualizer">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"></rect><path d="M6 4v8M10 4v8M14 4v8M18 4v8"></path></svg>
                        <span>View musical example</span>
                    </button>` : ''}
                </div>
            </div>
        `;

        // Attach event handlers
        const copyBtn = row.querySelector(".btn-copy");
        copyBtn.addEventListener("click", () => {
            const fullText = `${data.direct_answer}\n\n${data.explanation}`;
            navigator.clipboard.writeText(fullText);
            copyBtn.innerHTML = `<span>Copied!</span>`;
            setTimeout(() => {
                copyBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg><span>Copy</span>`;
            }, 1800);
        });

        const inspectBtn = row.querySelector(".btn-inspect");
        inspectBtn.addEventListener("click", () => {
            if (window.pipelineInspector) {
                window.pipelineInspector.open(data.retrieval_trace, originalQuery);
            }
        });

        const pianoBtn = row.querySelector(".btn-show-piano");
        if (pianoBtn && data.visualizer) {
            pianoBtn.addEventListener("click", () => {
                if (window.pianoSynth) {
                    window.pianoSynth.openVisualizer(data.visualizer);
                }
            });
        }

        // Citation chip click -> open drawer
        row.querySelectorAll(".citation-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                const idx = parseInt(chip.dataset.idx, 10);
                const cit = data.citations[idx];
                if (cit) this.openSourceDrawer(cit);
            });
        });

        this.messagesContainer.appendChild(row);
        this.scrollToBottom();
    }

    openSourceDrawer(citation) {
        if (!this.sourceDrawer) return;

        document.getElementById("drawer-chunk-id").textContent = citation.chunk_id;
        document.getElementById("drawer-doc-title").textContent = citation.document_title;
        document.getElementById("drawer-author").textContent = citation.author || "Unknown";
        document.getElementById("drawer-page").textContent = citation.page_number 
            ? `Page ${citation.page_number} (${citation.section || 'General'})` 
            : (citation.section || "Body Text");
        document.getElementById("drawer-content").textContent = citation.quoted_passage;

        this.sourceDrawer.classList.remove("hidden");
    }

    appendLoadingIndicator() {
        const id = `loading-${Date.now()}`;
        const row = document.createElement("div");
        row.className = "message-row message-assistant";
        row.id = id;
        row.innerHTML = `
            <div class="message-avatar">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>
            </div>
            <div class="message-bubble" style="padding: 14px 20px;">
                <div style="display:flex; align-items:center; gap:8px; color:var(--text-secondary); font-size:0.9rem;">
                    <span>Synthesizing evidence from indexed harmony treatises...</span>
                </div>
            </div>
        `;
        this.messagesContainer.appendChild(row);
        this.scrollToBottom();
        return id;
    }

    appendErrorMessage(text) {
        const row = document.createElement("div");
        row.className = "message-row message-assistant";
        row.innerHTML = `
            <div class="message-avatar" style="background:var(--status-error);">!</div>
            <div class="message-bubble" style="border-color: rgba(239, 68, 68, 0.4); background: var(--status-error-bg);">
                <strong style="color:var(--status-error);">Request Failed</strong>
                <p style="color: #fca5a5; font-size:0.9rem; margin-top:4px;">${this.escapeHTML(text)}</p>
            </div>
        `;
        this.messagesContainer.appendChild(row);
        this.scrollToBottom();
    }

    removeMessage(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    scrollToBottom() {
        const viewport = document.querySelector(".chat-viewport");
        if (viewport) {
            viewport.scrollTop = viewport.scrollHeight;
        }
    }

    escapeHTML(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    formatMarkdown(text) {
        if (!text) return "";
        let escaped = this.escapeHTML(text);

        // Bold
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Quotes
        escaped = escaped.replace(/^> (.*)$/gm, '<blockquote>$1</blockquote>');
        // Bullet points
        escaped = escaped.replace(/^\* (.*)$/gm, '• $1<br>');
        // Newlines
        escaped = escaped.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');

        return escaped;
    }
}

window.chatController = new ChatController();
