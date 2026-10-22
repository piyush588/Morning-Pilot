/**
 * player.js — Audio player controlling the central Voice Orb and audio playback.
 */

const Player = {
  audio: null,
  isPlaying: false,
  currentBriefingId: null,

  init() {
    this.audio = document.getElementById('audio-player');
    this.playBtn = document.getElementById('play-btn');
    this.voiceOrb = document.getElementById('voice-orb');
    this.progressBar = document.getElementById('progress-bar');
    this.progressFill = document.getElementById('progress-fill');
    this.timeCurrent = document.getElementById('time-current');
    this.timeTotal = document.getElementById('time-total');
    this.statusDot = document.getElementById('player-status-dot');
    this.statusText = document.getElementById('player-status-text');

    // Click play button or center Voice Orb to toggle playback
    if (this.playBtn) {
      this.playBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.togglePlay();
      });
    }

    if (this.voiceOrb) {
      this.voiceOrb.addEventListener('click', () => this.togglePlay());
    }

    // Progress bar seek
    if (this.progressBar) {
      this.progressBar.addEventListener('click', (e) => {
        if (!this.audio.duration) return;
        const rect = this.progressBar.getBoundingClientRect();
        const pct = (e.clientX - rect.left) / rect.width;
        this.audio.currentTime = pct * this.audio.duration;
      });
    }

    // Audio events
    this.audio.addEventListener('timeupdate', () => this._onTimeUpdate());
    this.audio.addEventListener('loadedmetadata', () => this._onLoaded());
    this.audio.addEventListener('ended', () => this._onEnded());
    this.audio.addEventListener('error', (e) => {
      console.error('Audio error:', e);
      Components.showToast('Failed to load audio episode', 'error');
    });
  },

  /**
   * Load a briefing audio.
   * @param {string} briefingId
   * @param {string} audioUrl
   */
  loadBriefing(briefingId, audioUrl) {
    this.currentBriefingId = briefingId;
    this.audio.src = audioUrl;
    this.audio.load();

    if (this.playBtn) this.playBtn.disabled = false;
    if (this.voiceOrb) this.voiceOrb.classList.add('ready');

    this._updateStatus('ready', 'Ready to play');
  },

  togglePlay() {
    if (this.isPlaying) {
      this.pause();
    } else {
      this.play();
    }
  },

  play() {
    if (!this.audio.src) return;

    // Pause any Q&A answer audio if playing
    const answerAudio = document.getElementById('answer-audio');
    if (answerAudio && !answerAudio.paused) {
      answerAudio.pause();
    }

    this.audio.play();
    this.isPlaying = true;

    if (this.playBtn) {
      this.playBtn.innerHTML = Components.ICONS.pause;
      this.playBtn.setAttribute('title', 'Pause');
    }

    if (this.voiceOrb) {
      this.voiceOrb.classList.add('is-playing');
    }

    this._updateStatus('playing', 'Playing Briefing');
  },

  pause() {
    this.audio.pause();
    this.isPlaying = false;

    if (this.playBtn) {
      this.playBtn.innerHTML = Components.ICONS.play;
      this.playBtn.setAttribute('title', 'Play');
    }

    if (this.voiceOrb) {
      this.voiceOrb.classList.remove('is-playing');
    }

    this._updateStatus('paused', 'Paused');
  },

  _updateStatus(stateClass, label) {
    if (this.statusDot) {
      this.statusDot.className = `status-dot ${stateClass}`;
    }
    if (this.statusText) {
      this.statusText.textContent = label;
    }
  },

  _onTimeUpdate() {
    if (!this.audio.duration) return;
    const pct = (this.audio.currentTime / this.audio.duration) * 100;
    if (this.progressFill) this.progressFill.style.width = `${pct}%`;
    if (this.timeCurrent) this.timeCurrent.textContent = this._formatTime(this.audio.currentTime);
  },

  _onLoaded() {
    if (this.timeTotal) this.timeTotal.textContent = this._formatTime(this.audio.duration);
  },

  _onEnded() {
    this.isPlaying = false;
    if (this.playBtn) this.playBtn.innerHTML = Components.ICONS.play;
    if (this.voiceOrb) this.voiceOrb.classList.remove('is-playing');
    if (this.progressFill) this.progressFill.style.width = '0%';
    this._updateStatus('ready', 'Briefing Completed');

    Components.showToast('Briefing finished. Tap mic or ask a question anytime.', 'info');
  },

  _formatTime(s) {
    const min = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${min}:${sec.toString().padStart(2, '0')}`;
  },
};
