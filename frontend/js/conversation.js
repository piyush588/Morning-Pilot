/**
 * conversation.js — Voice Q&A with microphone input, text input, and live interruption.
 */

const Conversation = {
  mediaRecorder: null,
  audioChunks: [],
  isRecording: false,
  answerAudio: null,

  init() {
    this.micBtn = document.getElementById('mic-btn');
    this.questionInput = document.getElementById('question-input');
    this.sendBtn = document.getElementById('send-btn');
    this.messagesContainer = document.getElementById('conversation-messages');
    this.answerAudio = document.getElementById('answer-audio');
    this.voiceOrb = document.getElementById('voice-orb');

    // Set initial mic icon
    if (this.micBtn) {
      this.micBtn.innerHTML = Components.ICONS.mic;
    }

    if (this.sendBtn) {
      this.sendBtn.innerHTML = Components.ICONS.send;
    }

    // Send text question
    if (this.sendBtn) {
      this.sendBtn.addEventListener('click', () => this._sendTextQuestion());
    }

    if (this.questionInput) {
      this.questionInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          this._sendTextQuestion();
        }
      });
    }

    // Mic button — click or hold to talk
    if (this.micBtn) {
      this.micBtn.addEventListener('click', () => {
        if (this.isRecording) {
          this._stopRecording();
        } else {
          this._startRecording();
        }
      });
    }

    // Answer audio events
    if (this.answerAudio) {
      this.answerAudio.addEventListener('play', () => {
        if (this.voiceOrb) this.voiceOrb.classList.add('is-answering');
        const statusText = document.getElementById('player-status-text');
        if (statusText) statusText.textContent = 'Voice Assistant Replying';
      });

      this.answerAudio.addEventListener('ended', () => {
        if (this.voiceOrb) this.voiceOrb.classList.remove('is-answering');
        const statusText = document.getElementById('player-status-text');
        if (statusText) statusText.textContent = Player.isPlaying ? 'Playing Briefing' : 'Ready';
      });

      this.answerAudio.addEventListener('pause', () => {
        if (this.voiceOrb) this.voiceOrb.classList.remove('is-answering');
      });
    }
  },

  /** Get current briefing ID from transcript */
  _getBriefingId() {
    return Transcript.currentBriefing?.briefing_id || 'unknown';
  },

  /** Interrupt playback if active */
  _interruptBriefing() {
    if (Player && Player.isPlaying) {
      Player.pause();
      Components.showToast('Briefing paused for question', 'info', 2500);
    }
  },

  /** Send a text question */
  async _sendTextQuestion() {
    const question = this.questionInput.value.trim();
    if (!question) return;

    // Interrupt current playback if user is asking
    this._interruptBriefing();

    this.questionInput.value = '';
    this.sendBtn.disabled = true;

    // Clear empty state
    const empty = document.getElementById('conversation-empty');
    if (empty) empty.remove();

    // Add user message
    this._addMessage(question, 'user');

    // Add loading indicator
    const loadingMsg = this._addLoadingMessage();

    try {
      const response = await API.askQuestion(this._getBriefingId(), question);
      this._removeMessage(loadingMsg);
      this._addAssistantMessage(response);

      // Update profile if interest changed
      if (response.profile_update) {
        Profile.addUpdate(response.profile_update);
        Components.showToast(
          `${response.profile_update.action === 'added' ? 'Added' : 'Boosted'}: ${response.profile_update.topic} (${response.profile_update.delta})`,
          'success'
        );
      }

      // Play answer audio
      if (response.answer_audio_url) {
        this.answerAudio.src = response.answer_audio_url;
        this.answerAudio.play().catch(e => console.warn('Auto-play blocked:', e));
      }
    } catch (e) {
      this._removeMessage(loadingMsg);
      this._addMessage(`Sorry, I couldn't process that: ${e.message}`, 'assistant');
      Components.showToast('Q&A failed — check your connection', 'error');
    } finally {
      this.sendBtn.disabled = false;
    }
  },

  /** Start recording audio */
  async _startRecording() {
    // Interrupt current playback
    this._interruptBriefing();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      this.audioChunks = [];

      this.mediaRecorder.addEventListener('dataavailable', (e) => {
        this.audioChunks.push(e.data);
      });

      this.mediaRecorder.start();
      this.isRecording = true;
      this.micBtn.classList.add('recording');
      if (this.voiceOrb) this.voiceOrb.classList.add('is-listening');

      const statusText = document.getElementById('player-status-text');
      if (statusText) statusText.textContent = 'Listening to your voice...';
    } catch (e) {
      console.error('Microphone error:', e);
      Components.showToast('Microphone access denied or unavailable', 'error');
    }
  },

  /** Stop recording and send audio */
  async _stopRecording() {
    if (!this.isRecording || !this.mediaRecorder) return;

    this.mediaRecorder.stop();
    this.isRecording = false;
    this.micBtn.classList.remove('recording');
    if (this.voiceOrb) this.voiceOrb.classList.remove('is-listening');

    const statusText = document.getElementById('player-status-text');
    if (statusText) statusText.textContent = 'Processing your question...';

    // Wait for the final data
    this.mediaRecorder.addEventListener('stop', async () => {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

      // Stop stream tracks
      this.mediaRecorder.stream.getTracks().forEach(t => t.stop());

      // Clear empty state
      const empty = document.getElementById('conversation-empty');
      if (empty) empty.remove();

      // Add user message
      this._addMessage('Spoken question', 'user');
      const loadingMsg = this._addLoadingMessage();

      try {
        const response = await API.askVoice(this._getBriefingId(), audioBlob);
        this._removeMessage(loadingMsg);
        this._addAssistantMessage(response);

        if (response.profile_update) {
          Profile.addUpdate(response.profile_update);
          Components.showToast(
            `${response.profile_update.action === 'added' ? 'Added' : 'Boosted'}: ${response.profile_update.topic} (${response.profile_update.delta})`,
            'success'
          );
        }

        if (response.answer_audio_url) {
          this.answerAudio.src = response.answer_audio_url;
          this.answerAudio.play().catch(e => console.warn('Auto-play blocked:', e));
        }
      } catch (e) {
        this._removeMessage(loadingMsg);
        this._addMessage(`Voice Q&A failed: ${e.message}`, 'assistant');
      }
    }, { once: true });
  },

  /** Add a message to the conversation container */
  _addMessage(text, sender) {
    if (!this.messagesContainer) return null;
    const msg = document.createElement('div');
    msg.className = `message ${sender}`;
    msg.innerHTML = `<div class="message-bubble">${text}</div>`;
    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    return msg;
  },

  /** Add assistant response message with citations and badges */
  _addAssistantMessage(data) {
    if (!this.messagesContainer) return;
    const msg = document.createElement('div');
    msg.className = 'message assistant';

    let badgesHtml = '';
    if (data.tools_used && data.tools_used.length > 0) {
      badgesHtml = `<div class="tools-badges">` +
        data.tools_used.map(t => Components.createToolBadge(t).outerHTML).join('') +
        `</div>`;
    }

    let sourcesHtml = '';
    if (data.sources && data.sources.length > 0) {
      sourcesHtml = `<div class="message-sources">` +
        data.sources.map(s => Components.createSourceLink(s).outerHTML).join('') +
        `</div>`;
    }

    msg.innerHTML = `
      <div class="message-bubble">
        ${badgesHtml}
        <div class="message-text">${data.answer_text}</div>
        ${sourcesHtml}
      </div>
    `;

    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  },

  /** Add loading indicator message */
  _addLoadingMessage() {
    if (!this.messagesContainer) return null;
    const msg = document.createElement('div');
    msg.className = 'message assistant loading';
    msg.innerHTML = `
      <div class="message-bubble">
        ${Components.createLoadingDots().outerHTML}
      </div>
    `;
    this.messagesContainer.appendChild(msg);
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    return msg;
  },

  /** Remove a message element */
  _removeMessage(msgEl) {
    if (msgEl && msgEl.remove) msgEl.remove();
  },
};
