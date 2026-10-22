/**
 * profile.js — Interest picker, profile management, sidebar updates.
 */

const Profile = {
  /** All available topics for the picker */
  AVAILABLE_TOPICS: [
    'AI', 'Cricket', 'Startups', 'Markets', 'Technology', 'Sports',
    'Politics', 'Economy', 'Climate', 'Health', 'Education', 'Space',
    'Crypto', 'Entertainment', 'Science', 'Gaming', 'Business', 'World News',
  ],

  selectedTopics: new Set(),
  currentProfile: null,

  init() {
    this._renderOnboardingTopics();
    this._renderProfileTopics();
  },

  /** Render topic chips for onboarding */
  _renderOnboardingTopics() {
    const container = document.getElementById('onboarding-topics');
    if (!container) return;

    container.innerHTML = '';
    this.AVAILABLE_TOPICS.forEach(topic => {
      const chip = document.createElement('button');
      chip.className = 'topic-chip';
      chip.textContent = topic;
      chip.addEventListener('click', () => {
        if (this.selectedTopics.has(topic)) {
          this.selectedTopics.delete(topic);
          chip.classList.remove('selected');
        } else {
          this.selectedTopics.add(topic);
          chip.classList.add('selected');
        }
      });
      container.appendChild(chip);
    });

    // Pre-select defaults
    ['AI', 'Cricket', 'Startups', 'Markets'].forEach(t => {
      this.selectedTopics.add(t);
      const chips = container.querySelectorAll('.topic-chip');
      chips.forEach(c => {
        if (c.textContent === t) c.classList.add('selected');
      });
    });
  },

  /** Render topic chips for profile edit page */
  _renderProfileTopics() {
    const container = document.getElementById('profile-topics');
    if (!container) return;

    container.innerHTML = '';
    this.AVAILABLE_TOPICS.forEach(topic => {
      const chip = document.createElement('button');
      chip.className = 'topic-chip';
      chip.textContent = topic;
      chip.disabled = true; // Read-only by default
      container.appendChild(chip);
    });
  },

  /** Save onboarding profile and dismiss overlay */
  async saveOnboarding() {
    const name = document.getElementById('onboarding-name').value.trim() || 'User';
    const interests = Array.from(this.selectedTopics).map((topic, i) => ({
      topic,
      score: 10 - i,
      source: 'manual',
      reason: 'Selected at signup',
    }));

    try {
      await API.updateProfile({ name, interests });
      Components.showToast(`Welcome, ${name}!`, 'success');
    } catch (e) {
      console.error('Profile save failed:', e);
      // Continue anyway for demo
    }

    document.getElementById('onboarding-overlay').classList.add('hidden');
    this.loadProfile();
  },

  /** Load profile from backend and update all UI */
  async loadProfile() {
    try {
      this.currentProfile = await API.getProfile();
    } catch (e) {
      console.warn('Could not load profile from server, using defaults');
      this.currentProfile = {
        user_id: 'demo-user',
        name: 'Piyush',
        interests: [
          { topic: 'AI', score: 8, source: 'manual' },
          { topic: 'Cricket', score: 7, source: 'manual' },
          { topic: 'Startups', score: 6, source: 'manual' },
          { topic: 'Markets', score: 5, source: 'manual' },
        ],
        recent_updates: [],
      };
    }

    this._updateSidebar();
    this._updateProfilePage();
  },

  /** Update sidebar interest list */
  _updateSidebar() {
    const listEl = document.getElementById('interests-list');
    if (!listEl || !this.currentProfile) return;

    listEl.innerHTML = '';
    const sorted = [...this.currentProfile.interests].sort((a, b) => b.score - a.score);
    sorted.forEach(interest => {
      listEl.appendChild(Components.createInterestItem(interest));
    });
  },

  /** Update interest updates feed */
  updateFeed(updates) {
    const feed = document.getElementById('updates-feed');
    if (!feed) return;

    // Clear empty state
    const empty = feed.querySelector('.empty-state');
    if (empty) empty.remove();

    updates.forEach(update => {
      const item = Components.createUpdateItem(update, true);
      feed.insertBefore(item, feed.firstChild);
    });

    // Keep max 15 items
    while (feed.children.length > 15) {
      feed.removeChild(feed.lastChild);
    }
  },

  /** Add a single interest update (from conversation) */
  addUpdate(update) {
    if (!this.currentProfile) return;

    // Update local data
    if (update.action === 'added') {
      this.currentProfile.interests.push({
        topic: update.topic,
        score: parseFloat(update.delta) || 3,
        source: 'question',
      });
    } else if (update.action === 'boosted') {
      const existing = this.currentProfile.interests.find(
        i => i.topic.toLowerCase() === update.topic.toLowerCase()
      );
      if (existing) {
        existing.score = Math.min(10, existing.score + (parseFloat(update.delta) || 2));
      }
    }

    this.currentProfile.recent_updates = this.currentProfile.recent_updates || [];
    this.currentProfile.recent_updates.unshift(update);

    this._updateSidebar();
    this.updateFeed([update]);
  },

  /** Update profile page fields */
  _updateProfilePage() {
    if (!this.currentProfile) return;

    const nameInput = document.getElementById('profile-name');
    if (nameInput) nameInput.value = this.currentProfile.name;

    const topicContainer = document.getElementById('profile-topics');
    if (topicContainer) {
      const chips = topicContainer.querySelectorAll('.topic-chip');
      const activeTopics = new Set(this.currentProfile.interests.map(i => i.topic));
      chips.forEach(c => {
        if (activeTopics.has(c.textContent)) {
          c.classList.add('selected');
        } else {
          c.classList.remove('selected');
        }
      });
    }
  },
};
