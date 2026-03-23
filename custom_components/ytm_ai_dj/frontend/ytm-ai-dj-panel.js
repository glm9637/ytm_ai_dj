const LitElement = Object.getPrototypeOf(customElements.get("ha-panel-config"));
const { html, css } = LitElement;

class YtmAiDjPanel extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      narrow: { type: Boolean },
      route: { type: Object },
      panel: { type: Object },
      parties: { type: Array },
      selectedPartyId: { type: String },
      newPartyName: { type: String },
      sidebarOpen: { type: Boolean },
      massPlayers: { type: Array }
    };
  }

  static get styles() {
    return css`
      :host {
        display: block;
        height: 100vh;
        background-color: var(--primary-background-color, #fafafa);
        color: var(--primary-text-color, #212121);
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      }
      .container {
        display: flex;
        height: 100%;
      }
      .sidebar {
        width: 250px;
        border-right: 1px solid var(--divider-color, #e0e0e0);
        background: var(--card-background-color, #fff);
        padding: 16px;
        overflow-y: auto;
        transition: transform 0.3s ease;
      }
      .sidebar-overlay {
        display: none;
      }
      .menu-btn {
        background: transparent;
        color: var(--primary-text-color);
        font-size: 24px;
        padding: 4px 8px;
        margin-right: 12px;
        display: none;
        cursor: pointer;
        border: none;
      }
      @media (max-width: 768px) {
        .menu-btn {
          display: block;
        }
        .sidebar {
          position: fixed;
          top: 0;
          bottom: 0;
          left: 0;
          z-index: 100;
          transform: translateX(-100%);
          box-shadow: 2px 0 10px rgba(0,0,0,0.2);
        }
        .sidebar.open {
          transform: translateX(0);
        }
        .sidebar-overlay.open {
          display: block;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.5);
          z-index: 99;
        }
      }
      .main {
        flex: 1;
        padding: 24px;
        overflow-y: auto;
      }
      h2 {
        margin-top: 0;
        color: var(--primary-text-color);
      }
      .party-item {
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 8px;
        cursor: pointer;
        background: var(--secondary-background-color, #f5f5f5);
        transition: background 0.2s;
      }
      .party-item:hover {
        background: var(--primary-color, #03a9f4);
        color: white;
      }
      .party-item.selected {
        background: var(--primary-color, #03a9f4);
        color: white;
        font-weight: bold;
      }
      input[type="text"], input[type="datetime-local"] {
        width: 100%;
        padding: 10px;
        margin: 8px 0 16px;
        box-sizing: border-box;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        font-size: 16px;
      }
      button {
        background: var(--primary-color, #03a9f4);
        color: white;
        border: none;
        padding: 10px 16px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: background 0.2s;
      }
      button:hover {
        opacity: 0.9;
      }
      button:disabled {
        background: var(--disabled-text-color, #bdbdbd);
        cursor: not-allowed;
      }
      button.danger {
        background: var(--error-color, #f44336);
      }
      button.success {
        background: var(--success-color, #4caf50);
        font-size: 18px;
        padding: 12px 24px;
      }
      .card {
        background: var(--card-background-color, #fff);
        padding: 24px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 24px;
      }
      .form-group {
        margin-bottom: 16px;
      }
      .flex-row {
        display: flex;
        gap: 16px;
      }
      .flex-row > div {
        flex: 1;
      }
      .history-list {
        background: var(--secondary-background-color, #f5f5f5);
        border-radius: 8px;
        padding: 16px;
      }
      .history-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .history-item:last-child {
        border-bottom: none;
      }
      .delete-btn {
        background: transparent;
        color: var(--error-color, #f44336);
        padding: 4px 8px;
      }
      .delete-btn:hover {
        background: rgba(244, 67, 54, 0.1);
      }
      .song-info {
        display: flex;
        flex-direction: column;
      }
      .song-title {
        font-weight: bold;
      }
      .song-artist {
        font-size: 0.9em;
        color: var(--secondary-text-color, #757575);
      }
      .badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
        background: var(--success-color, #4caf50);
        color: white;
        margin-left: 8px;
      }
    `;
  }

constructor() {
    super();
    this.parties = [];
    this.massPlayers = [];
    this.selectedPartyId = null;
    this.newPartyName = "";
    this.sidebarOpen = window.innerWidth > 768;
    this._handleResize = () => {
      if (window.innerWidth > 768 && !this.sidebarOpen) {
        this.sidebarOpen = true;
      }
    };
  }

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener('resize', this._handleResize);
    this._pollingInterval = setInterval(() => {
      this.fetchParties();
    }, 10000); 
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('resize', this._handleResize);
    if (this._pollingInterval) {
      clearInterval(this._pollingInterval);
    }
  }

  firstUpdated() {
    this.fetchParties();
    this.fetchMassPlayers();
  }

  async fetchParties() {
    if (!this.hass) return;
    try {
      const parties = await this.hass.callWS({
        type: "ytm_ai_dj/parties/get"
      });
      this.parties = parties || [];
    } catch (err) {
      console.error("Failed to fetch parties:", err);
    }
  }

  async fetchMassPlayers() {
    const players = await this.hass.callWS({
      type: "ytm_ai_dj/players/get"
    });
    this.massPlayers = players || [];
  }

  async createParty() {
    if (!this.newPartyName.trim() || !this.hass) return;
    try {
      const party = await this.hass.callWS({
        type: "ytm_ai_dj/parties/create",
        name: this.newPartyName
      });
      this.newPartyName = "";
      await this.fetchParties();
      this.selectedPartyId = party.id;
    } catch (err) {
      console.error("Failed to create party:", err);
    }
  }

  async updateParty(partyId, updates) {
    if (!this.hass) return;
    try {
      const updatedParty = await this.hass.callWS({
        type: "ytm_ai_dj/parties/update",
        party_id: partyId,
        ...updates
      });
      
      const index = this.parties.findIndex(p => p.id === partyId);
      if (index !== -1) {
        this.parties[index] = updatedParty;
        this.requestUpdate();
      }
    } catch (err) {
      console.error("Failed to update party:", err);
    }
  }

  async deleteParty(partyId) {
    if (!this.hass || !confirm("Are you sure you want to delete this party?")) return;
    try {
      await this.hass.callWS({
        type: "ytm_ai_dj/parties/delete",
        party_id: partyId
      });
      if (this.selectedPartyId === partyId) {
        this.selectedPartyId = null;
      }
      await this.fetchParties();
    } catch (err) {
      console.error("Failed to delete party:", err);
    }
  }

  async togglePartyActive(party) {
    const updates = { active: !party.active };
    if (!party.active && !party.start_time) {
      // Auto-populate start time to now() if starting for the first time
      const now = new Date();
      // Format as YYYY-MM-DDThh:mm (datetime-local format)
      now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
      updates.start_time = now.toISOString().slice(0, 16);
    }
    await this.updateParty(party.id, updates);
  }

  async removeHistoryItem(partyId, index) {
    if (!this.hass) return;
    try {
      const updatedParty = await this.hass.callWS({
        type: "ytm_ai_dj/history/delete",
        party_id: partyId,
        index: index
      });
      const partyIndex = this.parties.findIndex(p => p.id === partyId);
      if (partyIndex !== -1) {
        this.parties[partyIndex] = updatedParty;
        this.requestUpdate();
      }
    } catch (err) {
      console.error("Failed to remove history item:", err);
    }
  }

  async clearHistory(partyId) {
    if (!this.hass || !confirm("Clear all history?")) return;
    try {
      const updatedParty = await this.hass.callWS({
        type: "ytm_ai_dj/history/clear",
        party_id: partyId
      });
      const partyIndex = this.parties.findIndex(p => p.id === partyId);
      if (partyIndex !== -1) {
        this.parties[partyIndex] = updatedParty;
        this.requestUpdate();
      }
    } catch (err) {
      console.error("Failed to clear history:", err);
    }
  }

  renderSidebar() {
    return html`
      <div class="sidebar-overlay ${this.sidebarOpen ? 'open' : ''}" @click=${() => this.sidebarOpen = false}></div>
      <div class="sidebar ${this.sidebarOpen ? 'open' : ''}">
        <h2>AI DJ Parties</h2>
        <div class="form-group">
          <input 
            type="text" 
            placeholder="New Party Name" 
            .value=${this.newPartyName}
            @input=${e => this.newPartyName = e.target.value}
            @keypress=${e => e.key === 'Enter' && this.createParty()}
          >
          <button @click=${this.createParty} style="width: 100%">Create Party</button>
        </div>
        
        <div style="margin-top: 24px;">
          ${this.parties.map(party => html`
            <div 
              class="party-item ${this.selectedPartyId === party.id ? 'selected' : ''}"
              @click=${() => {
                this.selectedPartyId = party.id;
                if (window.innerWidth <= 768) this.sidebarOpen = false;
              }}
            >
              ${party.name}
              ${party.active ? html`<span class="badge">Active</span>` : ''}
            </div>
          `)}
        </div>
      </div>
    `;
  }

  renderMain() {
    const party = this.parties.find(p => p.id === this.selectedPartyId);
    
    if (!party) {
      return html`
        <div class="main" style="display: flex; flex-direction: column; align-items: center; justify-content: center; color: gray;">
          <button class="menu-btn" style="margin-bottom: 24px; display: inline-block; font-size: 18px;" @click=${() => this.sidebarOpen = true}>☰ Open Menu</button>
          <h2>Select or create a party to manage the AI DJ</h2>
        </div>
      `;
    }

    return html`
      <div class="main">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
          <div style="display: flex; align-items: center;">
            <button class="menu-btn" @click=${() => this.sidebarOpen = !this.sidebarOpen}>☰</button>
            <h2 style="margin: 0">${party.name}</h2>
          </div>
          <button class="danger" @click=${() => this.deleteParty(party.id)}>Delete Party</button>
        </div>

        <div class="card">
          <div class="form-group">
            <label><strong>Target Speaker</strong></label>
            <select 
              style="width: 100%; padding: 10px; margin-top: 8px; border-radius: 4px;"
              @change=${e => this.updateParty(party.id, { media_player_id: e.target.value })}
            >
              <option value="" ?selected=${!party.media_player_id}>Select a Speaker</option>
              ${this.massPlayers.map(player => html`
                <option value="${player.entity_id}" ?selected=${party.media_player_id === player.entity_id}>${player.name}</option>
              `)}
            </select>
          </div>
        </div>

        <div class="card">
          <div class="form-group">
            <label><strong>Vibe / Prompt</strong></label>
            <input 
              type="text" 
              placeholder="e.g. Upbeat 90s dance tracks, high energy" 
              .value=${party.vibe || ''}
              @change=${e => this.updateParty(party.id, { vibe: e.target.value })}
            >
            <small style="color: gray;">This instructs the AI DJ on what mood to generate.</small>
          </div>

          <div class="flex-row">
            <div>
              <label><strong>Start Time</strong></label>
              <input 
                type="datetime-local" 
                .value=${party.start_time || ''}
                @change=${e => this.updateParty(party.id, { start_time: e.target.value })}
              >
            </div>
            <div>
              <label><strong>Planned End Time</strong></label>
              <input 
                type="datetime-local" 
                .value=${party.end_time || ''}
                @change=${e => this.updateParty(party.id, { end_time: e.target.value })}
              >
            </div>
          </div>
        </div>

        <div class="card" style="display: flex; justify-content: space-between; align-items: center; background: ${party.active ? 'var(--ha-color-green-20, #0a3a1d)' : 'var(--card-background-color)'}">
          <div>
            <h3 style="margin: 0 0 8px 0;">DJ Status: ${party.active ? 'Active' : 'Stopped'}</h3>
            <p style="margin: 0; color: gray;">When active, the AI DJ monitors your YouTube Music queue.</p>
          </div>
          <button 
            class="${party.active ? 'danger' : 'success'}" 
            @click=${() => this.togglePartyActive(party)}
          >
            ${party.active ? 'Stop AI DJ' : 'Start AI DJ'}
          </button>
        </div>

        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <h3 style="margin: 0">Play History</h3>
            <button @click=${() => this.clearHistory(party.id)}>Clear History</button>
          </div>
          
          <div class="history-list">
            ${(!party.history || party.history.length === 0) ? html`<div style="color: gray; text-align: center;">No songs played yet.</div>` : ''}
            ${(party.history || []).map((song, index) => html`
              <div class="history-item">
                <div class="song-info">
                  <span class="song-title">${song.title}</span>
                  <span class="song-artist">${song.artist}</span>
                </div>
                <button class="delete-btn" @click=${() => this.removeHistoryItem(party.id, index)}>
                  ✕
                </button>
              </div>
            `)}
          </div>
        </div>
      </div>
    `;
  }

  render() {
    return html`
      <div class="container">
        ${this.renderSidebar()}
        ${this.renderMain()}
      </div>
    `;
  }
}

customElements.define("ytm-ai-dj-panel", YtmAiDjPanel);
