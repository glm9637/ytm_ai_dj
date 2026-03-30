import {
  LitElement,
  html,
  css,
} from "https://unpkg.com/lit@3.3.2/index.js?module";
import { sharedStyles } from "../shared-style.js";

/** @typedef {import('../services/data-service.js').DataService} DataService */
/** @typedef {import('../types/dto').Party} Party */

export class MassAiDjSidebar extends LitElement {
  static get properties() {
    return {
      service: { type: Object },
      _parties: { type: Array },
      _selectedPartyId: { type: String },
      _newPartyName: { type: String },
      hass: { type: Object },
      narrow: { type: Boolean },
    };
  }

  constructor() {
    super();

    /** @type {DataService} */
    this.service;

    /** @type {Party[]} @private */
    this._parties = [];

    /** @type {string|null} @private */
    this._selectedPartyId = null;

    /** @type {string} @private */
    this._newPartyName = "";
  }

  /** @type {(() => void)[]} */
  #unsubs = [];

  connectedCallback() {
    super.connectedCallback();

    this.#unsubs = [
      this.service.registerPartyCallback((p) => {
        this._parties = p;
      }),
      this.service.registerSelectedPartyCallback((p) => {
        this._selectedPartyId = p?.id || null;
      }),
    ];
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#unsubs.forEach((unsub) => unsub());
  }

  /** @param {KeyboardEvent} e */
  _handleKeyDown(e) {
    if (e.key === "Enter") {
      this._onCreate();
    }
  }

  async _onCreate() {
    const name = this._newPartyName.trim();
    if (!name) return;

    await this.service.createParty({ name });
    this._newPartyName = "";
  }

  render() {
    return html`
      <div class="sidebar-container">
        <div class="header" style="display: flex; align-items: center;">
          <ha-menu-button .hass=${this.hass} .narrow=${this.narrow}></ha-menu-button>
          <h2 style="margin: 0; margin-left: 8px;">AI DJ Parties</h2>
        </div>

        <div class="create-section">
          <input
            type="text"
            placeholder="New Party Name..."
            .value=${this._newPartyName}
            @input=${(/** @type {{ target: { value: any; }; }} */ e) =>
              (this._newPartyName = e.target.value)}
            @keydown=${this._handleKeyDown}
          />
          <button
            class="btn"
            ?disabled=${!this._newPartyName.trim()}
            @click=${this._onCreate}
          >
            Add
          </button>
        </div>

        <div class="party-list">
          ${this._parties.length === 0
            ? html` <div class="empty-msg">No parties created yet.</div> `
            : ""}
          ${this._parties.map(
            (party) => html`
              <div
                class="party-item ${this._selectedPartyId === party.id
                  ? "selected"
                  : ""}"
                @click=${() => this.service.selectParty(party.id)}
              >
                <div class="party-info">
                  <span class="name">${party.name}</span>
                  <span class="vibe-count"
                    >${party.sessions?.length || 0} Vibes</span
                  >
                </div>
                ${party.active
                  ? html`<div
                      class="status-indicator live"
                      title="Active"
                    ></div>`
                  : ""}
              </div>
            `,
          )}
        </div>
      </div>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        height: 100%;
        background: var(--card-background-color, #fafafa);
        border-right: 1px solid var(--divider-color, #e0e0e0);
        width: 300px;
        flex-shrink: 0;
      }
      @media (max-width: 800px) {
      :host {
        width: 100%;
        border-right: none;
      }
    }
    .sidebar-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .header {
      padding: 16px;
      border-bottom: 1px solid var(--divider-color);
    }
    h2 {
      margin: 0;
      font-size: 1.1em;
    }

    /* Create Form Styles */
    .create-section {
      padding: 16px;
      display: flex;
      gap: 8px;
      background: var(--secondary-background-color);
      border-bottom: 1px solid var(--divider-color);
    }
    input {
      flex: 1;
      min-width: 0;
    }
    
    /* List Styles */
    .party-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px 0;
    }
    .party-item {
      padding: 12px 16px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.2s;
      border-left: 4px solid transparent;
    }
    .party-item:hover {
      background: var(--secondary-background-color);
    }
    .party-item.selected {
      background: rgba(var(--rgb-primary-color), 0.1);
      border-left-color: var(--primary-color);
    }
    .party-info {
      display: flex;
      flex-direction: column;
    }
    .name {
      font-weight: 500;
    }
    .vibe-count {
      font-size: 0.8em;
      color: var(--secondary-text-color);
    }
    .empty-msg {
      padding: 20px;
      text-align: center;
      color: var(--secondary-text-color);
      font-style: italic;
    }

    /* Status Dot */
    .status-indicator.live {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #4caf50;
      box-shadow: 0 0 5px #4caf50;
    }
  `];
}

customElements.define("mass-ai-dj-sidebar", MassAiDjSidebar);
