/**
 * HarmonicRAG — Main Application Orchestrator
 * View switching, settings, sidebar history, and health status polling.
 */

class HarmonicApp {
    constructor() {
        this.currentView = "chat";
        this.sidebar = document.getElementById("sidebar");
        this.settingsModal = document.getElementById("settings-modal");
        this.btnOpenSettings = document.getElementById("btn-open-settings");
        this.btnCloseSettings = document.getElementById("btn-close-settings");

        this.init();
    }

    init() {
        // Navigation Switcher
        document.querySelectorAll(".nav-item").forEach(btn => {
            btn.addEventListener("click", () => {
                const view = btn.dataset.view;
                this.switchView(view);
            });
        });

        // Mobile Sidebar Toggles
        const mobileMenuBtn = document.getElementById("btn-mobile-menu");
        const sidebarToggleBtn = document.getElementById("btn-sidebar-toggle");

        if (mobileMenuBtn && this.sidebar) {
            mobileMenuBtn.addEventListener("click", () => {
                this.sidebar.classList.add("open");
            });
        }
        if (sidebarToggleBtn && this.sidebar) {
            sidebarToggleBtn.addEventListener("click", () => {
                this.sidebar.classList.remove("open");
            });
        }

        // Settings Modal
        if (this.btnOpenSettings && this.settingsModal) {
            this.btnOpenSettings.addEventListener("click", () => {
                this.settingsModal.classList.remove("hidden");
            });
        }
        if (this.btnCloseSettings && this.settingsModal) {
            this.btnCloseSettings.addEventListener("click", () => {
                this.settingsModal.classList.add("hidden");
            });
        }
        const btnSaveSettings = document.getElementById("btn-save-settings");
        if (btnSaveSettings) {
            btnSaveSettings.addEventListener("click", () => {
                alert("Settings saved for current browser session.");
                this.settingsModal.classList.add("hidden");
            });
        }

        // Initial data loads
        this.checkHealth();
        this.loadConversations();
    }

    switchView(viewName) {
        this.currentView = viewName;

        // Update nav items
        document.querySelectorAll(".nav-item").forEach(n => {
            n.classList.toggle("active", n.dataset.view === viewName);
        });

        // Update view panels
        document.querySelectorAll(".view-panel").forEach(p => {
            p.classList.remove("active");
        });

        const activePanel = document.getElementById(`view-${viewName}`);
        if (activePanel) {
            activePanel.classList.add("active");
        }

        // Close mobile sidebar if open
        if (this.sidebar) {
            this.sidebar.classList.remove("open");
        }

        if (viewName !== "chat" && window.pianoSynth) {
            window.pianoSynth.stopAll();
        }

        // Refresh specific view data
        if (viewName === "documents" && window.documentManager) {
            window.documentManager.loadDocuments();
        } else if (viewName === "evaluation" && window.evaluationController) {
            window.evaluationController.loadLatestResults();
        }
    }

    async checkHealth() {
        const statusDot = document.getElementById("system-status-dot");
        const statusText = document.getElementById("system-status-text");

        try {
            const resp = await fetch("/api/health");
            if (!resp.ok) throw new Error("Health check failed");
            const data = await resp.json();

            if (statusDot && statusText) {
                if (data.gemini_api_key_configured) {
                    statusDot.className = "status-dot status-ok";
                    statusText.textContent = "Gemini: Configured";
                    statusText.title = "Gemini API key is configured";
                } else {
                    statusDot.className = "status-dot status-warning";
                    statusText.textContent = "Gemini: Unavailable";
                    statusText.title = "No Gemini API key set; local fallback active";
                }
            }
        } catch (err) {
            if (statusDot && statusText) {
                statusDot.className = "status-dot status-error";
                statusText.textContent = "Backend Offline";
                statusText.title = "Cannot reach HarmonicRAG server";
            }
        }
    }

    async loadConversations() {
        const listContainer = document.getElementById("conversation-list");
        if (!listContainer) return;

        try {
            const resp = await fetch("/api/chat/conversations");
            if (!resp.ok) return;
            const convs = await resp.json();

            listContainer.innerHTML = "";
            if (!convs || convs.length === 0) {
                listContainer.innerHTML = `<span style="font-size:0.75rem; color:var(--text-muted); padding:4px 8px;">No discussions yet</span>`;
                return;
            }

            convs.forEach(c => {
                const item = document.createElement("div");
                item.className = "history-item";
                item.innerHTML = `
                    <span class="history-title" title="${this.escapeHTML(c.title)}">${this.escapeHTML(c.title)}</span>
                    <button class="history-del-btn" title="Delete conversation">&times;</button>
                `;

                item.querySelector(".history-title").addEventListener("click", async () => {
                    // Switch to chat
                    this.switchView("chat");
                    // Load conversation history
                    const histResp = await fetch(`/api/chat/conversations/${c.conversation_id}`);
                    if (histResp.ok) {
                        const turns = await histResp.json();
                        const msgContainer = document.getElementById("messages-container");
                        const welcome = document.getElementById("welcome-screen");
                        if (welcome) welcome.style.display = "none";
                        if (msgContainer) msgContainer.innerHTML = "";

                        turns.forEach(t => {
                            if (t.role === "user") {
                                window.chatController.appendUserMessage(t.content);
                            } else if (t.role === "assistant" && t.response) {
                                window.chatController.appendAssistantMessage(t.response, "");
                            }
                        });
                        window.chatController.currentConversationId = c.conversation_id;
                    }
                });

                item.querySelector(".history-del-btn").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    await fetch(`/api/chat/conversations/${c.conversation_id}`, { method: "DELETE" });
                    this.loadConversations();
                });

                listContainer.appendChild(item);
            });
        } catch (err) {
            console.log("Error loading conversations:", err);
        }
    }

    escapeHTML(str) {
        if (!str) return "";
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#x27;");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    window.app = new HarmonicApp();
});
