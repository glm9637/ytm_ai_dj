import { LitElement, html, css } from "https://unpkg.com/lit@3.3.2/index.js?module";

import { sharedStyles } from "./shared-style.js";
import { ApiService } from "./services/api-service.js";
import { DataService } from "./services/data-service.js";
import "./components/sidebar.js";
import "./components/party.js";

class MassAiDjPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      _selectedParty: { type: Object },
    };
  }

  static get styles() {
    return [
      sharedStyles,
      css`
        :host {
          display: block;
          height: calc(100vh - var(--header-height, 56px));
          background-color: var(--primary-background-color);
          box-sizing: border-box;
        }
        .app-container {
          display: flex;
          flex-direction: row;
          height: 100%;
          width: 100%;
          overflow: hidden;
        }
        .content {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          background: var(--primary-background-color);
        }
        .welcome {
          display: flex;
          flex-direction: column;
          height: 100%;
          align-items: center;
          justify-content: center;
          color: var(--secondary-text-color);
          text-align: center;
        }
        .welcome h2 {
          color: var(--secondary-text-color);
          margin-bottom: 8px;
        }
      `
    ];
  }

  constructor() {
    super();
    const api = new ApiService();
    this.service = new DataService(api);
    /**
     * @type {import('./types/dto').Party | null}
     */
    this._selectedParty = null;

    /**
     * @type {import('./types/home-assistant.js').HomeAssistant | null}
     */
    this.hass = null;
  }

  /** @type {(() => void)[]} */
  #unsubs = [];

  connectedCallback() {
    super.connectedCallback();
    this.#unsubs = [
      this.service.registerSelectedPartyCallback((p) => {
        this._selectedParty = p;
      }),
    ];

    this.service.fetchParties();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this.#unsubs.forEach((unsub) => unsub());
  }

  /**
   *
   * @param {any} changedProps
   */
  updated(changedProps) {
    if (changedProps.has("hass") && this.hass) {
      this.service.updateHass(this.hass);
    }
  }

  firstUpdated() {
    this.service.fetchParties();
  }

  render() {
    if (!this.hass) {
      return html`<ha-circular-progress active></ha-circular-progress>`;
    }

    const showSidebar = !this.narrow || !this._selectedParty;
    const showContent = !this.narrow || this._selectedParty;

    return html`
      <div class="app-container">
        ${showSidebar
          ? html`<mass-ai-dj-sidebar .service=${this.service}></mass-ai-dj-sidebar>`
          : ""}

        ${showContent
          ? html`
              <main class="content">
                ${this.narrow && this._selectedParty
                  ? html`<button class="btn text" style="margin-bottom: 16px; display: flex; align-items: center;" @click=${() => this.service.selectParty(null)}>
                      <ha-icon icon="mdi:arrow-left" style="margin-right: 8px;"></ha-icon> Back to Parties
                    </button>`
                  : ""}
                ${this._selectedParty
                  ? html`<mass-ai-dj-party
                      .service=${this.service}
                      .party=${this._selectedParty}
                    ></mass-ai-dj-party>`
                  : html`<div class="welcome">
                      <h2>AI DJ</h2>
                      <p>Select a party from the sidebar to get started.</p>
                    </div>`}
              </main>
            `
          : ""}
      </div>
    `;
  }
}

customElements.define("mass-ai-dj-panel", MassAiDjPanel);
