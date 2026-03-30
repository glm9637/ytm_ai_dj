// @ts-check
import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit@3.3.2/index.js?module";
import { sharedStyles } from "../shared-style.js"; // Assuming you split this out
import { VIBE_CHANGE_EVENT } from "./vibe.js";

/** @typedef {import('../services/data-service').DataService} DataService */
/** @typedef {import('../types/dto').Party} Party */
/** @typedef {import('../types/dto').Player} Player */

export class MassAiDjParty extends LitElement {
  static get properties() {
    return {
      service: { type: Object },
      party: { type: Object },
      _draftSessions: { type: Array },
      _massPlayers: { type: Array },
      _isDirty: { type: Boolean },
    };
  }

  constructor() {
    super();
    /** @type {DataService} */
    this.service;
    /** @type {Party} */
    this.party;

    /**
     * @type {import('../types/dto').VibeSession[]}
     */
    this._draftSessions = [];
    /**
     * @type {import('../types/dto').Player[]}
     */
    this._massPlayers = [];
    this._isDirty = false;
    this.#unsubs = [];
  }
  /** @type {(() => void)[]} */
  #unsubs = [];

  connectedCallback() {
    super.connectedCallback();
    this.#unsubs = [
      this.service.registerPlayersCallback((players) => {
        this._massPlayers = players;
      }),
    ];
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#unsubs.forEach((unsub) => unsub());
  }

  /**
   * Syncs the local draft whenever a new party object is received from the service.
   * @param {import('lit').PropertyValues} changedProps
   */
  willUpdate(changedProps) {
    if (changedProps.has("party") && this.party) {
      this._resetDraft();
    }
  }

  /**
   * Reverts the local draft to match the saved state of the party.
   */
  _resetDraft() {
    this._draftSessions = JSON.parse(JSON.stringify(this.party.sessions || []));
    this._isDirty = false;
  }

  _addSession() {
    const newSession = { vibe: "", from_date: "", to_date: "" };
    this._draftSessions = [...this._draftSessions, newSession];
    this._isDirty = true;
  }

  /** @param {number} index */
  _removeSession(index) {
    this._draftSessions = this._draftSessions.filter((_, i) => i !== index);
    this._isDirty = true;
  }

  _handleSave() {
    this.service.updateParty({
      party_id: this.party.id,
      sessions: this._draftSessions,
    });
  }

  /**@param {any} e */
  _updatePlayer(e) {
    this.service.updateParty({
      party_id: this.party.id,
      media_player_id: e.target.value,
    });
  }

  /**
   * @param {number} index
   * @param {CustomEvent<import("../types/dto").VibeSession>} e
   */
  _handleVibeChange(index, e) {
    // Create a shallow copy of the draft array
    const updatedDraft = [...this._draftSessions];

    // Replace the session at the given index with the new full object
    updatedDraft[index] = e.detail;

    // Re-assign to trigger Lit's reactivity
    this._draftSessions = updatedDraft;
    this._isDirty = true;
  }

  render() {
    if (!this.party)
      return html`<div class="empty">No party data available.</div>`;

    return html`
      <div class="header">
        <div class="title-row">
          <h1>${this.party.name}</h1>
          ${this.party.active ? html`<span class="badge live">LIVE</span>` : ""}
        </div>
        <button
          class="btn ${this.party.active ? "danger" : "success"}"
          @click=${() => this.service.togglePartyActive(this.party.id)}
        >
          ${this.party.active ? "Stop AI DJ" : "Start AI DJ"}
        </button>
      </div>

      <div class="main-grid">
        <div class="editor-column">
          <section class="card">
            <h2>Vibe Timeline</h2>

            <div class="form-group">
              <label>Target Media Player (Music Assistant)</label>
              <select
                .value=${this.party.media_player_id || ""}
                @change=${this._updatePlayer}
              >
                <option value="">-- No Player Selected --</option>
                ${this._massPlayers.map(
                  (p) => html`
                    <option value=${p.entity_id}>${p.name}</option>
                  `,
                )}
              </select>
            </div>

            <div class="timeline">
              ${this._draftSessions.map(
                (session, index) => html`
                  <mass-ai-dj-vibe-card
                    .session=${session}
                    @remove=${() => this._removeSession(index)}
                    @${VIBE_CHANGE_EVENT}=${(
                      /** @type {CustomEvent<import("../types/dto").VibeSession>} */ e,
                    ) => this._handleVibeChange(index, e)}
                  ></mass-ai-dj-vibe-card>
                `,
              )}
              ${this._draftSessions.length === 0
                ? html`
                    <p class="placeholder">
                      No vibe sessions defined. Add one to start scheduling
                      moods.
                    </p>
                  `
                : ""}
            </div>

            <div class="action-bar">
              <button class="btn secondary" @click=${this._addSession}>
                + Add Vibe Slot
              </button>
              <div class="save-group">
                ${this._isDirty
                  ? html`
                      <button class="btn text" @click=${this._resetDraft}>
                        Cancel
                      </button>
                      <button class="btn success" @click=${this._handleSave}>
                        Save Timeline
                      </button>
                    `
                  : ""}
              </div>
            </div>
          </section>

          <div class="danger-zone">
            <h3>Danger Zone</h3>
            <button
              class="btn danger small"
              @click=${() => this.service.deleteParty(this.party.id)}
            >
              Delete Party Forever
            </button>
          </div>
        </div>

        <div class="history-column">
          <section class="card">
            <div class="section-header">
              <h2>History</h2>
              <button
                class="btn text danger"
                @click=${() => this.service.clearHistory(this.party.id)}
              >
                Clear
              </button>
            </div>
            <div class="history-list">
              ${this.party.history?.length
                ? this.party.history.map(
                    (song, idx) => html`
                      <div class="history-item">
                        <div class="song-meta">
                          <span class="song-title">${song.title}</span>
                          <span class="song-artist">${song.artist}</span>
                        </div>
                        <button
                          class="icon-btn"
                          @click=${() =>
                            this.service.removeFromHistory(this.party.id, idx)}
                        >
                          &times;
                        </button>
                      </div>
                    `,
                  )
                : html`<p class="placeholder">History is empty.</p>`}
            </div>
          </section>
        </div>
      </div>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }
      .main-grid {
        display: grid;
        grid-template-columns: 1fr 350px;
        gap: 24px;
      }
      @media (max-width: 800px) {
        .main-grid {
          grid-template-columns: 1fr;
        }
      }
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }
      .history-list {
        max-height: 500px;
        overflow-y: auto;
      }
      .history-item {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
      }
      .danger-zone {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px dashed var(--error-color);
      }
      .form-group {
        margin-bottom: 24px;
      }
      .timeline {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .action-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 24px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .save-group {
        display: flex;
        gap: 8px;
      }
      select {
        width: 100%;
        padding: 8px;
        border-radius: 4px;
        background: var(--card-background-color);
        color: var(--primary-text-color);
      }
    `,
  ];
}

customElements.define("mass-ai-dj-party", MassAiDjParty);
