const PANEL_ELEMENT_NAME = "backup-checkup-panel-v2-7-1-r1";

const TRANSLATION_SEPARATOR = "\u001f";
const TRANSLATION_KEYS = Object.freeze({
  "scalar": [
    "dashboard",
    "subtitle",
    "healthy",
    "attention",
    "unavailable",
    "healthScore",
    "status",
    "recommendation",
    "latestBackup",
    "backupSize",
    "storedBackups",
    "integrity",
    "problems",
    "noProblems",
    "storage",
    "noStorage",
    "backups",
    "lastBackup",
    "refresh",
    "verify",
    "settings",
    "updated",
    "actionFailed",
    "unknownError",
    "unknownRecommendation",
    "healthDetails",
    "noDeductions",
    "pointsDeducted",
    "integrityDetails",
    "checkedAt",
    "duration",
    "verifiedSize",
    "filesChecked",
    "warnings",
    "nextStep",
    "statusLabel",
    "newEntries",
    "clearLog",
    "exportLog",
    "clearConfirm",
    "persistentLog",
    "runtimeLog",
    "filterLabel",
    "overviewTab",
    "logTab",
    "logTitle",
    "searchLogs",
    "noLogs",
    "loggingDisabled",
    "live"
  ],
  "levelLabels": [
    "all",
    "info",
    "warning",
    "error"
  ],
  "typeLabels": [
    "all",
    "check",
    "backup",
    "notification",
    "system"
  ],
  "storageStates": [
    "online",
    "stale",
    "offline"
  ],
  "detailLabels": [
    "error_code",
    "error_type",
    "reason",
    "source",
    "status",
    "version",
    "target_count",
    "notification_type",
    "retry_attempts",
    "remaining",
    "failures",
    "enabled",
    "platform_count"
  ],
  "detailValues": [
    "manual",
    "automatic",
    "cooldown",
    "not_configured",
    "true",
    "false",
    "test"
  ],
  "errorMessages": [
    "timeout",
    "connection_error",
    "not_configured",
    "cooldown",
    "password_required",
    "unavailable"
  ],
  "errorRecommendations": [
    "timeout",
    "connection_error",
    "not_configured",
    "cooldown",
    "password_required",
    "unavailable"
  ],
  "healthComponents": [
    "availability",
    "freshness",
    "backup_quality",
    "integrity",
    "storage",
    "automation"
  ],
  "activityActions": [
    "verification_prepare",
    "storage_copy_prepare",
    "backup_download",
    "backup_extract",
    "encrypted_backup_extract",
    "database_read",
    "temporary_data_cleanup",
    "inventory_refresh",
    "backup_manager_read",
    "integrity_check",
    "integrity_check_request",
    "integrity_result_persist",
    "health_state",
    "notification_send",
    "notification_processing",
    "config_entry_setup",
    "entity_platform_setup",
    "repair_issue_sync",
    "first_refresh",
    "coordinator_shutdown",
    "integrity_state_load",
    "integrity_check_schedule",
    "integrity_background_task",
    "post_verification_refresh",
    "service_refresh",
    "service_verify_latest_backup",
    "service_test_notification",
    "panel_setup",
    "config_entry_unload",
    "config_entry_remove"
  ],
  "activityOutcomes": [
    "started",
    "completed",
    "changed",
    "skipped",
    "failed",
    "cancelled"
  ]
});

const NESTED_TRANSLATION_GROUPS = Object.freeze(["levelLabels","typeLabels","storageStates","detailLabels","detailValues","errorMessages","errorRecommendations","healthComponents","activityActions","activityOutcomes"]);

const unpackTranslation = (keys, packed) => Object.fromEntries(
  packed.split(TRANSLATION_SEPARATOR).map((value, index) => [keys[index], value])
);

const createLocale = (packed) => {
  const groups = packed.map((value, index) => unpackTranslation(
    TRANSLATION_KEYS[index === 0 ? "scalar" : NESTED_TRANSLATION_GROUPS[index - 1]], value
  ));
  return {
    ...groups[0],
    levelLabels: groups[1],
    typeLabels: groups[2],
    storageStates: groups[3],
    detailLabels: groups[4],
    detailValues: groups[5],
    errorMessages: groups[6],
    errorRecommendations: groups[7],
    healthComponents: groups[8],
    activityActions: groups[9],
    activityOutcomes: groups[10],
  };
};

const TEXT = {
  en: createLocale(["Backup overview\u001fLive status of your Home Assistant backups\u001fBackup protection is healthy\u001fBackup protection needs attention\u001fBackup data is not available yet\u001fHealth score\u001fCurrent status\u001fRecommendation\u001fLatest backup\u001fLatest backup size\u001fStored backups\u001fIntegrity\u001fActive problems\u001fNo active backup problems.\u001fStorage locations\u001fNo storage information is available.\u001fbackups\u001fLatest backup\u001fRefresh\u001fVerify latest backup\u001fSettings\u001fUpdated\u001fThe action could not be completed.\u001fThe operation could not be completed.\u001fCheck Home Assistant and the storage location, then retry.\u001fWhy this score?\u001fNo health-score deductions are active.\u001fpoints deducted\u001fLatest verification result\u001fChecked\u001fDuration\u001fVerified size\u001fFiles checked\u001fWarnings\u001fRecommended next step\u001fStatus\u001fNew entries available\u001fClear log\u001fExport log\u001fClear all live-log entries?\u001fPersistent\u001fUntil restart\u001fFilter\u001fOverview\u001fLive log\u001fBackupCheckup live log\u001fSearch log entries\u001fNo matching log entries are available.\u001fDetailed live logging is disabled in the integration options.\u001fLive","All\u001fInfo\u001fWarnings\u001fErrors","All operations\u001fChecks\u001fBackups\u001fNotifications\u001fSystem","Online\u001fOutdated\u001fOffline","Reason\u001fError type\u001fReason\u001fTrigger\u001fStatus\u001fVersion\u001fRecipients\u001fNotification\u001fRetry attempts\u001fRemaining\u001fFailures\u001fEnabled\u001fPlatforms","Manual\u001fAutomatic\u001fWaiting period active\u001fNot configured\u001fYes\u001fNo\u001fTest","The operation exceeded its time limit.\u001fThe storage location could not be reached.\u001fThe required function is not configured.\u001fThe safety waiting period is still active.\u001fThe backup password is required.\u001fThe requested service is currently unavailable.","Try again and review the configured time limit.\u001fCheck the storage connection and retry the operation.\u001fComplete the integration options before retrying.\u001fWait until the displayed waiting period ends.\u001fStore the backup password in Home Assistant and retry.\u001fCheck Home Assistant and the storage location, then retry.","Backup availability\u001fBackup age\u001fBackup quality\u001fIntegrity verification\u001fStorage and redundancy\u001fAutomatic backups and schedule","Preparing integrity verification\u001fPreparing storage copy\u001fDownloading backup\u001fExtracting backup\u001fExtracting encrypted backup\u001fReading and checking database\u001fRemoving temporary verification data\u001fRefreshing backup inventory\u001fReading backup manager\u001fRunning integrity verification\u001fProcessing verification request\u001fSaving verification result\u001fUpdating backup health\u001fSending notification\u001fProcessing notifications\u001fStarting integration\u001fSetting up entities\u001fSynchronizing repair notices\u001fCompleting first inventory refresh\u001fStopping integration\u001fLoading saved verification state\u001fScheduling automatic verification\u001fMonitoring background verification\u001fRefreshing status after verification\u001fRunning manual refresh\u001fStarting manual backup verification\u001fTesting notification\u001fSetting up sidebar panel\u001fStopping integration entry\u001fRemoving integration data","started\u001fcompleted\u001fin progress\u001fskipped\u001ffailed\u001fcancelled"]),
  de: createLocale(["Backup-Übersicht\u001fLive-Status deiner Home-Assistant-Backups\u001fDer Backup-Schutz ist in Ordnung\u001fDer Backup-Schutz benötigt Aufmerksamkeit\u001fBackup-Daten sind noch nicht verfügbar\u001fGesundheitswert\u001fAktueller Status\u001fEmpfehlung\u001fLetztes Backup\u001fGröße des letzten Backups\u001fGespeicherte Backups\u001fIntegrität\u001fAktive Probleme\u001fKeine aktiven Backup-Probleme.\u001fSpeicherorte\u001fKeine Informationen zu Speicherorten verfügbar.\u001fBackups\u001fLetztes Backup\u001fAktualisieren\u001fLetztes Backup prüfen\u001fEinstellungen\u001fAktualisiert\u001fDie Aktion konnte nicht ausgeführt werden.\u001fDer Vorgang konnte nicht abgeschlossen werden.\u001fHome Assistant und den Speicherort prüfen und den Vorgang wiederholen.\u001fWarum dieser Wert?\u001fEs sind keine Abzüge beim Gesundheitswert aktiv.\u001fPunkte Abzug\u001fErgebnis der letzten Prüfung\u001fGeprüft\u001fDauer\u001fGeprüfte Größe\u001fGeprüfte Dateien\u001fWarnungen\u001fEmpfohlener nächster Schritt\u001fStatus\u001fNeue Einträge verfügbar\u001fProtokoll leeren\u001fProtokoll exportieren\u001fAlle Einträge des Live-Protokolls löschen?\u001fDauerhaft gespeichert\u001fBis zum Neustart\u001fFilter\u001fÜbersicht\u001fProtokoll\u001fBackupCheckup Live-Protokoll\u001fProtokolle durchsuchen\u001fKeine passenden Protokolleinträge vorhanden.\u001fDas ausführliche Live-Protokoll ist in den Integrationsoptionen deaktiviert.\u001fLive","Alle\u001fInfo\u001fWarnungen\u001fFehler","Alle Vorgänge\u001fPrüfungen\u001fBackups\u001fBenachrichtigungen\u001fSystem","Online\u001fVeraltet\u001fOffline","Grund\u001fFehlerart\u001fGrund\u001fAuslöser\u001fStatus\u001fVersion\u001fEmpfänger\u001fBenachrichtigung\u001fWiederholungen\u001fVerbleibend\u001fFehler\u001fAktiviert\u001fPlattformen","Manuell\u001fAutomatisch\u001fSicherheitswartezeit aktiv\u001fNicht eingerichtet\u001fJa\u001fNein\u001fTest","Der Vorgang hat das Zeitlimit überschritten.\u001fDer Speicherort konnte nicht erreicht werden.\u001fDie benötigte Funktion ist nicht eingerichtet.\u001fDie Sicherheitswartezeit ist noch aktiv.\u001fDas Backup-Passwort wird benötigt.\u001fDer angeforderte Dienst ist derzeit nicht verfügbar.","Erneut versuchen und das eingestellte Zeitlimit prüfen.\u001fVerbindung zum Speicherort prüfen und den Vorgang wiederholen.\u001fIntegrationsoptionen vervollständigen und erneut versuchen.\u001fBis zum Ende der angezeigten Wartezeit warten.\u001fBackup-Passwort in Home Assistant hinterlegen und erneut prüfen.\u001fHome Assistant und den Speicherort prüfen und erneut versuchen.","Backup-Verfügbarkeit\u001fBackup-Alter\u001fBackup-Qualität\u001fIntegritätsprüfung\u001fSpeicher und Redundanz\u001fAutomatische Backups und Zeitplan","Integritätsprüfung wird vorbereitet\u001fSpeicherkopie wird vorbereitet\u001fBackup wird heruntergeladen\u001fBackup wird extrahiert\u001fVerschlüsseltes Backup wird extrahiert\u001fDatenbank wird gelesen und geprüft\u001fTemporäre Prüfdaten werden entfernt\u001fBackup-Inventar wird aktualisiert\u001fBackup-Manager wird gelesen\u001fIntegritätsprüfung wird ausgeführt\u001fPrüfauftrag wird verarbeitet\u001fPrüfergebnis wird gespeichert\u001fBackup-Zustand wird aktualisiert\u001fBenachrichtigung wird gesendet\u001fBenachrichtigungen werden verarbeitet\u001fIntegration wird gestartet\u001fEntitäten werden eingerichtet\u001fReparaturhinweise werden synchronisiert\u001fErste Inventarabfrage wird abgeschlossen\u001fIntegration wird beendet\u001fGespeicherter Prüfstatus wird geladen\u001fAutomatische Prüfung wird eingeplant\u001fHintergrundprüfung wird überwacht\u001fStatus wird nach der Prüfung aktualisiert\u001fManuelle Aktualisierung wird ausgeführt\u001fManuelle Backup-Prüfung wird gestartet\u001fBenachrichtigung wird getestet\u001fSeitenleistenansicht wird eingerichtet\u001fIntegrationseintrag wird beendet\u001fIntegrationsdaten werden entfernt","gestartet\u001fabgeschlossen\u001fläuft\u001fübersprungen\u001ffehlgeschlagen\u001fabgebrochen"]),
  da: createLocale(["Backupoversigt\u001fLivestatus for dine Home Assistant-backups\u001fBackupbeskyttelsen er i orden\u001fBackupbeskyttelsen kræver opmærksomhed\u001fBackupdata er endnu ikke tilgængelige\u001fSundhedsscore\u001fAktuel status\u001fAnbefaling\u001fSeneste backup\u001fStørrelse på seneste backup\u001fGemte backups\u001fIntegritet\u001fAktive problemer\u001fIngen aktive backupproblemer.\u001fLagerplaceringer\u001fIngen lageroplysninger er tilgængelige.\u001fbackups\u001fSeneste backup\u001fOpdater\u001fKontrollér seneste backup\u001fIndstillinger\u001fOpdateret\u001fHandlingen kunne ikke gennemføres.\u001fHandlingen kunne ikke gennemføres.\u001fKontrollér Home Assistant og lagerplaceringen, og prøv igen.\u001fHvorfor denne score?\u001fIngen fradrag i sundhedsscoren er aktive.\u001fpoint trukket fra\u001fSeneste kontrolresultat\u001fKontrolleret\u001fVarighed\u001fKontrolleret størrelse\u001fKontrollerede filer\u001fAdvarsler\u001fAnbefalet næste trin\u001fStatus\u001fNye poster tilgængelige\u001fRyd log\u001fEksportér log\u001fRyd alle poster i liveloggen?\u001fPermanent\u001fIndtil genstart\u001fFilter\u001fOversigt\u001fLivelog\u001fBackupCheckup-livelog\u001fSøg i logposter\u001fIngen matchende logposter.\u001fDetaljeret livelog er deaktiveret i integrationsindstillingerne.\u001fLive","Alle\u001fInfo\u001fAdvarsler\u001fFejl","Alle handlinger\u001fKontroller\u001fBackups\u001fNotifikationer\u001fSystem","Online\u001fForældet\u001fOffline","Årsag\u001fFejltype\u001fÅrsag\u001fUdløser\u001fStatus\u001fVersion\u001fModtagere\u001fNotifikation\u001fForsøg\u001fResterende\u001fFejl\u001fAktiveret\u001fPlatforme","Manuel\u001fAutomatisk\u001fVentetid aktiv\u001fIkke konfigureret\u001fJa\u001fNej\u001fTest","Handlingen overskred tidsgrænsen.\u001fLagerplaceringen kunne ikke nås.\u001fDen nødvendige funktion er ikke konfigureret.\u001fSikkerhedsventetiden er stadig aktiv.\u001fBackupadgangskoden er nødvendig.\u001fTjenesten er ikke tilgængelig.","Prøv igen, og kontrollér tidsgrænsen.\u001fKontrollér lagerforbindelsen, og prøv igen.\u001fFuldfør integrationsindstillingerne.\u001fVent, til den viste ventetid er udløbet.\u001fGem backupadgangskoden, og prøv igen.\u001fKontrollér Home Assistant og lagerplaceringen.","Backuptilgængelighed\u001fBackupalder\u001fBackupkvalitet\u001fIntegritetskontrol\u001fLager og redundans\u001fAutomatiske backups og tidsplan","Forbereder integritetskontrol\u001fForbereder lagerkopi\u001fDownloader backup\u001fUdpakker backup\u001fUdpakker krypteret backup\u001fLæser og kontrollerer database\u001fFjerner midlertidige kontroldata\u001fOpdaterer backupoversigt\u001fLæser backupmanager\u001fKører integritetskontrol\u001fBehandler kontrolanmodning\u001fGemmer kontrolresultat\u001fOpdaterer backuptilstand\u001fSender notifikation\u001fBehandler notifikationer\u001fStarter integration\u001fKonfigurerer enheder\u001fSynkroniserer reparationsmeddelelser\u001fAfslutter første opdatering\u001fStopper integration\u001fIndlæser gemt kontrolstatus\u001fPlanlægger automatisk kontrol\u001fOvervåger baggrundskontrol\u001fOpdaterer status efter kontrol\u001fKører manuel opdatering\u001fStarter manuel backupkontrol\u001fTester notifikation\u001fKonfigurerer sidepanel\u001fStopper integrationspost\u001fFjerner integrationsdata","startet\u001fafsluttet\u001fi gang\u001fsprunget over\u001fmislykket\u001fannulleret"]),
  es: createLocale(["Resumen de copias\u001fEstado en vivo de tus copias de Home Assistant\u001fLa protección de copias está correcta\u001fLa protección de copias requiere atención\u001fLos datos de copia aún no están disponibles\u001fPuntuación de salud\u001fEstado actual\u001fRecomendación\u001fÚltima copia\u001fTamaño de la última copia\u001fCopias guardadas\u001fIntegridad\u001fProblemas activos\u001fNo hay problemas activos.\u001fUbicaciones de almacenamiento\u001fNo hay información de almacenamiento.\u001fcopias\u001fÚltima copia\u001fActualizar\u001fVerificar última copia\u001fAjustes\u001fActualizado\u001fNo se pudo completar la acción.\u001fNo se pudo completar la operación.\u001fComprueba Home Assistant y el almacenamiento y reintenta.\u001f¿Por qué esta puntuación?\u001fNo hay deducciones activas.\u001fpuntos descontados\u001fÚltimo resultado de verificación\u001fVerificado\u001fDuración\u001fTamaño verificado\u001fArchivos verificados\u001fAdvertencias\u001fSiguiente paso recomendado\u001fEstado\u001fHay entradas nuevas\u001fBorrar registro\u001fExportar registro\u001f¿Borrar todas las entradas del registro?\u001fPersistente\u001fHasta reiniciar\u001fFiltro\u001fResumen\u001fRegistro en vivo\u001fRegistro en vivo de BackupCheckup\u001fBuscar entradas\u001fNo hay entradas coincidentes.\u001fEl registro detallado está desactivado en las opciones de la integración.\u001fEn vivo","Todo\u001fInfo\u001fAdvertencias\u001fErrores","Todas las operaciones\u001fVerificaciones\u001fCopias\u001fNotificaciones\u001fSistema","En línea\u001fDesactualizado\u001fSin conexión","Motivo\u001fTipo de error\u001fMotivo\u001fActivador\u001fEstado\u001fVersión\u001fDestinatarios\u001fNotificación\u001fReintentos\u001fRestante\u001fErrores\u001fActivado\u001fPlataformas","Manual\u001fAutomático\u001fEspera de seguridad activa\u001fSin configurar\u001fSí\u001fNo\u001fPrueba","La operación superó el tiempo límite.\u001fNo se pudo acceder al almacenamiento.\u001fLa función necesaria no está configurada.\u001fLa espera de seguridad sigue activa.\u001fSe necesita la contraseña de la copia.\u001fEl servicio no está disponible.","Vuelve a intentarlo y revisa el límite de tiempo.\u001fComprueba la conexión del almacenamiento y reintenta.\u001fCompleta las opciones de la integración.\u001fEspera hasta que finalice el periodo indicado.\u001fGuarda la contraseña y vuelve a intentarlo.\u001fComprueba Home Assistant y el almacenamiento.","Disponibilidad de copias\u001fAntigüedad de la copia\u001fCalidad de la copia\u001fVerificación de integridad\u001fAlmacenamiento y redundancia\u001fCopias automáticas y programación","Preparando verificación de integridad\u001fPreparando copia de almacenamiento\u001fDescargando copia\u001fExtrayendo copia\u001fExtrayendo copia cifrada\u001fLeyendo y comprobando la base de datos\u001fEliminando datos temporales\u001fActualizando inventario de copias\u001fLeyendo gestor de copias\u001fEjecutando verificación de integridad\u001fProcesando solicitud de verificación\u001fGuardando resultado\u001fActualizando estado de protección\u001fEnviando notificación\u001fProcesando notificaciones\u001fIniciando integración\u001fConfigurando entidades\u001fSincronizando avisos de reparación\u001fCompletando primera actualización\u001fDeteniendo integración\u001fCargando estado guardado\u001fProgramando verificación automática\u001fSupervisando verificación en segundo plano\u001fActualizando estado tras la verificación\u001fEjecutando actualización manual\u001fIniciando verificación manual\u001fProbando notificación\u001fConfigurando panel lateral\u001fDeteniendo entrada de integración\u001fEliminando datos de integración","iniciado\u001fcompletado\u001fen curso\u001fomitido\u001ffallido\u001fcancelado"]),
  fr: createLocale(["Vue d’ensemble des sauvegardes\u001fÉtat en direct des sauvegardes Home Assistant\u001fLa protection des sauvegardes est correcte\u001fLa protection des sauvegardes requiert votre attention\u001fLes données de sauvegarde ne sont pas encore disponibles\u001fScore de santé\u001fÉtat actuel\u001fRecommandation\u001fDernière sauvegarde\u001fTaille de la dernière sauvegarde\u001fSauvegardes stockées\u001fIntégrité\u001fProblèmes actifs\u001fAucun problème de sauvegarde actif.\u001fEmplacements de stockage\u001fAucune information de stockage disponible.\u001fsauvegardes\u001fDernière sauvegarde\u001fActualiser\u001fVérifier la dernière sauvegarde\u001fParamètres\u001fActualisé\u001fL’action n’a pas pu être effectuée.\u001fL’opération n’a pas pu être terminée.\u001fVérifiez Home Assistant et le stockage puis réessayez.\u001fPourquoi ce score ?\u001fAucune déduction du score n’est active.\u001fpoints déduits\u001fDernier résultat de vérification\u001fVérifié\u001fDurée\u001fTaille vérifiée\u001fFichiers vérifiés\u001fAvertissements\u001fProchaine étape recommandée\u001fÉtat\u001fNouvelles entrées disponibles\u001fEffacer le journal\u001fExporter le journal\u001fEffacer toutes les entrées du journal ?\u001fPersistant\u001fJusqu’au redémarrage\u001fFiltre\u001fVue d’ensemble\u001fJournal en direct\u001fJournal en direct BackupCheckup\u001fRechercher dans le journal\u001fAucune entrée correspondante.\u001fLe journal détaillé est désactivé dans les options de l’intégration.\u001fDirect","Tout\u001fInfo\u001fAvertissements\u001fErreurs","Toutes les opérations\u001fVérifications\u001fSauvegardes\u001fNotifications\u001fSystème","En ligne\u001fObsolète\u001fHors ligne","Cause\u001fType d’erreur\u001fCause\u001fDéclencheur\u001fÉtat\u001fVersion\u001fDestinataires\u001fNotification\u001fTentatives\u001fRestant\u001fErreurs\u001fActivé\u001fPlateformes","Manuel\u001fAutomatique\u001fDélai de sécurité actif\u001fNon configuré\u001fOui\u001fNon\u001fTest","L’opération a dépassé le délai.\u001fLe stockage est inaccessible.\u001fLa fonction requise n’est pas configurée.\u001fLe délai de sécurité est encore actif.\u001fLe mot de passe de sauvegarde est requis.\u001fLe service est indisponible.","Réessayez et vérifiez le délai configuré.\u001fVérifiez la connexion au stockage puis réessayez.\u001fComplétez les options de l’intégration.\u001fAttendez la fin du délai affiché.\u001fEnregistrez le mot de passe puis réessayez.\u001fVérifiez Home Assistant et le stockage.","Disponibilité des sauvegardes\u001fÂge de la sauvegarde\u001fQualité de la sauvegarde\u001fVérification d’intégrité\u001fStockage et redondance\u001fSauvegardes automatiques et planning","Préparation de la vérification d’intégrité\u001fPréparation de la copie de stockage\u001fTéléchargement de la sauvegarde\u001fExtraction de la sauvegarde\u001fExtraction de la sauvegarde chiffrée\u001fLecture et vérification de la base de données\u001fSuppression des données temporaires\u001fActualisation de l’inventaire\u001fLecture du gestionnaire de sauvegardes\u001fExécution de la vérification d’intégrité\u001fTraitement de la demande de vérification\u001fEnregistrement du résultat\u001fActualisation de l’état de protection\u001fEnvoi de la notification\u001fTraitement des notifications\u001fDémarrage de l’intégration\u001fConfiguration des entités\u001fSynchronisation des réparations\u001fFin de la première actualisation\u001fArrêt de l’intégration\u001fChargement de l’état enregistré\u001fPlanification de la vérification automatique\u001fSurveillance de la vérification en arrière-plan\u001fActualisation après vérification\u001fActualisation manuelle\u001fDémarrage de la vérification manuelle\u001fTest de la notification\u001fConfiguration du panneau latéral\u001fArrêt de l’entrée d’intégration\u001fSuppression des données d’intégration","démarré\u001fterminé\u001fen cours\u001fignoré\u001féchoué\u001fannulé"]),
  it: createLocale(["Panoramica backup\u001fStato in tempo reale dei backup di Home Assistant\u001fLa protezione dei backup è corretta\u001fLa protezione dei backup richiede attenzione\u001fI dati dei backup non sono ancora disponibili\u001fPunteggio di salute\u001fStato attuale\u001fRaccomandazione\u001fUltimo backup\u001fDimensione ultimo backup\u001fBackup archiviati\u001fIntegrità\u001fProblemi attivi\u001fNessun problema di backup attivo.\u001fPosizioni di archiviazione\u001fNessuna informazione di archiviazione disponibile.\u001fbackup\u001fUltimo backup\u001fAggiorna\u001fVerifica ultimo backup\u001fImpostazioni\u001fAggiornato\u001fImpossibile completare l’azione.\u001fImpossibile completare l’operazione.\u001fControlla Home Assistant e l’archiviazione e riprova.\u001fPerché questo punteggio?\u001fNon ci sono detrazioni attive.\u001fpunti detratti\u001fUltimo risultato della verifica\u001fVerificato\u001fDurata\u001fDimensione verificata\u001fFile verificati\u001fAvvisi\u001fPassaggio successivo consigliato\u001fStato\u001fNuove voci disponibili\u001fCancella registro\u001fEsporta registro\u001fCancellare tutte le voci del registro?\u001fPersistente\u001fFino al riavvio\u001fFiltro\u001fPanoramica\u001fRegistro live\u001fRegistro live BackupCheckup\u001fCerca nel registro\u001fNessuna voce corrispondente.\u001fIl registro dettagliato è disattivato nelle opzioni dell’integrazione.\u001fLive","Tutto\u001fInfo\u001fAvvisi\u001fErrori","Tutte le operazioni\u001fVerifiche\u001fBackup\u001fNotifiche\u001fSistema","Online\u001fObsoleto\u001fOffline","Motivo\u001fTipo di errore\u001fMotivo\u001fAttivazione\u001fStato\u001fVersione\u001fDestinatari\u001fNotifica\u001fTentativi\u001fRimanenti\u001fErrori\u001fAttivato\u001fPiattaforme","Manuale\u001fAutomatico\u001fAttesa di sicurezza attiva\u001fNon configurato\u001fSì\u001fNo\u001fTest","L’operazione ha superato il tempo limite.\u001fImpossibile raggiungere l’archiviazione.\u001fLa funzione richiesta non è configurata.\u001fL’attesa di sicurezza è ancora attiva.\u001fÈ richiesta la password del backup.\u001fIl servizio non è disponibile.","Riprova e controlla il limite di tempo.\u001fControlla la connessione e riprova.\u001fCompleta le opzioni dell’integrazione.\u001fAttendi la fine del periodo indicato.\u001fSalva la password e riprova.\u001fControlla Home Assistant e l’archiviazione.","Disponibilità backup\u001fEtà del backup\u001fQualità backup\u001fVerifica integrità\u001fArchiviazione e ridondanza\u001fBackup automatici e pianificazione","Preparazione verifica integrità\u001fPreparazione copia di archiviazione\u001fDownload backup\u001fEstrazione backup\u001fEstrazione backup crittografato\u001fLettura e verifica database\u001fRimozione dati temporanei\u001fAggiornamento inventario backup\u001fLettura gestore backup\u001fEsecuzione verifica integrità\u001fElaborazione richiesta di verifica\u001fSalvataggio risultato\u001fAggiornamento stato protezione\u001fInvio notifica\u001fElaborazione notifiche\u001fAvvio integrazione\u001fConfigurazione entità\u001fSincronizzazione riparazioni\u001fCompletamento primo aggiornamento\u001fArresto integrazione\u001fCaricamento stato salvato\u001fPianificazione verifica automatica\u001fMonitoraggio verifica in background\u001fAggiornamento dopo verifica\u001fAggiornamento manuale\u001fAvvio verifica manuale\u001fTest notifica\u001fConfigurazione pannello laterale\u001fArresto voce integrazione\u001fRimozione dati integrazione","avviato\u001fcompletato\u001fin corso\u001fsaltato\u001fnon riuscito\u001fannullato"]),
  nl: createLocale(["Back-upoverzicht\u001fLivestatus van je Home Assistant-back-ups\u001fDe back-upbeveiliging is in orde\u001fDe back-upbeveiliging vereist aandacht\u001fBack-upgegevens zijn nog niet beschikbaar\u001fGezondheidsscore\u001fHuidige status\u001fAanbeveling\u001fLaatste back-up\u001fGrootte laatste back-up\u001fOpgeslagen back-ups\u001fIntegriteit\u001fActieve problemen\u001fGeen actieve back-upproblemen.\u001fOpslaglocaties\u001fGeen opslaginformatie beschikbaar.\u001fback-ups\u001fLaatste back-up\u001fVernieuwen\u001fLaatste back-up controleren\u001fInstellingen\u001fBijgewerkt\u001fDe actie kon niet worden voltooid.\u001fDe bewerking kon niet worden voltooid.\u001fControleer Home Assistant en de opslaglocatie en probeer opnieuw.\u001fWaarom deze score?\u001fEr zijn geen aftrekpunten actief.\u001fpunten afgetrokken\u001fLaatste controleresultaat\u001fGecontroleerd\u001fDuur\u001fGecontroleerde grootte\u001fGecontroleerde bestanden\u001fWaarschuwingen\u001fAanbevolen volgende stap\u001fStatus\u001fNieuwe items beschikbaar\u001fLogboek wissen\u001fLogboek exporteren\u001fAlle live-logboekitems wissen?\u001fPermanent\u001fTot herstart\u001fFilter\u001fOverzicht\u001fLive-logboek\u001fBackupCheckup live-logboek\u001fLogboek doorzoeken\u001fGeen overeenkomende logboekitems.\u001fGedetailleerde livelogging is uitgeschakeld in de integratieopties.\u001fLive","Alles\u001fInfo\u001fWaarschuwingen\u001fFouten","Alle bewerkingen\u001fControles\u001fBack-ups\u001fMeldingen\u001fSysteem","Online\u001fVerouderd\u001fOffline","Reden\u001fFouttype\u001fReden\u001fTrigger\u001fStatus\u001fVersie\u001fOntvangers\u001fMelding\u001fPogingen\u001fResterend\u001fFouten\u001fIngeschakeld\u001fPlatformen","Handmatig\u001fAutomatisch\u001fVeiligheidswachttijd actief\u001fNiet ingesteld\u001fJa\u001fNee\u001fTest","De bewerking overschreed de tijdslimiet.\u001fDe opslaglocatie kon niet worden bereikt.\u001fDe vereiste functie is niet ingesteld.\u001fDe veiligheidswachttijd is nog actief.\u001fHet back-upwachtwoord is vereist.\u001fDe dienst is niet beschikbaar.","Probeer opnieuw en controleer de tijdslimiet.\u001fControleer de opslagverbinding en probeer opnieuw.\u001fVul de integratieopties aan.\u001fWacht tot de getoonde periode voorbij is.\u001fSla het wachtwoord op en probeer opnieuw.\u001fControleer Home Assistant en de opslaglocatie.","Beschikbaarheid back-up\u001fLeeftijd back-up\u001fKwaliteit back-up\u001fIntegriteitscontrole\u001fOpslag en redundantie\u001fAutomatische back-ups en planning","Integriteitscontrole voorbereiden\u001fOpslagkopie voorbereiden\u001fBack-up downloaden\u001fBack-up uitpakken\u001fVersleutelde back-up uitpakken\u001fDatabase lezen en controleren\u001fTijdelijke controlegegevens verwijderen\u001fBack-upinventaris vernieuwen\u001fBack-upbeheer lezen\u001fIntegriteitscontrole uitvoeren\u001fControleverzoek verwerken\u001fControleresultaat opslaan\u001fBack-upstatus bijwerken\u001fMelding verzenden\u001fMeldingen verwerken\u001fIntegratie starten\u001fEntiteiten instellen\u001fReparatiemeldingen synchroniseren\u001fEerste vernieuwing afronden\u001fIntegratie stoppen\u001fOpgeslagen controlestatus laden\u001fAutomatische controle plannen\u001fAchtergrondcontrole bewaken\u001fStatus na controle vernieuwen\u001fHandmatig vernieuwen\u001fHandmatige controle starten\u001fMelding testen\u001fZijpaneel instellen\u001fIntegratie-item stoppen\u001fIntegratiegegevens verwijderen","gestart\u001fvoltooid\u001fbezig\u001fovergeslagen\u001fmislukt\u001fgeannuleerd"]),
  pl: createLocale(["Przegląd kopii\u001fBieżący stan kopii zapasowych Home Assistant\u001fOchrona kopii zapasowych działa prawidłowo\u001fOchrona kopii zapasowych wymaga uwagi\u001fDane kopii zapasowych nie są jeszcze dostępne\u001fOcena kondycji\u001fBieżący stan\u001fZalecenie\u001fNajnowsza kopia\u001fRozmiar najnowszej kopii\u001fZapisane kopie\u001fIntegralność\u001fAktywne problemy\u001fBrak aktywnych problemów z kopiami.\u001fLokalizacje przechowywania\u001fBrak informacji o lokalizacjach.\u001fkopii\u001fNajnowsza kopia\u001fOdśwież\u001fSprawdź najnowszą kopię\u001fUstawienia\u001fZaktualizowano\u001fNie udało się wykonać działania.\u001fNie udało się zakończyć operacji.\u001fSprawdź Home Assistant i magazyn, a następnie ponów.\u001fSkąd ten wynik?\u001fBrak aktywnych odliczeń od wyniku.\u001fodjętych punktów\u001fNajnowszy wynik weryfikacji\u001fSprawdzono\u001fCzas trwania\u001fSprawdzony rozmiar\u001fSprawdzone pliki\u001fOstrzeżenia\u001fZalecany następny krok\u001fStan\u001fDostępne są nowe wpisy\u001fWyczyść dziennik\u001fEksportuj dziennik\u001fWyczyścić wszystkie wpisy dziennika?\u001fTrwały\u001fDo ponownego uruchomienia\u001fFiltr\u001fPrzegląd\u001fDziennik na żywo\u001fDziennik BackupCheckup na żywo\u001fPrzeszukaj dziennik\u001fBrak pasujących wpisów.\u001fSzczegółowy dziennik jest wyłączony w opcjach integracji.\u001fNa żywo","Wszystkie\u001fInfo\u001fOstrzeżenia\u001fBłędy","Wszystkie operacje\u001fKontrole\u001fKopie\u001fPowiadomienia\u001fSystem","Online\u001fNieaktualny\u001fOffline","Powód\u001fTyp błędu\u001fPowód\u001fWyzwalacz\u001fStan\u001fWersja\u001fOdbiorcy\u001fPowiadomienie\u001fPróby\u001fPozostało\u001fBłędy\u001fWłączone\u001fPlatformy","Ręcznie\u001fAutomatycznie\u001fTrwa okres oczekiwania\u001fNie skonfigurowano\u001fTak\u001fNie\u001fTest","Operacja przekroczyła limit czasu.\u001fNie udało się połączyć z magazynem.\u001fWymagana funkcja nie jest skonfigurowana.\u001fOkres bezpieczeństwa nadal trwa.\u001fWymagane jest hasło kopii.\u001fUsługa jest niedostępna.","Spróbuj ponownie i sprawdź limit czasu.\u001fSprawdź połączenie z magazynem i ponów.\u001fUzupełnij opcje integracji.\u001fPoczekaj do końca wskazanego okresu.\u001fZapisz hasło i spróbuj ponownie.\u001fSprawdź Home Assistant i magazyn.","Dostępność kopii\u001fWiek kopii\u001fJakość kopii\u001fKontrola integralności\u001fMagazyn i nadmiarowość\u001fAutomatyczne kopie i harmonogram","Przygotowanie kontroli integralności\u001fPrzygotowanie kopii magazynu\u001fPobieranie kopii\u001fRozpakowywanie kopii\u001fRozpakowywanie zaszyfrowanej kopii\u001fOdczyt i kontrola bazy danych\u001fUsuwanie danych tymczasowych\u001fOdświeżanie spisu kopii\u001fOdczyt menedżera kopii\u001fKontrola integralności\u001fPrzetwarzanie żądania kontroli\u001fZapisywanie wyniku\u001fAktualizowanie stanu ochrony\u001fWysyłanie powiadomienia\u001fPrzetwarzanie powiadomień\u001fUruchamianie integracji\u001fKonfigurowanie encji\u001fSynchronizowanie napraw\u001fKończenie pierwszego odświeżenia\u001fZatrzymywanie integracji\u001fWczytywanie zapisanego stanu\u001fPlanowanie automatycznej kontroli\u001fMonitorowanie kontroli w tle\u001fOdświeżanie po kontroli\u001fRęczne odświeżanie\u001fUruchamianie ręcznej kontroli\u001fTestowanie powiadomienia\u001fKonfigurowanie panelu bocznego\u001fZatrzymywanie wpisu integracji\u001fUsuwanie danych integracji","uruchomiono\u001fzakończono\u001fw toku\u001fpominięto\u001fniepowodzenie\u001fanulowano"]),
  sv: createLocale(["Säkerhetskopieöversikt\u001fLivestatus för dina Home Assistant-säkerhetskopior\u001fSäkerhetskopieringen fungerar korrekt\u001fSäkerhetskopieringen behöver uppmärksamhet\u001fSäkerhetskopiedata är ännu inte tillgängliga\u001fHälsopoäng\u001fAktuell status\u001fRekommendation\u001fSenaste säkerhetskopian\u001fStorlek på senaste säkerhetskopian\u001fLagrade säkerhetskopior\u001fIntegritet\u001fAktiva problem\u001fInga aktiva säkerhetskopieringsproblem.\u001fLagringsplatser\u001fIngen lagringsinformation är tillgänglig.\u001fsäkerhetskopior\u001fSenaste säkerhetskopian\u001fUppdatera\u001fKontrollera senaste säkerhetskopian\u001fInställningar\u001fUppdaterad\u001fÅtgärden kunde inte slutföras.\u001fÅtgärden kunde inte slutföras.\u001fKontrollera Home Assistant och lagringsplatsen och försök igen.\u001fVarför detta värde?\u001fInga avdrag från hälsopoängen är aktiva.\u001fpoäng avdrag\u001fSenaste verifieringsresultat\u001fKontrollerad\u001fVaraktighet\u001fVerifierad storlek\u001fVerifierade filer\u001fVarningar\u001fRekommenderat nästa steg\u001fStatus\u001fNya poster tillgängliga\u001fRensa logg\u001fExportera logg\u001fRensa alla poster i liveloggen?\u001fPermanent\u001fTill omstart\u001fFilter\u001fÖversikt\u001fLivelogg\u001fBackupCheckup-livelogg\u001fSök i loggen\u001fInga matchande loggposter.\u001fDetaljerad liveloggning är inaktiverad i integrationsalternativen.\u001fLive","Alla\u001fInfo\u001fVarningar\u001fFel","Alla åtgärder\u001fKontroller\u001fSäkerhetskopior\u001fAviseringar\u001fSystem","Online\u001fFöråldrad\u001fOffline","Orsak\u001fFeltyp\u001fOrsak\u001fUtlösare\u001fStatus\u001fVersion\u001fMottagare\u001fAvisering\u001fFörsök\u001fÅterstår\u001fFel\u001fAktiverad\u001fPlattformar","Manuell\u001fAutomatisk\u001fSäkerhetsväntetid aktiv\u001fInte konfigurerad\u001fJa\u001fNej\u001fTest","Åtgärden överskred tidsgränsen.\u001fLagringsplatsen kunde inte nås.\u001fDen nödvändiga funktionen är inte konfigurerad.\u001fSäkerhetsväntetiden är fortfarande aktiv.\u001fSäkerhetskopians lösenord krävs.\u001fTjänsten är inte tillgänglig.","Försök igen och kontrollera tidsgränsen.\u001fKontrollera lagringsanslutningen och försök igen.\u001fSlutför integrationsalternativen.\u001fVänta tills den visade tiden har löpt ut.\u001fSpara lösenordet och försök igen.\u001fKontrollera Home Assistant och lagringsplatsen.","Tillgänglighet\u001fSäkerhetskopians ålder\u001fKvalitet\u001fIntegritetskontroll\u001fLagring och redundans\u001fAutomatiska kopior och schema","Förbereder integritetskontroll\u001fFörbereder lagringskopia\u001fHämtar säkerhetskopia\u001fPackar upp säkerhetskopia\u001fPackar upp krypterad säkerhetskopia\u001fLäser och kontrollerar databasen\u001fTar bort tillfälliga kontrolldata\u001fUppdaterar säkerhetskopielistan\u001fLäser säkerhetskopiehanteraren\u001fKör integritetskontroll\u001fBehandlar kontrollbegäran\u001fSparar kontrollresultat\u001fUppdaterar skyddsstatus\u001fSkickar avisering\u001fBehandlar aviseringar\u001fStartar integration\u001fKonfigurerar entiteter\u001fSynkroniserar reparationsmeddelanden\u001fSlutför första uppdateringen\u001fStoppar integration\u001fLäser sparad kontrollstatus\u001fSchemalägger automatisk kontroll\u001fÖvervakar bakgrundskontroll\u001fUppdaterar status efter kontroll\u001fKör manuell uppdatering\u001fStartar manuell kontroll\u001fTestar avisering\u001fKonfigurerar sidopanel\u001fStoppar integrationspost\u001fTar bort integrationsdata","startad\u001fslutförd\u001fpågår\u001föverhoppad\u001fmisslyckad\u001favbruten"]),
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
  clear_activity_log: "button.backup_checkup_clear_activity_log",
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
    this._logLevelFilter = "all";
    this._logTypeFilter = "all";
    this._lastActivitySequence = null;
    this._lastActivityEntryCount = 0;
    this._pendingLogEntries = 0;
    this._scrollLogToBottom = false;
    this._relevantStateRefs = new Map();
    this._viewContext = "";
    this._panelEntitySignature = "";
  }

  set hass(value) {
    const shouldRender = this._relevantStateChanged(value);
    this._hass = value;
    if (shouldRender) this._scheduleRender();
  }

  get hass() {
    return this._hass;
  }

  set panel(value) {
    const entitySignature = JSON.stringify(value?.config?.entities || {});
    this._panel = value;
    if (entitySignature === this._panelEntitySignature) return;
    this._panelEntitySignature = entitySignature;
    this._relevantStateRefs = new Map();
    if (this._hass) this._relevantStateChanged(this._hass);
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

  _relevantStateChanged(hass) {
    const nextRefs = new Map();
    this._relevantEntityIds().forEach((entityId) => {
      nextRefs.set(entityId, hass?.states?.[entityId]);
    });
    const context = [
      hass?.locale?.language || hass?.language || "en",
      Boolean(hass?.user?.is_admin),
    ].join("|");
    const stateChanged = nextRefs.size !== this._relevantStateRefs.size
      || [...nextRefs].some(
        ([entityId, state]) => this._relevantStateRefs.get(entityId) !== state
      );
    const changed = stateChanged || context !== this._viewContext;
    this._relevantStateRefs = nextRefs;
    this._viewContext = context;
    return changed;
  }

  _relevantEntityIds() {
    const entities = this._entities();
    if (this._activeTab === "logs") {
      return [entities.activity_log, entities.clear_activity_log];
    }
    return Object.entries(entities)
      .filter(([key]) => !["activity_log", "clear_activity_log"].includes(key))
      .map(([, entityId]) => entityId);
  }

  _captureScrollPositions() {
    const positions = [];
    const seen = new Set();
    const remember = (element) => {
      if (!element || seen.has(element)) return;
      seen.add(element);
      positions.push({
        element,
        left: Number(element.scrollLeft) || 0,
        top: Number(element.scrollTop) || 0,
      });
    };
    let current = this;
    while (current) {
      remember(current);
      const root = current.getRootNode?.();
      current = current.parentElement || root?.host || null;
    }
    remember(document.scrollingElement);
    return positions;
  }

  _restoreScrollPositions(positions) {
    positions.forEach(({ element, left, top }) => {
      element.scrollLeft = left;
      element.scrollTop = top;
    });
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
    return this._formatDate(value, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  _logTimestamp(value) {
    return this._formatDate(value, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  _formatDate(value, options) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(this._language(), options).format(date);
  }

  _storageRows(agents, text) {
    if (!agents.length) return `<div class="empty">${this._escape(text.noStorage)}</div>`;
    return agents.map((agent) => {
      const tone = this._storageTone(agent);
      const state = agent.error ? "offline" : agent.stale ? "stale" : "online";
      const latest = agent.latest_backup ? this._date(agent.latest_backup) : "—";
      const reason = agent.error ? this._friendlyError(agent.error, text) : "";
      return `
        <div class="storage-row">
          <div class="storage-icon ${tone}"><ha-icon icon="mdi:database"></ha-icon></div>
          <div class="storage-copy">
            <strong>${this._escape(agent.storage_name || agent.storage_reference || "—")}</strong>
            <span>${this._escape(text.lastBackup)}: ${this._escape(latest)}</span>
            ${reason ? `<small>${this._escape(reason)}</small>` : ""}
          </div>
          <span class="status-badge ${tone}">${this._escape(text.storageStates?.[state] || this._humanize(state))}</span>
          <div class="storage-count">${this._escape(agent.backup_count ?? 0)} <span>${this._escape(text.backups)}</span></div>
        </div>`;
    }).join("");
  }

  _storageTone(agent) {
    if (agent.error) return "danger";
    return agent.stale ? "warning" : "good";
  }

  _errorKey(value) {
    const code = String(value || "").toLowerCase();
    if (code.includes("timeout")) return "timeout";
    if (code.includes("connection") || code.includes("network")) return "connection_error";
    if (code.includes("config")) return "not_configured";
    if (code.includes("cooldown")) return "cooldown";
    if (code.includes("password")) return "password_required";
    if (code.includes("unavailable") || code.includes("not_ready")) return "unavailable";
    return code;
  }

  _friendlyError(value, text) {
    const key = this._errorKey(value);
    return text.errorMessages?.[key] || text.unknownError || this._humanize(value);
  }

  _friendlyRecommendation(value, text) {
    const key = this._errorKey(value);
    return text.errorRecommendations?.[key] || text.unknownRecommendation || "";
  }

  _healthRows(deductions, text) {
    const rows = Object.entries(deductions || {})
      .filter(([, value]) => Number(value) > 0)
      .sort((left, right) => Number(right[1]) - Number(left[1]));
    if (!rows.length) return `<div class="empty success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.noDeductions)}</div>`;
    return rows.map(([key, value]) => `<div class="explanation-row">
      <span>${this._escape(text.healthComponents?.[key] || this._humanize(key))}</span>
      <strong>−${this._escape(value)} ${this._escape(text.pointsDeducted)}</strong>
    </div>`).join("");
  }

  _integrityRows(integrity, text) {
    const attributes = integrity?.attributes || {};
    const values = [
      [text.statusLabel, this._formatState(integrity)],
      [text.checkedAt, this._date(attributes.checked_at)],
      [text.duration, attributes.duration_seconds == null ? "—" : `${attributes.duration_seconds} s`],
      [text.verifiedSize, attributes.verified_size_mb == null ? "—" : `${attributes.verified_size_mb} MB`],
      [text.filesChecked, attributes.file_count ?? "—"],
      [text.warnings, Array.isArray(attributes.warnings) ? attributes.warnings.length : 0],
    ];
    const error = attributes.error_code;
    const detailRows = values.map(([label, value]) => `<div class="explanation-row"><span>${this._escape(label)}</span><strong>${this._escape(value)}</strong></div>`).join("");
    if (!error) return detailRows;
    const recommendation = this._friendlyRecommendation(error, text);
    return `${detailRows}<div class="result-advice"><strong>${this._escape(this._friendlyError(error, text))}</strong>${recommendation ? `<span>${this._escape(text.nextStep)}: ${this._escape(recommendation)}</span>` : ""}</div>`;
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
      integrityState: integrity,
      healthDeductions: scoreState?.attributes?.component_deductions || {},
      isAdmin: Boolean(this._hass.user?.is_admin),
      verifyState: this._state("verify"),
      refreshState: this._state("refresh"),
      activityEntries: Array.isArray(activity?.attributes?.entries)
        ? activity.attributes.entries : [],
      activityEnabled: Boolean(activity?.attributes?.enabled),
      activityPersistent: Boolean(activity?.attributes?.persistent),
      activityRetentionDays: activity?.attributes?.retention_days,
      activitySequence: Number(activity?.state) || 0,
      clearActivityState: this._state("clear_activity_log"),
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
      <article class="card">
        <div class="card-title"><ha-icon icon="mdi:chart-donut"></ha-icon><h3>${this._escape(model.text.healthDetails)}</h3></div>
        <div class="rows">${this._healthRows(model.healthDeductions, model.text)}</div>
      </article>
      <article class="card">
        <div class="card-title"><ha-icon icon="mdi:shield-search"></ha-icon><h3>${this._escape(model.text.integrityDetails)}</h3></div>
        <div class="rows">${this._integrityRows(model.integrityState, model.text)}</div>
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

  _activityDetails(record, text) {
    const details = Object.entries(record.details || {})
      .filter(([key]) => key !== "progress_percent")
      .filter(([key]) => key !== "error_type" || !record.details?.error_code)
      .map(([key, value]) => {
        const label = text.detailLabels?.[key] || this._humanize(key);
        const translatedValue = ["error_code", "reason", "error_type"].includes(key)
          ? this._friendlyError(value, text)
          : text.detailValues?.[String(value)] || value;
        return `${label}: ${translatedValue}`;
      });
    return details.join(" · ");
  }

  _activityType(record) {
    const action = String(record.action || "");
    if (action.includes("notification")) return "notification";
    if (action.includes("backup") || action.includes("storage_copy")) return "backup";
    if (action.includes("integrity") || action.includes("verification")) return "check";
    return "system";
  }

  _activityAdvice(record, text) {
    if (!["failed", "skipped", "cancelled"].includes(record.outcome)) return "";
    const code = record.details?.error_code || record.details?.reason || record.details?.error_type;
    if (!code) return "";
    const message = this._friendlyError(code, text);
    const recommendation = this._friendlyRecommendation(code, text);
    return `<div class="log-advice"><strong>${this._escape(message)}</strong>${recommendation ? `<span>${this._escape(text.nextStep)}: ${this._escape(recommendation)}</span>` : ""}</div>`;
  }

  _levelMatches(record) {
    if (this._logLevelFilter === "all") return true;
    if (this._logLevelFilter === "error") {
      return ["error", "critical"].includes(record.level) || record.outcome === "failed";
    }
    return record.level === this._logLevelFilter;
  }

  _filterButtons(values, selected, attribute, labels) {
    return values.map((value) => `<button class="filter-chip ${selected === value ? "active" : ""}" ${attribute}="${value}">${this._escape(labels[value])}</button>`).join("");
  }

  _logRows(records, text) {
    const query = this._logSearch.trim().toLocaleLowerCase(this._language());
    const filtered = records.filter((record) => {
      if (!this._levelMatches(record)) return false;
      if (this._logTypeFilter !== "all" && this._activityType(record) !== this._logTypeFilter) return false;
      const searchable = `${record.action} ${record.outcome} ${this._activityMessage(record, text)} ${this._activityDetails(record, text)}`;
      return !query || searchable.toLocaleLowerCase(this._language()).includes(query);
    });
    if (!filtered.length) return `<div class="log-empty">${this._escape(text.noLogs)}</div>`;
    return filtered.map((record) => {
      const details = this._activityDetails(record, text);
      const detailLine = details ? `<span>${this._escape(details)}</span>` : "";
      const level = ["warning", "error", "critical"].includes(record.level)
        ? record.level : "info";
      return `<div class="log-row ${level}">
        <time>${this._escape(this._logTimestamp(record.timestamp))}</time>
        <div class="log-message"><strong>${this._escape(this._activityMessage(record, text))}</strong>${this._activityAdvice(record, text)}</div>
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
        <span class="live-indicator"><i></i>${this._escape(model.text.live)} · ${this._escape(model.activityPersistent ? model.text.persistentLog : model.text.runtimeLog)}</span>
      </div>
      <div class="log-filters" aria-label="${this._escape(model.text.filterLabel)}">
        <div>${this._filterButtons(["all", "info", "warning", "error"], this._logLevelFilter, "data-level-filter", model.text.levelLabels)}</div>
        <div>${this._filterButtons(["all", "check", "backup", "notification", "system"], this._logTypeFilter, "data-type-filter", model.text.typeLabels)}</div>
      </div>
      ${this._pendingLogEntries ? `<button class="new-entries" data-new-entries><ha-icon icon="mdi:arrow-down"></ha-icon>${this._escape(model.text.newEntries)} (${this._pendingLogEntries})</button>` : ""}
      <article class="log-console">
        <div class="log-heading"><h2>${this._escape(model.text.logTitle)}</h2><div>
          <button class="log-action" data-export-log><ha-icon icon="mdi:download-outline"></ha-icon>${this._escape(model.text.exportLog)}</button>
          ${model.isAdmin ? `<button class="log-action danger" data-action="clear_activity_log" ${this._buttonDisabled(model.clearActivityState, "clear_activity_log") ? "disabled" : ""}><ha-icon icon="mdi:delete-sweep-outline"></ha-icon>${this._escape(model.text.clearLog)}</button>` : ""}
        </div></div>
        <div class="log-lines">${this._logRows(model.activityEntries, model.text)}</div>
      </article>
    </section>`;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const scrollPositions = this._captureScrollPositions();
    const previousLog = this.shadowRoot.querySelector(".log-lines");
    const previousLogState = previousLog ? {
      top: previousLog.scrollTop,
      atBottom: previousLog.scrollHeight - previousLog.scrollTop - previousLog.clientHeight < 48,
    } : null;
    const restoreSearchFocus = this.shadowRoot.activeElement?.hasAttribute("data-log-search");
    const model = this._renderModel();
    if (this._activeTab === "logs") {
      const entryCount = model.activityEntries.length;
      if (this._lastActivitySequence === null) {
        this._scrollLogToBottom = true;
      } else if (model.activitySequence > this._lastActivitySequence && entryCount >= this._lastActivityEntryCount) {
        const added = Math.max(1, entryCount - this._lastActivityEntryCount);
        if (previousLogState?.atBottom) this._scrollLogToBottom = true;
        else this._pendingLogEntries += added;
      }
      if (entryCount < this._lastActivityEntryCount) this._pendingLogEntries = 0;
      this._lastActivitySequence = model.activitySequence;
      this._lastActivityEntryCount = entryCount;
    }
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
        if (this._activeTab === "logs") {
          this._scrollLogToBottom = true;
          this._pendingLogEntries = 0;
        }
        this._relevantStateChanged(this._hass);
        this._scheduleRender();
      });
    });
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "clear_activity_log" && !window.confirm(model.text.clearConfirm)) return;
        this._runAction(action);
      });
    });
    this.shadowRoot.querySelectorAll("[data-level-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        this._logLevelFilter = button.dataset.levelFilter;
        this._scheduleRender();
      });
    });
    this.shadowRoot.querySelectorAll("[data-type-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        this._logTypeFilter = button.dataset.typeFilter;
        this._scheduleRender();
      });
    });
    this.shadowRoot.querySelector("[data-export-log]")?.addEventListener("click", () => this._exportActivityLog(model));
    this.shadowRoot.querySelector("[data-new-entries]")?.addEventListener("click", () => {
      const log = this.shadowRoot.querySelector(".log-lines");
      if (log) log.scrollTo({ top: log.scrollHeight, behavior: "smooth" });
      this._pendingLogEntries = 0;
      this._scheduleRender();
    });
    const search = this.shadowRoot.querySelector("[data-log-search]");
    search?.addEventListener("input", (event) => {
      this._logSearch = event.target.value;
      this._scheduleRender();
    });
    if (restoreSearchFocus && search) {
      search.focus({ preventScroll: true });
      search.setSelectionRange(search.value.length, search.value.length);
    }
    const currentLog = this.shadowRoot.querySelector(".log-lines");
    if (currentLog) {
      if (this._scrollLogToBottom || !previousLogState) {
        currentLog.scrollTop = currentLog.scrollHeight;
        this._scrollLogToBottom = false;
      } else {
        currentLog.scrollTop = previousLogState.top;
      }
      currentLog.addEventListener("scroll", () => {
        const atBottom = currentLog.scrollHeight - currentLog.scrollTop - currentLog.clientHeight < 48;
        if (atBottom && this._pendingLogEntries) {
          this._pendingLogEntries = 0;
          this._scheduleRender();
        }
      }, { passive: true });
    }
    this._restoreScrollPositions(scrollPositions);
  }

  _exportActivityLog(model) {
    const payload = {
      exported_at: new Date().toISOString(),
      privacy: "Backup names, IDs, paths, passwords and content are excluded.",
      persistent: model.activityPersistent,
      retention_days: model.activityRetentionDays,
      entries: model.activityEntries,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `backup-checkup-live-log-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
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
      .storage-copy small { color:#d84b55; font-size:11px; line-height:1.35; }
      .status-badge { flex:0 0 auto; padding:5px 9px; border-radius:999px; background:rgba(96,125,139,.13); color:#607d8b; font-size:11px; font-weight:700; }
      .status-badge.good { background:rgba(46,157,104,.13); color:#2e9d68; }
      .status-badge.warning { background:rgba(231,154,36,.13); color:#b87300; }
      .status-badge.danger { background:rgba(216,75,85,.13); color:#d84b55; }
      .storage-count { text-align:right; font-size:17px; font-weight:650; }
      .storage-count span { display:block; color:var(--secondary-text-color); font-size:11px; font-weight:400; }
      .empty { min-height:52px; display:flex; align-items:center; gap:9px; color:var(--secondary-text-color); }
      .empty.success ha-icon { color:#2e9d68; }
      .explanation-row { min-height:44px; display:flex; align-items:center; justify-content:space-between; gap:16px; border-top:1px solid var(--divider-color); }
      .explanation-row:first-child { border-top:0; }
      .explanation-row span { color:var(--secondary-text-color); font-size:12px; }
      .explanation-row strong { text-align:right; font-size:13px; }
      .result-advice { display:flex; flex-direction:column; gap:5px; margin-top:12px; padding:12px; border-radius:11px; background:rgba(216,75,85,.10); }
      .result-advice strong { color:#d84b55; }
      .result-advice span { color:var(--secondary-text-color); font-size:12px; line-height:1.4; }
      .log-view { display:flex; flex-direction:column; gap:16px; }
      .log-toolbar { display:flex; align-items:center; gap:14px; }
      .log-toolbar label { flex:1; min-height:44px; display:flex; align-items:center; gap:9px; padding:0 13px; border:1px solid var(--divider-color); border-radius:12px; background:var(--card-background-color); }
      .log-toolbar label:focus-within { border-color:var(--primary-color); box-shadow:0 0 0 1px var(--primary-color); }
      .log-toolbar input { width:100%; border:0; outline:0; background:transparent; color:var(--primary-text-color); font:inherit; }
      .log-filters { display:flex; flex-direction:column; gap:8px; }
      .log-filters > div { display:flex; flex-wrap:wrap; gap:7px; }
      .filter-chip, .log-action, .new-entries { border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color); font:inherit; cursor:pointer; }
      .filter-chip { min-height:34px; padding:0 12px; border-radius:999px; font-size:12px; }
      .filter-chip.active { border-color:var(--primary-color); background:color-mix(in srgb, var(--primary-color) 12%, var(--card-background-color)); color:var(--primary-color); font-weight:700; }
      .new-entries { align-self:center; min-height:38px; display:flex; align-items:center; gap:7px; padding:0 14px; border-radius:999px; color:var(--primary-color); font-size:12px; font-weight:700; }
      .live-indicator { display:flex; align-items:center; gap:7px; color:var(--primary-color); font-size:13px; font-weight:700; }
      .live-indicator i { width:9px; height:9px; border-radius:50%; background:var(--primary-color); box-shadow:0 0 0 4px color-mix(in srgb, var(--primary-color) 18%, transparent); }
      .log-console { min-height:520px; overflow:hidden; border:1px solid var(--divider-color); border-radius:16px; background:var(--card-background-color); }
      .log-heading { min-height:58px; display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 14px 10px 18px; border-bottom:1px solid var(--divider-color); }
      .log-heading h2 { margin:0; font-size:18px; }
      .log-heading > div { display:flex; flex-wrap:wrap; gap:7px; justify-content:flex-end; }
      .log-action { min-height:36px; display:flex; align-items:center; gap:6px; padding:0 10px; border-radius:9px; font-size:12px; }
      .log-action.danger { color:#d84b55; }
      .log-action:disabled { opacity:.45; cursor:default; }
      .log-lines { max-height:68vh; overflow:auto; padding:8px 0; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
      .log-row { display:grid; grid-template-columns:190px minmax(250px, .9fr) minmax(220px, 1.1fr); gap:14px; padding:8px 18px; border-left:3px solid transparent; font-size:12px; line-height:1.45; }
      .log-row:hover { background:color-mix(in srgb, var(--primary-color) 7%, transparent); }
      .log-row time { color:var(--secondary-text-color); }
      .log-row strong { color:#2e9d68; }
      .log-message { display:flex; flex-direction:column; gap:5px; }
      .log-advice { display:flex; flex-direction:column; gap:3px; padding:7px 9px; border-radius:8px; background:rgba(216,75,85,.10); }
      .log-advice strong { color:#d84b55 !important; }
      .log-advice span { color:var(--secondary-text-color); font-family:var(--paper-font-body1_-_font-family, system-ui, sans-serif); font-size:11px; }
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

if (!customElements.get(PANEL_ELEMENT_NAME)) {
  customElements.define(PANEL_ELEMENT_NAME, BackupCheckupPanel);
}
