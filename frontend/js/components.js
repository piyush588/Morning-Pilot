/**
 * components.js — Reusable UI components with Apple-inspired SVG icons (No Emojis).
 */

const Components = {
  /** SVG Icon dictionary */
  ICONS: {
    check: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
    error: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    info: `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
    link: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>`,
    play: `<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"/></svg>`,
    pause: `<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`,
    mic: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>`,
    send: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>`,
    sparkle: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/></svg>`,
    search: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
    document: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>`,
    volume: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>`,
  },

  /**
   * Show a toast notification.
   * @param {string} message
   * @param {'success'|'error'|'info'} type
   * @param {number} duration - ms before auto-dismiss
   */
  showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="toast-icon">${this.ICONS[type] || this.ICONS.info}</span> <span>${message}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px) scale(0.96)';
      toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },

  /**
   * Create a tool badge element.
   * @param {Object} tool - { tool, query, url, action }
   * @returns {HTMLElement}
   */
  createToolBadge(tool) {
    const badge = document.createElement('span');
    const name = tool.tool.replace('tinyfish_', '');
    const typeMap = {
      search: 'search',
      fetch: 'fetch',
      web_agent: 'agent',
    };
    badge.className = `tool-badge ${typeMap[name] || 'search'}`;
    badge.textContent = name.toUpperCase();
    badge.title = tool.query || tool.url || tool.action || '';
    return badge;
  },

  /**
   * Create a source link element.
   * @param {Object} source - { title, url, snippet }
   * @returns {HTMLElement}
   */
  createSourceLink(source) {
    const item = document.createElement('div');
    item.className = 'message-source-item';
    item.innerHTML = `
      <span class="source-icon">${this.ICONS.link}</span>
      <a href="${source.url}" target="_blank" rel="noopener">${source.title || 'Source'}</a>
    `;
    return item;
  },

  /**
   * Create a story card element.
   * @param {Object} story
   * @returns {HTMLElement}
   */
  createStoryCard(story) {
    const card = document.createElement('div');
    card.className = 'story-card';

    let sourcesHtml = '';
    if (story.sources && story.sources.length > 0) {
      sourcesHtml = story.sources.map(s =>
        `<a class="story-source-link" href="${s.url}" target="_blank" rel="noopener">
          ${this.ICONS.link} <span>${s.title || 'Source'}</span>
        </a>`
      ).join('');
    }

    card.innerHTML = `
      <div class="story-top-row">
        <span class="story-rank">${story.rank}</span>
        <h4 class="story-headline">${story.headline}</h4>
      </div>
      ${story.summary ? `<p class="story-summary">${story.summary}</p>` : ''}
      <div class="story-meta">
        <span class="story-interest-tag">${story.interest_match}</span>
        <div class="story-sources-wrap">${sourcesHtml}</div>
        <button class="story-ask-btn" data-question="Tell me more about ${story.headline.replace(/"/g, '&quot;')}">
          ${this.ICONS.sparkle} Ask about this
        </button>
      </div>
    `;

    // Connect "Ask about this" quick button to conversation input
    const askBtn = card.querySelector('.story-ask-btn');
    if (askBtn) {
      askBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const input = document.getElementById('question-input');
        if (input) {
          input.value = `Tell me more about: ${story.headline}`;
          input.focus();
        }
      });
    }

    return card;
  },

  /**
   * Create an interest item for the sidebar.
   * @param {Object} interest - { topic, score, source }
   * @returns {HTMLElement}
   */
  createInterestItem(interest) {
    const item = document.createElement('div');
    item.className = 'interest-item';

    const pct = Math.min(100, Math.round((interest.score / 10) * 100));

    item.innerHTML = `
      <div class="interest-header">
        <span class="interest-topic">${interest.topic}</span>
        <span class="interest-score">${interest.score.toFixed(1)}</span>
      </div>
      <div class="interest-bar-track">
        <div class="interest-bar-fill" style="width: ${pct}%"></div>
      </div>
    `;
    return item;
  },

  /**
   * Create an interest update item for the feed.
   * @param {Object} update
   * @returns {HTMLElement}
   */
  createUpdateItem(update, highlight = false) {
    const item = document.createElement('div');
    item.className = `update-item ${highlight ? 'highlight' : ''}`;

    const isNeg = update.delta && update.delta.startsWith('-');

    item.innerHTML = `
      <span class="update-delta ${isNeg ? 'negative' : ''}">${update.delta}</span>
      <span class="update-topic">${update.topic}</span>
      <span class="update-trigger">${update.trigger || update.action}</span>
    `;
    return item;
  },

  /**
   * Create a pipeline step element with Apple SVGs.
   * @param {Object} step - { step, topic, message }
   * @returns {HTMLElement}
   */
  createPipelineStep(step) {
    const el = document.createElement('div');
    el.className = 'pipeline-step';

    const iconMap = {
      loading: this.ICONS.document,
      searching: this.ICONS.search,
      fetching: this.ICONS.document,
      ranking: this.ICONS.sparkle,
      verifying: this.ICONS.check,
      scripting: this.ICONS.sparkle,
      speaking: this.ICONS.volume,
      complete: this.ICONS.check,
    };

    const isDone = step.step === 'complete';
    el.innerHTML = `
      <div class="pipeline-step-icon ${isDone ? 'done' : 'active'}">
        ${iconMap[step.step] || this.ICONS.sparkle}
      </div>
      <span class="pipeline-step-message">${step.message || step.step}</span>
    `;
    return el;
  },

  /**
   * Loading dots element.
   * @returns {HTMLElement}
   */
  createLoadingDots() {
    const el = document.createElement('div');
    el.className = 'loading-dots';
    el.innerHTML = '<span></span><span></span><span></span>';
    return el;
  },
};
