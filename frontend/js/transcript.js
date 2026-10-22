/**
 * transcript.js — Briefing transcript and story display.
 */

const Transcript = {
  currentBriefing: null,

  /** Display a briefing's transcript and stories */
  showBriefing(briefingData) {
    this.currentBriefing = briefingData;

    // Show transcript
    const transcriptCard = document.getElementById('transcript-card');
    const transcriptText = document.getElementById('transcript-text');
    if (transcriptCard && briefingData.script) {
      transcriptText.textContent = briefingData.script;
      transcriptCard.style.display = 'block';
    }

    // Show stories
    const storiesCard = document.getElementById('stories-card');
    const storiesGrid = document.getElementById('stories-grid');
    if (storiesCard && briefingData.stories && briefingData.stories.length > 0) {
      storiesGrid.innerHTML = '';
      briefingData.stories.forEach(story => {
        storiesGrid.appendChild(Components.createStoryCard(story));
      });
      storiesCard.style.display = 'block';
    }

    // Update player info
    const playerTitle = document.getElementById('player-title');
    const playerDate = document.getElementById('player-date');
    if (playerTitle) playerTitle.textContent = 'Your Morning Briefing';
    if (playerDate && briefingData.generated_at) {
      const d = new Date(briefingData.generated_at);
      playerDate.textContent = d.toLocaleDateString('en-IN', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    }
  },

  /** Clear transcript and stories */
  clear() {
    this.currentBriefing = null;
    const transcriptCard = document.getElementById('transcript-card');
    const storiesCard = document.getElementById('stories-card');
    if (transcriptCard) transcriptCard.style.display = 'none';
    if (storiesCard) storiesCard.style.display = 'none';
  },
};
