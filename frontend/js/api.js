/**
 * api.js — Fetch wrappers for all backend endpoints.
 * All functions return Promises. Base URL is relative (same origin).
 */

const API = {
  /** Base URL — empty for same-origin, or set for dev proxy */
  BASE: '',

  /** GET request helper */
  async get(path) {
    const resp = await fetch(`${this.BASE}${path}`);
    if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
    return resp.json();
  },

  /** POST request helper (JSON body) */
  async post(path, body = {}) {
    const resp = await fetch(`${this.BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`POST ${path} failed: ${resp.status}`);
    return resp.json();
  },

  /** PUT request helper (JSON body) */
  async put(path, body = {}) {
    const resp = await fetch(`${this.BASE}${path}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!resp.ok) throw new Error(`PUT ${path} failed: ${resp.status}`);
    return resp.json();
  },

  // ---- Profile ----
  getProfile(userId = 'demo-user') {
    return this.get(`/api/profile?user_id=${userId}`);
  },

  updateProfile(data) {
    return this.put('/api/profile', data);
  },

  getInterests(userId = 'demo-user') {
    return this.get(`/api/profile/interests?user_id=${userId}`);
  },

  // ---- Briefing ----
  generateBriefing(body = {}) {
    return this.post('/api/briefing/generate', body);
  },

  /**
   * Stream briefing generation via SSE.
   * @param {Function} onStep  - called with each progress event
   * @param {Function} onComplete - called with the final briefing
   * @param {Object} body - optional request body
   */
  async streamBriefing(onStep, onComplete, body = {}) {
    const resp = await fetch(`${this.BASE}/api/briefing/generate/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) throw new Error(`Stream failed: ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.step === 'complete') {
              onComplete(data.briefing || data);
            } else {
              onStep(data);
            }
          } catch (e) {
            console.warn('SSE parse error:', e);
          }
        }
      }
    }
  },

  getLatestBriefing(userId = 'demo-user') {
    return this.get(`/api/briefing/latest?user_id=${userId}`);
  },

  getAudioUrl(briefingId) {
    return `${this.BASE}/api/briefing/${briefingId}/audio`;
  },

  // ---- Conversation ----
  askQuestion(briefingId, question) {
    return this.post('/api/conversation/ask', {
      briefing_id: briefingId,
      question: question,
    });
  },

  /**
   * Send audio for voice Q&A.
   * @param {string} briefingId
   * @param {Blob} audioBlob
   */
  async askVoice(briefingId, audioBlob) {
    const formData = new FormData();
    formData.append('briefing_id', briefingId);
    formData.append('audio', audioBlob, 'recording.webm');

    const resp = await fetch(`${this.BASE}/api/conversation/ask-voice`, {
      method: 'POST',
      body: formData,
    });
    if (!resp.ok) throw new Error(`Voice Q&A failed: ${resp.status}`);
    return resp.json();
  },

  // ---- Health ----
  getHealth() {
    return this.get('/api/health');
  },
};
