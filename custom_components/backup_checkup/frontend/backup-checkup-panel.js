const TEXT = {
  en: {
    dashboard: "Backup overview",
    subtitle: "Live status of your Home Assistant backups",
    healthy: "Backup protection is healthy",
    attention: "Backup protection needs attention",
    unavailable: "Backup data is not available yet",
    healthScore: "Health score",
    status: "Current status",
    recommendation: "Recommendation",
    latestBackup: "Latest backup",
    backupSize: "Latest backup size",
    storedBackups: "Stored backups",
    integrity: "Integrity",
    problems: "Active problems",
    noProblems: "No active backup problems.",
    storage: "Storage locations",
    noStorage: "No storage information is available.",
    backups: "backups",
    lastBackup: "Latest backup",
    refresh: "Refresh",
    verify: "Verify latest backup",
    settings: "Settings",
    updated: "Updated",
    actionFailed: "The action could not be completed.",
    overviewTab: "Overview",
    logTab: "Live log",
    logTitle: "BackupCheckup live log",
    searchLogs: "Search log entries",
    noLogs: "No matching log entries are available.",
    loggingDisabled: "Detailed live logging is disabled in the integration options.",
    live: "Live",
    activityActions: {
      verification_prepare: "Preparing integrity verification",
      storage_copy_prepare: "Preparing storage copy",
      backup_download: "Downloading backup",
      backup_extract: "Extracting backup",
      encrypted_backup_extract: "Extracting encrypted backup",
      database_read: "Reading and checking database",
      temporary_data_cleanup: "Removing temporary verification data",
      inventory_refresh: "Refreshing backup inventory",
      backup_manager_read: "Reading backup manager",
      integrity_check: "Running integrity verification",
      integrity_check_request: "Processing verification request",
      integrity_result_persist: "Saving verification result",
      health_state: "Updating backup health",
      notification_send: "Sending notification",
      notification_processing: "Processing notifications",
      config_entry_setup: "Starting integration",
      entity_platform_setup: "Setting up entities",
      repair_issue_sync: "Synchronizing repair notices",
      first_refresh: "Completing first inventory refresh",
      coordinator_shutdown: "Stopping integration",
      integrity_state_load: "Loading saved verification state",
      integrity_check_schedule: "Scheduling automatic verification",
      integrity_background_task: "Monitoring background verification",
      post_verification_refresh: "Refreshing status after verification",
      service_refresh: "Running manual refresh",
      service_verify_latest_backup: "Starting manual backup verification",
      service_test_notification: "Testing notification",
      panel_setup: "Setting up sidebar panel",
    },
    activityOutcomes: {
      started: "started", completed: "completed", changed: "in progress",
      skipped: "skipped", failed: "failed", cancelled: "cancelled",
    },
  },
  de: {
    dashboard: "Backup-Übersicht",
    subtitle: "Live-Status deiner Home-Assistant-Backups",
    healthy: "Der Backup-Schutz ist in Ordnung",
    attention: "Der Backup-Schutz benötigt Aufmerksamkeit",
    unavailable: "Backup-Daten sind noch nicht verfügbar",
    healthScore: "Gesundheitswert",
    status: "Aktueller Status",
    recommendation: "Empfehlung",
    latestBackup: "Letztes Backup",
    backupSize: "Größe des letzten Backups",
    storedBackups: "Gespeicherte Backups",
    integrity: "Integrität",
    problems: "Aktive Probleme",
    noProblems: "Keine aktiven Backup-Probleme.",
    storage: "Speicherorte",
    noStorage: "Keine Informationen zu Speicherorten verfügbar.",
    backups: "Backups",
    lastBackup: "Letztes Backup",
    refresh: "Aktualisieren",
    verify: "Letztes Backup prüfen",
    settings: "Einstellungen",
    updated: "Aktualisiert",
    actionFailed: "Die Aktion konnte nicht ausgeführt werden.",
    overviewTab: "Übersicht",
    logTab: "Protokoll",
    logTitle: "BackupCheckup Live-Protokoll",
    searchLogs: "Protokolle durchsuchen",
    noLogs: "Keine passenden Protokolleinträge vorhanden.",
    loggingDisabled: "Das ausführliche Live-Protokoll ist in den Integrationsoptionen deaktiviert.",
    live: "Live",
    activityActions: {
      verification_prepare: "Integritätsprüfung wird vorbereitet",
      storage_copy_prepare: "Speicherkopie wird vorbereitet",
      backup_download: "Backup wird heruntergeladen",
      backup_extract: "Backup wird extrahiert",
      encrypted_backup_extract: "Verschlüsseltes Backup wird extrahiert",
      database_read: "Datenbank wird gelesen und geprüft",
      temporary_data_cleanup: "Temporäre Prüfdaten werden entfernt",
      inventory_refresh: "Backup-Inventar wird aktualisiert",
      backup_manager_read: "Backup-Manager wird gelesen",
      integrity_check: "Integritätsprüfung wird ausgeführt",
      integrity_check_request: "Prüfauftrag wird verarbeitet",
      integrity_result_persist: "Prüfergebnis wird gespeichert",
      health_state: "Backup-Zustand wird aktualisiert",
      notification_send: "Benachrichtigung wird gesendet",
      notification_processing: "Benachrichtigungen werden verarbeitet",
      config_entry_setup: "Integration wird gestartet",
      entity_platform_setup: "Entitäten werden eingerichtet",
      repair_issue_sync: "Reparaturhinweise werden synchronisiert",
      first_refresh: "Erste Inventarabfrage wird abgeschlossen",
      coordinator_shutdown: "Integration wird beendet",
      integrity_state_load: "Gespeicherter Prüfstatus wird geladen",
      integrity_check_schedule: "Automatische Prüfung wird eingeplant",
      integrity_background_task: "Hintergrundprüfung wird überwacht",
      post_verification_refresh: "Status wird nach der Prüfung aktualisiert",
      service_refresh: "Manuelle Aktualisierung wird ausgeführt",
      service_verify_latest_backup: "Manuelle Backup-Prüfung wird gestartet",
      service_test_notification: "Benachrichtigung wird getestet",
      panel_setup: "Seitenleistenansicht wird eingerichtet",
    },
    activityOutcomes: {
      started: "gestartet", completed: "abgeschlossen", changed: "läuft",
      skipped: "übersprungen", failed: "fehlgeschlagen", cancelled: "abgebrochen",
    },
  },
  da: {
    dashboard: "Backupoversigt", subtitle: "Livestatus for dine Home Assistant-backups",
    healthy: "Backupbeskyttelsen er i orden", attention: "Backupbeskyttelsen kræver opmærksomhed",
    unavailable: "Backupdata er endnu ikke tilgængelige", healthScore: "Sundhedsscore",
    status: "Aktuel status", recommendation: "Anbefaling", latestBackup: "Seneste backup",
    backupSize: "Størrelse på seneste backup", storedBackups: "Gemte backups", integrity: "Integritet",
    problems: "Aktive problemer", noProblems: "Ingen aktive backupproblemer.", storage: "Lagerplaceringer",
    noStorage: "Ingen lageroplysninger er tilgængelige.", backups: "backups", lastBackup: "Seneste backup",
    refresh: "Opdater", verify: "Kontrollér seneste backup", settings: "Indstillinger", updated: "Opdateret",
    actionFailed: "Handlingen kunne ikke gennemføres.",
  },
  es: {
    dashboard: "Resumen de copias", subtitle: "Estado en vivo de tus copias de Home Assistant",
    healthy: "La protección de copias está correcta", attention: "La protección de copias requiere atención",
    unavailable: "Los datos de copia aún no están disponibles", healthScore: "Puntuación de salud",
    status: "Estado actual", recommendation: "Recomendación", latestBackup: "Última copia",
    backupSize: "Tamaño de la última copia", storedBackups: "Copias guardadas", integrity: "Integridad",
    problems: "Problemas activos", noProblems: "No hay problemas activos.", storage: "Ubicaciones de almacenamiento",
    noStorage: "No hay información de almacenamiento.", backups: "copias", lastBackup: "Última copia",
    refresh: "Actualizar", verify: "Verificar última copia", settings: "Ajustes", updated: "Actualizado",
    actionFailed: "No se pudo completar la acción.",
  },
  fr: {
    dashboard: "Vue d’ensemble des sauvegardes", subtitle: "État en direct des sauvegardes Home Assistant",
    healthy: "La protection des sauvegardes est correcte", attention: "La protection des sauvegardes requiert votre attention",
    unavailable: "Les données de sauvegarde ne sont pas encore disponibles", healthScore: "Score de santé",
    status: "État actuel", recommendation: "Recommandation", latestBackup: "Dernière sauvegarde",
    backupSize: "Taille de la dernière sauvegarde", storedBackups: "Sauvegardes stockées", integrity: "Intégrité",
    problems: "Problèmes actifs", noProblems: "Aucun problème de sauvegarde actif.", storage: "Emplacements de stockage",
    noStorage: "Aucune information de stockage disponible.", backups: "sauvegardes", lastBackup: "Dernière sauvegarde",
    refresh: "Actualiser", verify: "Vérifier la dernière sauvegarde", settings: "Paramètres", updated: "Actualisé",
    actionFailed: "L’action n’a pas pu être effectuée.",
  },
  it: {
    dashboard: "Panoramica backup", subtitle: "Stato in tempo reale dei backup di Home Assistant",
    healthy: "La protezione dei backup è corretta", attention: "La protezione dei backup richiede attenzione",
    unavailable: "I dati dei backup non sono ancora disponibili", healthScore: "Punteggio di salute",
    status: "Stato attuale", recommendation: "Raccomandazione", latestBackup: "Ultimo backup",
    backupSize: "Dimensione ultimo backup", storedBackups: "Backup archiviati", integrity: "Integrità",
    problems: "Problemi attivi", noProblems: "Nessun problema di backup attivo.", storage: "Posizioni di archiviazione",
    noStorage: "Nessuna informazione di archiviazione disponibile.", backups: "backup", lastBackup: "Ultimo backup",
    refresh: "Aggiorna", verify: "Verifica ultimo backup", settings: "Impostazioni", updated: "Aggiornato",
    actionFailed: "Impossibile completare l’azione.",
  },
  nl: {
    dashboard: "Back-upoverzicht", subtitle: "Livestatus van je Home Assistant-back-ups",
    healthy: "De back-upbeveiliging is in orde", attention: "De back-upbeveiliging vereist aandacht",
    unavailable: "Back-upgegevens zijn nog niet beschikbaar", healthScore: "Gezondheidsscore",
    status: "Huidige status", recommendation: "Aanbeveling", latestBackup: "Laatste back-up",
    backupSize: "Grootte laatste back-up", storedBackups: "Opgeslagen back-ups", integrity: "Integriteit",
    problems: "Actieve problemen", noProblems: "Geen actieve back-upproblemen.", storage: "Opslaglocaties",
    noStorage: "Geen opslaginformatie beschikbaar.", backups: "back-ups", lastBackup: "Laatste back-up",
    refresh: "Vernieuwen", verify: "Laatste back-up controleren", settings: "Instellingen", updated: "Bijgewerkt",
    actionFailed: "De actie kon niet worden voltooid.",
  },
  pl: {
    dashboard: "Przegląd kopii", subtitle: "Bieżący stan kopii zapasowych Home Assistant",
    healthy: "Ochrona kopii zapasowych działa prawidłowo", attention: "Ochrona kopii zapasowych wymaga uwagi",
    unavailable: "Dane kopii zapasowych nie są jeszcze dostępne", healthScore: "Ocena kondycji",
    status: "Bieżący stan", recommendation: "Zalecenie", latestBackup: "Najnowsza kopia",
    backupSize: "Rozmiar najnowszej kopii", storedBackups: "Zapisane kopie", integrity: "Integralność",
    problems: "Aktywne problemy", noProblems: "Brak aktywnych problemów z kopiami.", storage: "Lokalizacje przechowywania",
    noStorage: "Brak informacji o lokalizacjach.", backups: "kopii", lastBackup: "Najnowsza kopia",
    refresh: "Odśwież", verify: "Sprawdź najnowszą kopię", settings: "Ustawienia", updated: "Zaktualizowano",
    actionFailed: "Nie udało się wykonać działania.",
  },
  sv: {
    dashboard: "Säkerhetskopieöversikt", subtitle: "Livestatus för dina Home Assistant-säkerhetskopior",
    healthy: "Säkerhetskopieringen fungerar korrekt", attention: "Säkerhetskopieringen behöver uppmärksamhet",
    unavailable: "Säkerhetskopiedata är ännu inte tillgängliga", healthScore: "Hälsopoäng",
    status: "Aktuell status", recommendation: "Rekommendation", latestBackup: "Senaste säkerhetskopian",
    backupSize: "Storlek på senaste säkerhetskopian", storedBackups: "Lagrade säkerhetskopior", integrity: "Integritet",
    problems: "Aktiva problem", noProblems: "Inga aktiva säkerhetskopieringsproblem.", storage: "Lagringsplatser",
    noStorage: "Ingen lagringsinformation är tillgänglig.", backups: "säkerhetskopior", lastBackup: "Senaste säkerhetskopian",
    refresh: "Uppdatera", verify: "Kontrollera senaste säkerhetskopian", settings: "Inställningar", updated: "Uppdaterad",
    actionFailed: "Åtgärden kunde inte slutföras.",
  },
};

const DEFAULT_ENTITIES = {
  status: "sensor.backup_checkup_status",
  health_score: "sensor.backup_checkup_health_score",
  recommendation: "sensor.backup_checkup_recommendation",
  stored_backups: "sensor.backup_checkup_stored_backups",
  latest_backup_age: "sensor.backup_checkup_latest_backup_age",
  latest_backup_size: "sensor.backup_checkup_latest_backup_size",
  integrity_status: "sensor.backup_checkup_integrity_status",
  problem: "binary_sensor.backup_checkup_problem",
  verify: "button.backup_checkup_verify_latest_backup",
  refresh: "button.backup_checkup_refresh",
  activity_log: "sensor.backup_checkup_activity_log",
};

class BackupCheckupPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._panel = undefined;
    this._renderPending = false;
    this._busy = new Set();
    this._activeTab = "overview";
    this._logSearch = "";
  }

  set hass(value) {
    this._hass = value;
    this._scheduleRender();
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    this._panel = value;
    this._scheduleRender();
  }

  get panel() {
    return this._panel;
  }

  set narrow(value) {
    this.toggleAttribute("narrow", Boolean(value));
  }

  set route(value) {
    this._route = value;
  }

  connectedCallback() {
    this._scheduleRender();
  }

  _scheduleRender() {
    if (this._renderPending || !this.isConnected) return;
    this._renderPending = true;
    requestAnimationFrame(() => {
      this._renderPending = false;
      this._render();
    });
  }

  _language() {
    const selected = String(
      this._hass?.locale?.language || this._hass?.language || document.documentElement.lang || "en"
    ).toLowerCase().split("-")[0];
    return TEXT[selected] ? selected : "en";
  }

  _text() {
    const selected = TEXT[this._language()];
    return {
      ...TEXT.en,
      ...selected,
      activityActions: { ...TEXT.en.activityActions, ...selected.activityActions },
      activityOutcomes: { ...TEXT.en.activityOutcomes, ...selected.activityOutcomes },
    };
  }

  _entities() {
    const configured = this._panel?.config?.entities;
    return configured ? { ...DEFAULT_ENTITIES, ...configured } : DEFAULT_ENTITIES;
  }

  _state(key) {
    const entityId = this._entities()[key];
    return entityId ? this._hass?.states?.[entityId] : undefined;
  }

  _formatState(state) {
    if (!state || ["unknown", "unavailable"].includes(state.state)) return "—";
    try {
      if (typeof this._hass?.formatEntityState === "function") {
        return this._hass.formatEntityState(state);
      }
    } catch (_error) {
      // Fall back to the raw value if a frontend formatter is unavailable.
    }
    const unit = state.attributes?.unit_of_measurement;
    const suffix = unit ? ` ${unit}` : "";
    return `${state.state}${suffix}`;
  }

  _localizedStatus(code) {
    if (!code) return "—";
    const key = `component.backup_checkup.entity.sensor.status.state.${code}`;
    return this._hass?.localize?.(key) || this._humanize(code);
  }

  _humanize(value) {
    return String(value || "—")
      .replaceAll("_", " ")
      .replace(/^./, (letter) => letter.toUpperCase());
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _tone(status, hasProblem) {
    if (!status || ["unknown", "unavailable"].includes(status)) return "neutral";
    return status === "ok" && !hasProblem ? "good" : "danger";
  }

  _date(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(this._language(), {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  }

  _storageRows(agents, text) {
    if (!agents.length) return `<div class="empty">${this._escape(text.noStorage)}</div>`;
    return agents.map((agent) => {
      const tone = this._storageTone(agent);
      const latest = agent.latest_backup ? this._date(agent.latest_backup) : "—";
      return `
        <div class="storage-row">
          <div class="storage-icon ${tone}"><ha-icon icon="mdi:database"></ha-icon></div>
          <div class="storage-copy">
            <strong>${this._escape(agent.storage_name || agent.storage_reference || "—")}</strong>
            <span>${this._escape(text.lastBackup)}: ${this._escape(latest)}</span>
          </div>
          <div class="storage-count">${this._escape(agent.backup_count ?? 0)} <span>${this._escape(text.backups)}</span></div>
        </div>`;
    }).join("");
  }

  _storageTone(agent) {
    if (agent.error) return "danger";
    return agent.stale ? "warning" : "good";
  }

  _problemRows(problems, text) {
    if (!problems.length) {
      return `<div class="empty success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.noProblems)}</div>`;
    }
    return problems.map((problem) => `
      <div class="problem-row">
        <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
        <span>${this._escape(this._localizedStatus(problem))}</span>
      </div>`).join("");
  }

  _metric(icon, label, value, tone = "") {
    return `
      <article class="metric ${tone}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><span>${this._escape(label)}</span><strong>${this._escape(value)}</strong></div>
      </article>`;
  }

  _heroMessage(tone, text) {
    if (tone === "good") return text.healthy;
    if (tone === "danger") return text.attention;
    return text.unavailable;
  }

  _integrityTone(integrity) {
    if (!integrity) return "";
    if (integrity.state === "valid") return "good";
    if (["valid_with_warnings", "not_checked", "checking"].includes(integrity.state)) {
      return "warning";
    }
    return "danger";
  }

  _renderModel() {
    const text = this._text();
    const status = this._state("status");
    const problem = this._state("problem");
    const scoreState = this._state("health_score");
    const recommendation = this._state("recommendation");
    const stored = this._state("stored_backups");
    const latestAge = this._state("latest_backup_age");
    const latestSize = this._state("latest_backup_size");
    const integrity = this._state("integrity_status");
    const activity = this._state("activity_log");
    const scoreValue = Number(scoreState?.state);
    const score = Number.isFinite(scoreValue)
      ? Math.min(100, Math.max(0, scoreValue))
      : null;
    const hasProblem = problem?.state === "on" || Boolean(status?.attributes?.problem);
    const tone = this._tone(status?.state, hasProblem);
    return {
      text,
      stored,
      latestAge,
      latestSize,
      score,
      tone,
      problems: Array.isArray(status?.attributes?.active_problems)
        ? status.attributes.active_problems : [],
      agents: Array.isArray(stored?.attributes?.agents) ? stored.attributes.agents : [],
      updated: status?.attributes?.checked_at || status?.last_updated,
      heroMessage: this._heroMessage(tone, text),
      statusLabel: this._formatState(status),
      recommendationLabel: this._formatState(recommendation),
      integrityLabel: this._formatState(integrity),
      integrityTone: this._integrityTone(integrity),
      isAdmin: Boolean(this._hass.user?.is_admin),
      verifyState: this._state("verify"),
      refreshState: this._state("refresh"),
      activityEntries: Array.isArray(activity?.attributes?.entries)
        ? activity.attributes.entries : [],
      activityEnabled: Boolean(activity?.attributes?.enabled),
    };
  }

  _settingsButton(isAdmin, text) {
    if (!isAdmin) return "";
    return `<button class="icon-button" data-nav="settings" title="${this._escape(text.settings)}">
      <ha-icon icon="mdi:cog-outline"></ha-icon>
    </button>`;
  }

  _actionFooter(model) {
    if (!model.isAdmin) return "";
    const refreshDisabled = this._buttonDisabled(model.refreshState, "refresh")
      ? "disabled" : "";
    const verifyDisabled = this._buttonDisabled(model.verifyState, "verify")
      ? "disabled" : "";
    return `<footer>
      <button class="action secondary" data-action="refresh" ${refreshDisabled}>
        <ha-icon icon="mdi:refresh"></ha-icon>${this._escape(model.text.refresh)}
      </button>
      <button class="action primary" data-action="verify" ${verifyDisabled}>
        <ha-icon icon="mdi:shield-search"></ha-icon>${this._escape(model.text.verify)}
      </button>
    </footer>`;
  }

  _tabs(text) {
    const overviewActive = this._activeTab === "overview" ? "active" : "";
    const logsActive = this._activeTab === "logs" ? "active" : "";
    return `<nav class="tabs" aria-label="BackupCheckup">
      <button class="tab ${overviewActive}" data-tab="overview">
        <ha-icon icon="mdi:view-dashboard-outline"></ha-icon>${this._escape(text.overviewTab)}
      </button>
      <button class="tab ${logsActive}" data-tab="logs">
        <ha-icon icon="mdi:text-box-search-outline"></ha-icon>${this._escape(text.logTab)}
      </button>
    </nav>`;
  }

  _overviewTemplate(model) {
    return `<section class="hero ${model.tone}">
      <div class="hero-copy">
        <div class="eyebrow"><span></span>${this._escape(model.statusLabel)}</div>
        <h2>${this._escape(model.heroMessage)}</h2>
        <p>${this._escape(model.text.updated)}: ${this._escape(this._date(model.updated))}</p>
      </div>
      <div class="score" style="--score:${model.score ?? 0}">
        <div><strong>${model.score ?? "—"}</strong><span>${this._escape(model.text.healthScore)}</span></div>
      </div>
    </section>
    <section class="metrics">
      ${this._metric("mdi:shield-check-outline", model.text.status, model.statusLabel, model.tone)}
      ${this._metric("mdi:timer-sand", model.text.latestBackup, this._formatState(model.latestAge))}
      ${this._metric("mdi:database", model.text.backupSize, this._formatState(model.latestSize))}
      ${this._metric("mdi:archive-multiple", model.text.storedBackups, this._formatState(model.stored))}
      ${this._metric("mdi:shield-search", model.text.integrity, model.integrityLabel, model.integrityTone)}
    </section>
    <section class="content-grid">
      <article class="card recommendation-card">
        <div class="card-title"><ha-icon icon="mdi:lightbulb-on-outline"></ha-icon><h3>${this._escape(model.text.recommendation)}</h3></div>
        <p>${this._escape(model.recommendationLabel)}</p>
      </article>
      <article class="card">
        <div class="card-title"><ha-icon icon="mdi:alert-outline"></ha-icon><h3>${this._escape(model.text.problems)}</h3></div>
        <div class="rows">${this._problemRows(model.problems, model.text)}</div>
      </article>
      <article class="card storage-card">
        <div class="card-title"><ha-icon icon="mdi:server-network"></ha-icon><h3>${this._escape(model.text.storage)}</h3></div>
        <div class="rows">${this._storageRows(model.agents, model.text)}</div>
      </article>
    </section>
    ${this._actionFooter(model)}`;
  }

  _activityMessage(record, text) {
    const action = text.activityActions[record.action] || this._humanize(record.action);
    const progress = record.details?.progress_percent;
    if (progress !== undefined) return `${action} – ${progress}%`;
    const outcome = text.activityOutcomes[record.outcome] || this._humanize(record.outcome);
    return `${action} – ${outcome}`;
  }

  _activityDetails(record) {
    const details = Object.entries(record.details || {})
      .filter(([key]) => key !== "progress_percent")
      .map(([key, value]) => `${this._humanize(key)}=${value}`);
    return details.join(" · ");
  }

  _logRows(records, text) {
    const query = this._logSearch.trim().toLocaleLowerCase(this._language());
    const filtered = records.filter((record) => {
      if (!query) return true;
      const searchable = `${record.action} ${record.outcome} ${this._activityMessage(record, text)} ${this._activityDetails(record)}`;
      return searchable.toLocaleLowerCase(this._language()).includes(query);
    });
    if (!filtered.length) return `<div class="log-empty">${this._escape(text.noLogs)}</div>`;
    return [...filtered].reverse().map((record) => {
      const details = this._activityDetails(record);
      const detailLine = details ? `<span>${this._escape(details)}</span>` : "";
      const level = ["warning", "error", "critical"].includes(record.level)
        ? record.level : "info";
      return `<div class="log-row ${level}">
        <time>${this._escape(this._date(record.timestamp))}</time>
        <strong>${this._escape(this._activityMessage(record, text))}</strong>
        ${detailLine}
      </div>`;
    }).join("");
  }

  _logTemplate(model) {
    if (!model.activityEnabled) {
      return `<section class="log-disabled">
        <ha-icon icon="mdi:text-box-remove-outline"></ha-icon>
        <p>${this._escape(model.text.loggingDisabled)}</p>
      </section>`;
    }
    return `<section class="log-view">
      <div class="log-toolbar">
        <label><ha-icon icon="mdi:magnify"></ha-icon>
          <input data-log-search type="search" value="${this._escape(this._logSearch)}" placeholder="${this._escape(model.text.searchLogs)}">
        </label>
        <span class="live-indicator"><i></i>${this._escape(model.text.live)}</span>
      </div>
      <article class="log-console">
        <h2>${this._escape(model.text.logTitle)}</h2>
        <div class="log-lines">${this._logRows(model.activityEntries, model.text)}</div>
      </article>
    </section>`;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const restoreSearchFocus = this.shadowRoot.activeElement?.hasAttribute("data-log-search");
    const model = this._renderModel();
    const content = this._activeTab === "logs"
      ? this._logTemplate(model) : this._overviewTemplate(model);
    const settingsButton = this._settingsButton(model.isAdmin, model.text);

    this.shadowRoot.innerHTML = `
      <style>${BackupCheckupPanel.styles}</style>
      <main>
        <header>
          <div class="brand"><ha-icon icon="mdi:backup-restore"></ha-icon></div>
          <div><h1>${this._escape(model.text.dashboard)}</h1><p>${this._escape(model.text.subtitle)}</p></div>
          ${settingsButton}
        </header>
        ${this._tabs(model.text)}
        ${content}
      </main>`;

    this.shadowRoot.querySelector('[data-nav="settings"]')?.addEventListener("click", () => this._openSettings());
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        this._activeTab = button.dataset.tab;
        this._scheduleRender();
      });
    });
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => this._runAction(button.dataset.action));
    });
    const search = this.shadowRoot.querySelector("[data-log-search]");
    search?.addEventListener("input", (event) => {
      this._logSearch = event.target.value;
      this._scheduleRender();
    });
    if (restoreSearchFocus && search) {
      search.focus();
      search.setSelectionRange(search.value.length, search.value.length);
    }
  }

  _buttonDisabled(state, action) {
    return this._busy.has(action) || !state || state.state === "unavailable";
  }

  async _runAction(action) {
    const entityId = this._entities()[action];
    if (!entityId || this._busy.has(action)) return;
    this._busy.add(action);
    this._scheduleRender();
    try {
      await this._hass.callService("button", "press", { entity_id: entityId });
    } catch (_error) {
      this.dispatchEvent(new CustomEvent("hass-notification", {
        bubbles: true,
        composed: true,
        detail: { message: this._text().actionFailed },
      }));
    } finally {
      this._busy.delete(action);
      this._scheduleRender();
    }
  }

  _openSettings() {
    history.pushState(null, "", "/config/integrations/integration/backup_checkup");
    window.dispatchEvent(new Event("location-changed"));
  }

  static get styles() {
    return `
      :host { display:block; min-height:100%; background:var(--primary-background-color); color:var(--primary-text-color); }
      * { box-sizing:border-box; }
      main { width:min(1180px, 100%); margin:0 auto; padding:28px 24px 40px; font-family:var(--paper-font-body1_-_font-family, system-ui, sans-serif); }
      header { display:flex; align-items:center; gap:14px; margin-bottom:24px; }
      header h1 { margin:0; font-size:26px; line-height:1.2; font-weight:650; }
      header p { margin:5px 0 0; color:var(--secondary-text-color); font-size:14px; }
      .brand { width:48px; height:48px; display:grid; place-items:center; border-radius:15px; background:var(--primary-color); color:var(--text-primary-color, white); }
      .brand ha-icon { --mdc-icon-size:27px; }
      .icon-button { margin-left:auto; width:44px; height:44px; display:grid; place-items:center; border:0; border-radius:13px; background:var(--card-background-color); color:var(--primary-text-color); box-shadow:var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.12)); cursor:pointer; }
      .tabs { display:flex; gap:6px; margin:-6px 0 22px; border-bottom:1px solid var(--divider-color); }
      .tab { display:flex; align-items:center; gap:8px; min-height:46px; padding:0 16px; border:0; border-bottom:3px solid transparent; background:transparent; color:var(--secondary-text-color); font:inherit; font-weight:600; cursor:pointer; }
      .tab.active { border-bottom-color:var(--primary-color); color:var(--primary-color); }
      .tab ha-icon { --mdc-icon-size:20px; }
      .hero { --tone:#607d8b; --tone-soft:rgba(96,125,139,.14); display:flex; align-items:center; justify-content:space-between; min-height:210px; padding:32px 38px; overflow:hidden; border-radius:24px; background:linear-gradient(125deg, var(--tone-soft), var(--card-background-color) 62%); border:1px solid color-mix(in srgb, var(--tone) 28%, var(--divider-color)); position:relative; }
      .hero.good { --tone:#2e9d68; --tone-soft:rgba(46,157,104,.19); }
      .hero.danger { --tone:#d84b55; --tone-soft:rgba(216,75,85,.18); }
      .hero::after { content:""; position:absolute; width:260px; height:260px; right:-80px; top:-130px; border-radius:50%; background:var(--tone-soft); }
      .hero-copy { position:relative; z-index:1; }
      .eyebrow { display:flex; align-items:center; gap:9px; color:var(--tone); font-weight:650; font-size:14px; }
      .eyebrow span { width:9px; height:9px; border-radius:50%; background:var(--tone); box-shadow:0 0 0 5px var(--tone-soft); }
      .hero h2 { margin:18px 0 9px; max-width:620px; font-size:clamp(25px, 4vw, 38px); line-height:1.12; letter-spacing:-.025em; }
      .hero p { margin:0; color:var(--secondary-text-color); font-size:13px; }
      .score { --score:0; flex:0 0 auto; width:142px; height:142px; margin-left:32px; display:grid; place-items:center; border-radius:50%; background:conic-gradient(var(--tone) calc(var(--score) * 1%), var(--divider-color) 0); position:relative; z-index:1; }
      .score::before { content:""; position:absolute; inset:10px; border-radius:50%; background:var(--card-background-color); }
      .score div { position:relative; display:flex; flex-direction:column; align-items:center; }
      .score strong { font-size:35px; line-height:1; }
      .score span { margin-top:7px; max-width:90px; text-align:center; color:var(--secondary-text-color); font-size:11px; }
      .metrics { display:grid; grid-template-columns:repeat(5, minmax(0, 1fr)); gap:13px; margin:18px 0; }
      .metric { --metric:#607d8b; min-height:105px; display:flex; align-items:flex-start; gap:12px; padding:18px; border-radius:17px; background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.08)); }
      .metric.good { --metric:#2e9d68; } .metric.warning { --metric:#e79a24; } .metric.danger { --metric:#d84b55; }
      .metric > ha-icon { flex:0 0 auto; color:var(--metric); --mdc-icon-size:24px; }
      .metric div { min-width:0; display:flex; flex-direction:column; gap:8px; }
      .metric span { color:var(--secondary-text-color); font-size:12px; line-height:1.25; }
      .metric strong { font-size:17px; line-height:1.25; overflow-wrap:anywhere; }
      .content-grid { display:grid; grid-template-columns:minmax(0, .8fr) minmax(0, 1.2fr); gap:18px; }
      .card { padding:22px; border-radius:19px; background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.08)); }
      .storage-card { grid-column:1 / -1; }
      .card-title { display:flex; align-items:center; gap:10px; margin-bottom:16px; }
      .card-title ha-icon { color:var(--primary-color); --mdc-icon-size:22px; }
      .card-title h3 { margin:0; font-size:16px; }
      .recommendation-card p { margin:0; font-size:19px; line-height:1.45; font-weight:550; }
      .rows { display:flex; flex-direction:column; }
      .problem-row, .storage-row { display:flex; align-items:center; gap:12px; min-height:52px; border-top:1px solid var(--divider-color); }
      .problem-row:first-child, .storage-row:first-child { border-top:0; }
      .problem-row ha-icon { color:#d84b55; }
      .storage-icon { width:37px; height:37px; display:grid; place-items:center; border-radius:11px; background:rgba(96,125,139,.12); color:#607d8b; }
      .storage-icon.good { background:rgba(46,157,104,.13); color:#2e9d68; }
      .storage-icon.warning { background:rgba(231,154,36,.13); color:#e79a24; }
      .storage-icon.danger { background:rgba(216,75,85,.13); color:#d84b55; }
      .storage-copy { min-width:0; flex:1; display:flex; flex-direction:column; gap:3px; }
      .storage-copy strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .storage-copy span { color:var(--secondary-text-color); font-size:12px; }
      .storage-count { text-align:right; font-size:17px; font-weight:650; }
      .storage-count span { display:block; color:var(--secondary-text-color); font-size:11px; font-weight:400; }
      .empty { min-height:52px; display:flex; align-items:center; gap:9px; color:var(--secondary-text-color); }
      .empty.success ha-icon { color:#2e9d68; }
      .log-view { display:flex; flex-direction:column; gap:16px; }
      .log-toolbar { display:flex; align-items:center; gap:14px; }
      .log-toolbar label { flex:1; min-height:44px; display:flex; align-items:center; gap:9px; padding:0 13px; border:1px solid var(--divider-color); border-radius:12px; background:var(--card-background-color); }
      .log-toolbar label:focus-within { border-color:var(--primary-color); box-shadow:0 0 0 1px var(--primary-color); }
      .log-toolbar input { width:100%; border:0; outline:0; background:transparent; color:var(--primary-text-color); font:inherit; }
      .live-indicator { display:flex; align-items:center; gap:7px; color:var(--primary-color); font-size:13px; font-weight:700; }
      .live-indicator i { width:9px; height:9px; border-radius:50%; background:var(--primary-color); box-shadow:0 0 0 4px color-mix(in srgb, var(--primary-color) 18%, transparent); }
      .log-console { min-height:520px; overflow:hidden; border:1px solid var(--divider-color); border-radius:16px; background:var(--card-background-color); }
      .log-console h2 { margin:0; padding:17px 18px; border-bottom:1px solid var(--divider-color); font-size:18px; }
      .log-lines { max-height:68vh; overflow:auto; padding:8px 0; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .log-row { display:grid; grid-template-columns:190px minmax(250px, .9fr) minmax(220px, 1.1fr); gap:14px; padding:8px 18px; border-left:3px solid transparent; font-size:12px; line-height:1.45; }
      .log-row:hover { background:color-mix(in srgb, var(--primary-color) 7%, transparent); }
      .log-row time { color:var(--secondary-text-color); }
      .log-row strong { color:#2e9d68; }
      .log-row.warning { border-left-color:#e79a24; } .log-row.warning strong { color:#e79a24; }
      .log-row.error, .log-row.critical { border-left-color:#d84b55; } .log-row.error strong, .log-row.critical strong { color:#d84b55; }
      .log-row span { color:var(--secondary-text-color); overflow-wrap:anywhere; }
      .log-empty, .log-disabled { min-height:260px; display:flex; align-items:center; justify-content:center; gap:12px; padding:28px; color:var(--secondary-text-color); text-align:center; }
      .log-disabled { flex-direction:column; border:1px dashed var(--divider-color); border-radius:16px; background:var(--card-background-color); }
      .log-disabled ha-icon { color:var(--primary-color); --mdc-icon-size:38px; }
      footer { display:flex; justify-content:flex-end; gap:11px; margin-top:20px; }
      .action { min-height:44px; display:flex; align-items:center; gap:8px; padding:0 17px; border-radius:12px; border:1px solid var(--divider-color); font:inherit; font-weight:600; cursor:pointer; }
      .action.primary { background:var(--primary-color); border-color:var(--primary-color); color:var(--text-primary-color, white); }
      .action.secondary { background:var(--card-background-color); color:var(--primary-text-color); }
      .action:disabled { opacity:.48; cursor:default; }
      @media (max-width:900px) { .metrics { grid-template-columns:repeat(2, minmax(0, 1fr)); } .content-grid { grid-template-columns:1fr; } .storage-card { grid-column:auto; } .log-row { grid-template-columns:165px 1fr; } .log-row span { grid-column:2; } }
      @media (max-width:620px) { main { padding:18px 12px 28px; } header { padding:0 4px; } header p { display:none; } .tabs { margin-top:0; } .hero { min-height:0; padding:24px 21px; } .score { width:104px; height:104px; margin-left:14px; } .score::before { inset:8px; } .score strong { font-size:27px; } .hero h2 { font-size:23px; } .metrics { grid-template-columns:1fr 1fr; gap:10px; } .metric { min-height:95px; padding:15px; } .content-grid { gap:12px; } .card { padding:18px; } .log-toolbar { align-items:stretch; flex-direction:column; } .live-indicator { align-self:flex-end; } .log-row { grid-template-columns:1fr; gap:3px; padding:10px 13px; } .log-row span { grid-column:auto; } footer { flex-direction:column-reverse; } .action { justify-content:center; } }
      @media (max-width:390px) { .hero { align-items:flex-start; } .score { width:88px; height:88px; } .score span { display:none; } .metrics { grid-template-columns:1fr; } }
    `;
  }
}

if (!customElements.get("backup-checkup-panel")) {
  customElements.define("backup-checkup-panel", BackupCheckupPanel);
}
