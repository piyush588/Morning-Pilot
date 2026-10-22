/**
 * app.js — Main application controller.
 * Initializes all modules, handles routing/tabs, and orchestrates the generate flow.
 */

(function () {
  'use strict';

  // ---- Tab Navigation ----
  const tabs = document.querySelectorAll('.nav-tab');
  const sections = document.querySelectorAll('.page-section');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      sections.forEach(s => {
        s.classList.remove('active');
        if (s.id === `section-${target}`) {
          s.classList.add('active');
        }
      });
    });
  });

  // ---- Initialize Modules ----
  Player.init();
  Profile.init();
  Conversation.init();

  // ---- Onboarding ----
  const onboardingSave = document.getElementById('onboarding-save');
  if (onboardingSave) {
    onboardingSave.addEventListener('click', () => {
      if (Profile.selectedTopics.size === 0) {
        Components.showToast('Select at least one interest to begin', 'error');
        return;
      }
      Profile.saveOnboarding();
    });
  }

  // ---- Check if profile already exists ----
  (async function checkProfile() {
    try {
      const profile = await API.getProfile();
      if (profile && profile.interests && profile.interests.length > 0) {
        // Profile exists, skip onboarding
        const overlay = document.getElementById('onboarding-overlay');
        if (overlay) overlay.classList.add('hidden');
        Profile.currentProfile = profile;
        Profile._updateSidebar();
        Profile._updateProfilePage();
      }
    } catch (e) {
      console.log('First time setup: showing onboarding');
    }

    // Try to load latest briefing
    try {
      const latest = await API.getLatestBriefing();
      if (latest && latest.briefing_id) {
        Transcript.showBriefing(latest);
        if (latest.audio_url) {
          Player.loadBriefing(latest.briefing_id, latest.audio_url);
        }
        const statusText = document.getElementById('player-status-text');
        if (statusText) statusText.textContent = 'Latest briefing ready';
      }
    } catch (e) {
      console.log('No previous briefing found');
    }
  })();

  // ---- Generate Briefing ----
  const generateBtn = document.getElementById('generate-btn');
  const heroGenerateBtn = document.getElementById('hero-generate-btn');
  const pipelineSteps = document.getElementById('pipeline-steps');

  async function triggerBriefingGeneration() {
    const btns = [generateBtn, heroGenerateBtn].filter(Boolean);
    btns.forEach(b => {
      b.disabled = true;
      b.dataset.origText = b.textContent;
      b.textContent = 'Generating...';
    });

    // Reset UI
    if (pipelineSteps) {
      pipelineSteps.innerHTML = '';
      pipelineSteps.style.display = 'flex';
    }
    Transcript.clear();

    // Update status
    const statusDot = document.getElementById('player-status-dot');
    const statusText = document.getElementById('player-status-text');
    if (statusDot) statusDot.className = 'status-dot generating';
    if (statusText) statusText.textContent = 'Gathering live news & generating audio...';
    
    const playBtn = document.getElementById('play-btn');
    if (playBtn) playBtn.disabled = true;

    try {
      await API.streamBriefing(
        // onStep
        (step) => {
          if (pipelineSteps) {
            pipelineSteps.appendChild(Components.createPipelineStep(step));
            pipelineSteps.scrollTop = pipelineSteps.scrollHeight;
          }
        },
        // onComplete
        (briefing) => {
          Transcript.showBriefing(briefing);

          if (briefing.audio_url) {
            Player.loadBriefing(briefing.briefing_id, briefing.audio_url);
          }

          if (statusDot) statusDot.className = 'status-dot';
          if (statusText) statusText.textContent = 'Briefing ready';

          if (pipelineSteps) {
            pipelineSteps.appendChild(Components.createPipelineStep({
              step: 'complete',
              message: 'Your briefing is ready to play.',
            }));
          }

          Components.showToast('Briefing generated successfully', 'success');

          btns.forEach(b => {
            b.disabled = false;
            b.textContent = b.dataset.origText || 'Generate Briefing';
          });
        },
      );
    } catch (e) {
      console.error('Generate failed:', e);
      Components.showToast(`Generation failed: ${e.message}`, 'error');

      if (statusDot) statusDot.className = 'status-dot';
      if (statusText) statusText.textContent = 'Generation failed';

      btns.forEach(b => {
        b.disabled = false;
        b.textContent = b.dataset.origText || 'Generate Briefing';
      });
    }
  }

  if (generateBtn) generateBtn.addEventListener('click', triggerBriefingGeneration);
  if (heroGenerateBtn) heroGenerateBtn.addEventListener('click', triggerBriefingGeneration);

  // ---- Profile Edit ----
  const editProfileBtn = document.getElementById('edit-profile-btn');
  const saveProfileBtn = document.getElementById('save-profile-btn');

  if (editProfileBtn) {
    editProfileBtn.addEventListener('click', () => {
      const nameInput = document.getElementById('profile-name');
      const topicChips = document.querySelectorAll('#profile-topics .topic-chip');

      nameInput.readOnly = !nameInput.readOnly;

      topicChips.forEach(c => {
        c.disabled = !c.disabled;
        if (!c.disabled) {
          c.addEventListener('click', function handler() {
            c.classList.toggle('selected');
          });
        }
      });

      if (saveProfileBtn) saveProfileBtn.style.display = nameInput.readOnly ? 'none' : 'inline-flex';
      editProfileBtn.textContent = nameInput.readOnly ? 'Edit Topics' : 'Cancel';
    });
  }

  if (saveProfileBtn) {
    saveProfileBtn.addEventListener('click', async () => {
      const name = document.getElementById('profile-name').value.trim();
      const selectedChips = document.querySelectorAll('#profile-topics .topic-chip.selected');
      const interests = Array.from(selectedChips).map((c, i) => ({
        topic: c.textContent,
        score: 10 - i * 0.5,
        source: 'manual',
        reason: 'Updated in profile',
      }));

      try {
        await API.updateProfile({ name, interests });
        Profile.loadProfile();
        Components.showToast('Profile updated', 'success');

        document.getElementById('profile-name').readOnly = true;
        document.querySelectorAll('#profile-topics .topic-chip').forEach(c => c.disabled = true);
        saveProfileBtn.style.display = 'none';
        if (editProfileBtn) editProfileBtn.textContent = 'Edit Topics';
      } catch (e) {
        Components.showToast('Failed to save profile', 'error');
      }
    });
  }

  // ---- Set today's date in header & player ----
  const playerDate = document.getElementById('player-date');
  if (playerDate && !playerDate.textContent) {
    playerDate.textContent = new Date().toLocaleDateString('en-IN', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  }

  const headerDate = document.getElementById('header-date');
  if (headerDate) {
    headerDate.textContent = new Date().toLocaleDateString('en-IN', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  }

  console.log('Morning Pilot initialized with Apple minimal theme');
})();
