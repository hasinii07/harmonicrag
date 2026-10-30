/**
 * HarmonicRAG — Interactive Piano & Web Audio Synthesizer
 * Uses Web Audio API for polyphonic synthesis and SVG/DOM for interactive keys.
 */

class PianoSynthesizer {
    constructor() {
        this.audioCtx = null;
        this.activeOscillators = [];
        this.playbackTimer = null;
        this.bpm = 120;
        this.currentVisualizerData = null;
        this.isVisualizerOpen = false;
        this._listenersAttached = false;

        // Note frequencies mapping helper
        this.noteNames = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
        this.startOctave = 3;
        this.octaveCount = 3; // C3 to B5 (36 keys)

        this.initDOM();
    }

    getAudioContext() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext();
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
        return this.audioCtx;
    }

    noteNameToMidi(noteStr) {
        // e.g. "C4", "F#4", "Bb4"
        const match = noteStr.trim().match(/^([A-Ga-g][#b♯♭]?)(\d)$/);
        if (!match) return 60; // Default C4

        let name = match[1].toUpperCase().replace('♯', '#').replace('♭', 'b');
        const enharmonic = { "DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#" };
        if (enharmonic[name]) name = enharmonic[name];

        const octave = parseInt(match[2], 10);
        const noteIndex = this.noteNames.indexOf(name);
        if (noteIndex === -1) return 60;

        return (octave + 1) * 12 + noteIndex;
    }

    midiToFreq(midi) {
        return 440 * Math.pow(2, (midi - 69) / 12);
    }

    playTone(midi, duration = 1.0, timeOffset = 0) {
        const ctx = this.getAudioContext();
        const now = ctx.currentTime + timeOffset;
        const freq = this.midiToFreq(midi);

        // Multi-oscillator tone synthesis (Triangle fundamental + Sine harmonic)
        const osc1 = ctx.createOscillator();
        const osc2 = ctx.createOscillator();
        const gainNode = ctx.createGain();

        osc1.type = 'triangle';
        osc1.frequency.setValueAtTime(freq, now);

        osc2.type = 'sine';
        osc2.frequency.setValueAtTime(freq * 2, now); // Second harmonic overtone

        // ADSR Envelope
        gainNode.gain.setValueAtTime(0.0001, now);
        gainNode.gain.linearRampToValueAtTime(0.22, now + 0.008); // Quick attack
        gainNode.gain.exponentialRampToValueAtTime(0.12, now + 0.15); // Decay to sustain
        gainNode.gain.exponentialRampToValueAtTime(0.0001, now + duration); // Release

        osc1.connect(gainNode);
        osc2.connect(gainNode);
        gainNode.connect(ctx.destination);

        osc1.start(now);
        osc2.start(now);
        osc1.stop(now + duration);
        osc2.stop(now + duration);

        this.activeOscillators.push(osc1, osc2);
    }

    stopAll() {
        if (this.playbackTimer) {
            clearTimeout(this.playbackTimer);
            this.playbackTimer = null;
        }
        this.activeOscillators.forEach(osc => {
            try { osc.stop(); } catch (e) {}
        });
        this.activeOscillators = [];
        this.clearKeyHighlights(false);
    }

    initDOM() {
        const container = document.getElementById("piano-keys");
        if (!container) return;
        container.innerHTML = "";

        // Build white and black keys across octaves
        for (let oct = this.startOctave; oct < this.startOctave + this.octaveCount; oct++) {
            for (let i = 0; i < 12; i++) {
                const noteName = this.noteNames[i];
                const noteWithOct = `${noteName}${oct}`;
                const isBlack = noteName.includes("#");

                const keyEl = document.createElement("div");
                keyEl.className = `piano-key ${isBlack ? 'black-key' : 'white-key'}`;
                keyEl.dataset.note = noteWithOct;
                keyEl.id = `pkey-${noteWithOct.replace('#', 's')}`;

                const labelSpan = document.createElement("span");
                labelSpan.className = "key-note-label";
                labelSpan.textContent = noteWithOct;
                keyEl.appendChild(labelSpan);

                const intervalSpan = document.createElement("span");
                intervalSpan.className = "key-interval-label";
                keyEl.appendChild(intervalSpan);

                keyEl.addEventListener("mousedown", (e) => {
                    e.preventDefault();
                    this.playNoteInteractive(noteWithOct);
                });

                container.appendChild(keyEl);
            }
        }

        // Attach Piano controls & toolbar triggers (ensure attached once)
        if (!this._listenersAttached) {
            this._listenersAttached = true;

            const btnToolbar = document.getElementById("btn-toolbar-visualizer");
            if (btnToolbar) {
                btnToolbar.addEventListener("click", (e) => {
                    e.preventDefault();
                    this.toggleVisualizer();
                });
            }

            const btnClose = document.getElementById("btn-close-piano");
            if (btnClose) {
                btnClose.addEventListener("click", (e) => {
                    e.preventDefault();
                    this.closeVisualizer();
                });
            }

            const btnToggle = document.getElementById("btn-toggle-piano");
            if (btnToggle) {
                btnToggle.addEventListener("click", (e) => {
                    e.preventDefault();
                    this.toggleVisualizer();
                });
            }

            const btnChord = document.getElementById("btn-play-chord");
            if (btnChord) btnChord.addEventListener("click", () => this.playChord());

            const btnScale = document.getElementById("btn-play-scale");
            if (btnScale) btnScale.addEventListener("click", () => this.playScale());

            const btnArp = document.getElementById("btn-play-arpeggio");
            if (btnArp) btnArp.addEventListener("click", () => this.playArpeggio());

            const btnStop = document.getElementById("btn-stop-audio");
            if (btnStop) btnStop.addEventListener("click", () => this.stopAll());

            const slider = document.getElementById("tempo-slider");
            const valText = document.getElementById("tempo-val");
            if (slider && valText) {
                slider.addEventListener("input", (e) => {
                    this.bpm = parseInt(e.target.value, 10);
                    valText.textContent = this.bpm;
                });
            }
        }

        // Initialize state as collapsed / hidden
        this.updatePanelVisibility();
    }

    openVisualizer(loadData = null) {
        this.isVisualizerOpen = true;
        if (loadData) {
            this.loadVisualizerData(loadData, false);
        }
        this.updatePanelVisibility();
    }

    closeVisualizer() {
        this.isVisualizerOpen = false;
        this.stopAll();
        this.updatePanelVisibility();
    }

    toggleVisualizer() {
        if (this.isVisualizerOpen) {
            this.closeVisualizer();
        } else {
            this.openVisualizer();
        }
    }

    updatePanelVisibility() {
        const panel = document.getElementById("piano-panel");
        const toolbarBtn = document.getElementById("btn-toolbar-visualizer");
        if (panel) {
            if (this.isVisualizerOpen) {
                panel.classList.remove("hidden", "collapsed");
                panel.classList.add("open");
                panel.setAttribute("data-state", "open");
                panel.style.display = "flex";
                panel.style.visibility = "visible";
            } else {
                panel.classList.remove("open");
                panel.classList.add("hidden", "collapsed");
                panel.setAttribute("data-state", "closed");
                panel.style.display = "none";
                panel.style.visibility = "hidden";
            }
        }
        if (toolbarBtn) {
            toolbarBtn.classList.toggle("active", this.isVisualizerOpen);
            toolbarBtn.setAttribute("aria-expanded", this.isVisualizerOpen ? "true" : "false");
        }
    }

    playNoteInteractive(noteStr) {
        const midi = this.noteNameToMidi(noteStr);
        this.playTone(midi, 0.8);
        this.flashKey(noteStr);
    }

    flashKey(noteStr) {
        const keyId = `pkey-${noteStr.replace('#', 's')}`;
        const el = document.getElementById(keyId);
        if (el) {
            el.classList.add("active");
            setTimeout(() => el.classList.remove("active"), 300);
        }
    }

    loadVisualizerData(visualizer, autoExpand = false) {
        if (!visualizer || !visualizer.notes || !visualizer.notes.length) return;
        this.currentVisualizerData = visualizer;

        const label = document.getElementById("piano-label");
        if (label) {
            label.textContent = visualizer.description || `${visualizer.root || ''} ${visualizer.type || ''}`.trim();
        }

        this.highlightTheory(visualizer);

        if (autoExpand) {
            this.openVisualizer();
        }
    }

    clearKeyHighlights(clearLabelsOnly = false) {
        document.querySelectorAll(".piano-key").forEach(k => {
            if (!clearLabelsOnly) {
                k.classList.remove("theory-highlight", "theory-root");
            }
            const iSpan = k.querySelector(".key-interval-label");
            if (iSpan) iSpan.textContent = "";
        });
    }

    highlightTheory(visualizer) {
        this.clearKeyHighlights(false);

        const notes = visualizer.notes;
        const intervals = visualizer.intervals || [];
        const root = visualizer.root;

        notes.forEach((note, idx) => {
            const keyId = `pkey-${note.replace('#', 's')}`;
            const el = document.getElementById(keyId);
            if (el) {
                const isRoot = root && (note.startsWith(root) || idx === 0);
                el.classList.add(isRoot ? "theory-root" : "theory-highlight");

                const iSpan = el.querySelector(".key-interval-label");
                if (iSpan && intervals[idx]) {
                    iSpan.textContent = intervals[idx];
                }
            }
        });
    }

    playChord() {
        if (!this.currentVisualizerData || !this.currentVisualizerData.notes.length) return;
        this.stopAll();

        const notes = this.currentVisualizerData.notes;
        notes.forEach(note => {
            const midi = this.noteNameToMidi(note);
            this.playTone(midi, 1.6);
            this.flashKey(note);
        });
    }

    playScale() {
        if (!this.currentVisualizerData || !this.currentVisualizerData.notes.length) return;
        this.stopAll();

        const notes = [...this.currentVisualizerData.notes];
        // If not already returning to tonic octave, append descending
        const fullSequence = [...notes, ...[...notes].reverse().slice(1)];
        this._playSequence(fullSequence, 0);
    }

    playArpeggio() {
        if (!this.currentVisualizerData || !this.currentVisualizerData.notes.length) return;
        this.stopAll();

        const notes = [...this.currentVisualizerData.notes];
        this._playSequence(notes, 0);
    }

    _playSequence(noteList, index) {
        if (index >= noteList.length) return;

        const note = noteList[index];
        const midi = this.noteNameToMidi(note);
        const beatSec = 60 / this.bpm;

        this.playTone(midi, beatSec * 0.95);
        this.flashKey(note);

        this.playbackTimer = setTimeout(() => {
            this._playSequence(noteList, index + 1);
        }, beatSec * 1000);
    }
}

// Global instance
window.pianoSynth = new PianoSynthesizer();
