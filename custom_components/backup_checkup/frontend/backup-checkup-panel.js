const PANEL_ELEMENT_NAME = "backup-checkup-panel-v3-0-12-r1";

const TRANSLATION_SEPARATOR = "\u001f";
const PACKED_TRANSLATION_KEYS = Object.freeze({"scalar":"dashboard\u001fsubtitle\u001fhealthy\u001fattention\u001funavailable\u001fhealthScore\u001fstatus\u001frecommendation\u001flatestBackup\u001fbackupSize\u001fstoredBackups\u001fintegrity\u001fproblems\u001fnoProblems\u001fstorage\u001fnoStorage\u001fbackups\u001flastBackup\u001frefresh\u001fverify\u001fsettings\u001fupdated\u001factionFailed\u001funknownError\u001funknownRecommendation\u001fhealthDetails\u001fnoDeductions\u001fpointsDeducted\u001fintegrityDetails\u001fcheckedAt\u001fduration\u001fverifiedSize\u001ffilesChecked\u001fwarnings\u001fnextStep\u001fstatusLabel\u001fnewEntries\u001fclearLog\u001fexportLog\u001fclearConfirm\u001fpersistentLog\u001fruntimeLog\u001ffilterLabel\u001foverviewTab\u001flogTab\u001flogTitle\u001fsearchLogs\u001fnoLogs\u001floggingDisabled\u001flive","levelLabels":"all\u001finfo\u001fwarning\u001ferror","typeLabels":"all\u001fcheck\u001fbackup\u001fnotification\u001fsystem","storageStates":"online\u001fstale\u001foffline","detailLabels":"error_code\u001ferror_type\u001freason\u001fsource\u001fstatus\u001fversion\u001ftarget_count\u001fnotification_type\u001fretry_attempts\u001fremaining\u001ffailures\u001fenabled\u001fplatform_count","detailValues":"manual\u001fautomatic\u001fcooldown\u001fnot_configured\u001ftrue\u001ffalse\u001ftest","errorMessages":"timeout\u001fconnection_error\u001fnot_configured\u001fcooldown\u001fpassword_required\u001funavailable","errorRecommendations":"timeout\u001fconnection_error\u001fnot_configured\u001fcooldown\u001fpassword_required\u001funavailable","healthComponents":"availability\u001ffreshness\u001fbackup_quality\u001fintegrity\u001fstorage\u001fautomation","activityActions":"verification_prepare\u001fstorage_copy_prepare\u001fbackup_download\u001fbackup_extract\u001fencrypted_backup_extract\u001fdatabase_read\u001ftemporary_data_cleanup\u001finventory_refresh\u001fbackup_manager_read\u001fintegrity_check\u001fintegrity_check_request\u001fintegrity_result_persist\u001fhealth_state\u001fnotification_send\u001fnotification_processing\u001fconfig_entry_setup\u001fentity_platform_setup\u001frepair_issue_sync\u001ffirst_refresh\u001fcoordinator_shutdown\u001fintegrity_state_load\u001fintegrity_check_schedule\u001fintegrity_background_task\u001fpost_verification_refresh\u001fservice_refresh\u001fservice_verify_latest_backup\u001fservice_test_notification\u001fpanel_setup\u001fconfig_entry_unload\u001fconfig_entry_remove","activityOutcomes":"started\u001fcompleted\u001fchanged\u001fskipped\u001ffailed\u001fcancelled"});
const TRANSLATION_KEYS = Object.freeze(Object.fromEntries(
  Object.entries(PACKED_TRANSLATION_KEYS).map(([group, keys]) => [group, keys.split(TRANSLATION_SEPARATOR)])
));

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

const unpackNestedTranslation = (paths, packed) => {
  const translation = {};
  const values = packed.split(TRANSLATION_SEPARATOR);
  paths.forEach((path, index) => {
    const segments = path.split(".");
    const leaf = segments.pop();
    const parent = segments.reduce((current, segment) => {
      current[segment] ||= {};
      return current[segment];
    }, translation);
    parent[leaf] = values[index];
  });
  return translation;
};

const RECOVERY_CHECK_KEYS = Object.freeze([
  "backup_available",
  "backup_current",
  "backup_complete",
  "homeassistant_included",
  "database_included",
  "integrity_verified",
  "database_verified",
  "independent_copy",
  "multiple_failure_domains",
  "copy_sizes_consistent",
  "content_stable",
  "preparedness_checklist_complete",
  "external_dependencies_protected",
  "simulated_restore_passed",
  "test_restore_documented",
]);

const RECOVERY_TEXT_PATHS_1 = Object.freeze("tab\u001ftitle\u001fsubtitle\u001fscore\u001fprotectionCheck\u001fevidenceTitle\u001fevidenceLabels.not_recoverable\u001fevidenceLabels.limited\u001fevidenceLabels.monitored\u001fevidenceLabels.structurally_verified\u001fevidenceLabels.runtime_ready\u001fevidenceLabels.fully_tested\u001fevidenceDescriptions.not_recoverable\u001fevidenceDescriptions.limited\u001fevidenceDescriptions.monitored\u001fevidenceDescriptions.structurally_verified\u001fevidenceDescriptions.runtime_ready\u001fevidenceDescriptions.fully_tested\u001fprofileLabels.compact\u001fprofileLabels.balanced\u001fprofileLabels.extended\u001fprofileLabels.enterprise\u001fadaptiveTitle\u001fopenRisksTitle\u001fnoOpenRisks\u001friskLabels.backup_stale\u001friskLabels.independent_copy_missing\u001friskLabels.backup_content_regression\u001friskLabels.external_dependency_unprotected\u001friskLabels.external_dependency_confirmation_required\u001ftechnicalDetails\u001foptionalEvidence\u001fnoDetectedDependencies\u001fstatus\u001frecommendation\u001fchecks\u001fdeductions\u001fnoDeductions\u001fpointsDeducted\u001fpassed\u001ffailed\u001funknown\u001freadyMessage\u001flimitedMessage\u001finsufficientMessage\u001funknownMessage\u001finventoryTitle\u001fcomparisonTitle\u001fstorageTitle\u001fbaselineMissing\u001fnoContentChanges\u001fcontentChanged\u001fcontentRegression\u001fbackupReference\u001fbaselineReference\u001fhomeAssistant\u001fdatabase\u001faddons\u001ffolders\u001fssl\u001fshare\u001fmedia\u001ffailedComponents\u001fcopies\u001fclassifiedCopies\u001funknownCopies\u001ffailureDomains\u001foffDeviceCopy\u001findependentCopy\u001fstorageClasses\u001fpresent\u001fmissing\u001fnotKnown\u001fyes\u001fno\u001fadded\u001fremoved\u001faddedAddons\u001fremovedAddons\u001faddedFolders\u001fremovedFolders\u001fcriticalMissing\u001fpreparednessTitle\u001fpreparednessIntro\u001fdependenciesTitle\u001fdependenciesIntro\u001freviewInterval\u001fdetected\u001fexpired\u001fadminOnly\u001fsimulationTitle\u001fsimulationIntro\u001fsimulationRun\u001fsimulationActivity\u001fsimulationStatus\u001fsimulationLive\u001fsimulationSafety\u001fsimulationStage\u001fsimulationProgress\u001fsimulationChecksPassed\u001fsimulationChecksOpen\u001fsimulationChecksFailed\u001fsimulationArchives\u001fsimulationFiles\u001fsimulationSize\u001fsimulationDuration\u001fblockingFailures\u001fsimulationWarnings\u001fsimulationStatusLabels.passed\u001fsimulationStatusLabels.warning\u001fsimulationStatusLabels.failed\u001fsimulationStatusLabels.running\u001fsimulationStatusLabels.aborted\u001fsimulationStatusLabels.password_required\u001fsimulationStatusLabels.inconclusive\u001fsimulationStatusLabels.not_run\u001fsimulationStageLabels.prepare\u001fsimulationStageLabels.storage\u001fsimulationStageLabels.download\u001fsimulationStageLabels.archives\u001fsimulationStageLabels.database\u001fsimulationStageLabels.evaluate\u001fsimulationStageLabels.cleanup\u001fsimulationStageLabels.complete\u001fsimulationStageStateLabels.pending\u001fsimulationStageStateLabels.running\u001fsimulationStageStateLabels.passed\u001fsimulationStageStateLabels.warning\u001fsimulationStageStateLabels.failed\u001fsimulationStageStateLabels.not_applicable\u001fruntimeTitle\u001fruntimeIntro\u001fruntimeStatus\u001fruntimeLive\u001fruntimeProgress\u001fruntimeSafety\u001fruntimeUnavailable\u001fruntimeStatusLabels.not_available\u001fruntimeStatusLabels.not_run\u001fruntimeStatusLabels.running\u001fruntimeStatusLabels.passed\u001fruntimeStatusLabels.failed\u001fruntimeStatusLabels.aborted\u001fruntimeStatusLabels.inconclusive\u001fruntimeStageLabels.runtime_prepare\u001fruntimeStageLabels.runtime_upload\u001fruntimeStageLabels.runtime_restore\u001fruntimeStageLabels.runtime_boot\u001fruntimeStageLabels.runtime_probe\u001fruntimeStageLabels.runtime_cleanup\u001fruntimeStageLabels.runtime_complete\u001frestoreTestTitle\u001frestoreTestIntro\u001frestoreTestMissing\u001frestoreTestDate\u001frestoreTestResult\u001frestoreTestScope\u001frestoreTestAge\u001frestoreTestValid\u001frestoreTestExpired\u001frecordRestoreTest\u001frestoreResultLabels.successful\u001frestoreResultLabels.failed\u001frestoreScopeLabels.full\u001frestoreScopeLabels.partial\u001fplanTitle\u001fplanIntro\u001fplanGenerated\u001fplanWarnings\u001fexportMarkdown\u001fexportHtml\u001fexportJson\u001fnoPlan\u001fchecklistLabels.backup_password_available\u001fchecklistLabels.storage_access_documented\u001fchecklistLabels.restore_method_known\u001fchecklistLabels.replacement_hardware_available\u001fchecklistLabels.network_access_documented\u001fchecklistLabels.recovery_contacts_documented\u001fdependencyLabels.external_database\u001fdependencyLabels.mqtt\u001fdependencyLabels.zigbee\u001fdependencyLabels.zwave\u001fdependencyLabels.thread\u001fdependencyLabels.esphome\u001fdependencyLabels.network_storage\u001fdependencyLabels.reverse_proxy\u001fdependencyLabels.certificates\u001fdependencyLabels.cloud_services\u001fchecklistStatusLabels.unknown\u001fchecklistStatusLabels.confirmed\u001fchecklistStatusLabels.missing\u001fchecklistStatusLabels.not_required\u001fdependencyStatusLabels.unknown\u001fdependencyStatusLabels.protected\u001fdependencyStatusLabels.unprotected\u001fdependencyStatusLabels.not_applicable\u001fstorageClassLabels.local_device\u001fstorageClassLabels.direct_attached\u001fstorageClassLabels.local_network\u001fstorageClassLabels.remote\u001fstorageClassLabels.cloud\u001fstorageClassLabels.unknown\u001fcheckLabels.backup_available\u001fcheckLabels.backup_current\u001fcheckLabels.backup_complete\u001fcheckLabels.homeassistant_included\u001fcheckLabels.database_included\u001fcheckLabels.integrity_verified\u001fcheckLabels.database_verified\u001fcheckLabels.independent_copy\u001fcheckLabels.multiple_failure_domains\u001fcheckLabels.copy_sizes_consistent\u001fcheckLabels.content_stable\u001fcheckLabels.preparedness_checklist_complete\u001fcheckLabels.external_dependencies_protected\u001fcheckLabels.simulated_restore_passed\u001fcheckLabels.test_restore_documented".split(TRANSLATION_SEPARATOR));
const RECOVERY_TEXT_PATHS_2 = Object.freeze("tab\u001ftitle\u001fscore\u001fstatus\u001frecommendation\u001fchecks\u001fdeductions".split(TRANSLATION_SEPARATOR));

const RECOVERY_TEXT = Object.freeze({
  en: unpackNestedTranslation(RECOVERY_TEXT_PATHS_1, "Recovery\u001fRecovery readiness\u001fCan Home Assistant be restored after a total system failure?\u001fRecovery score\u001fCheck backup protection\u001fVerified recovery level\u001fNot recoverable\u001fLimited\u001fMonitored\u001fStructurally verified\u001fRuntime start verified\u001fFully tested\u001fNo usable backup is available.\u001fA blocker prevents a reliable recovery.\u001fThe backup is monitored but has not yet been structurally verified.\u001fThe current backup was downloaded, decrypted when required, and read completely.\u001fAn isolated Home Assistant test instance also started successfully.\u001fA successful full external test restore is documented.\u001fCompact\u001fBalanced\u001fExtended\u001fServer\u001fAdaptive scope\u001fOpen risks\u001fNo blocking recovery risks were detected.\u001fThe latest backup is too old\u001fNo independent backup copy was detected\u001fPreviously included backup contents are missing\u001fAn external dependency is not protected\u001fConfirm the protection of an automatically detected dependency\u001fTechnical details and optional preparedness\u001fOptional additional evidence\u001fNo external dependency requiring confirmation was detected.\u001fRecovery status\u001fPriority action\u001fRecovery checks\u001fScore deductions\u001fNo recovery-score deductions are active.\u001fpoints deducted\u001fPassed\u001fNeeds action\u001fNot assessed\u001fThe recovery foundation is ready.\u001fRecovery is possible, but important gaps remain.\u001fRecovery readiness is insufficient.\u001fRecovery readiness cannot be assessed yet.\u001fContents of the latest backup\u001fCompared with the previous complete backup\u001fStorage resilience\u001fNo previous complete backup is available for comparison.\u001fNo relevant content changes were detected.\u001fThe backup scope changed without losing required contents.\u001fPreviously included contents are missing or incomplete.\u001fBackup reference\u001fComparison backup\u001fHome Assistant data\u001fDatabase\u001fAdd-ons\u001fFolders\u001fSSL\u001fShare\u001fMedia\u001fFailed components\u001fBackup copies\u001fClassified copies\u001fUnclassified copies\u001fIndependent failure domains\u001fCopy outside the Home Assistant device\u001fIndependent copy confirmed\u001fStorage classes\u001fPresent\u001fMissing\u001fNot known\u001fYes\u001fNo\u001fAdded\u001fRemoved\u001fAdded add-ons\u001fRemoved add-ons\u001fAdded folders\u001fRemoved folders\u001fCritical folders missing\u001fGuided emergency checklist\u001fConfirm only whether the required information is available. Passwords, paths and notes are never stored here.\u001fExternal dependencies\u001fBackupCheckup shows only automatically detected or previously configured dependencies. Confirm whether detected external data is protected separately.\u001fConfirmations expire after {days} days and must then be reviewed again.\u001fDetected\u001fReview expired\u001fOnly Home Assistant administrators can change these states.\u001fBackup protection check\u001fRuns the real protected read pipeline: the backup is downloaded, decrypted when required, and every archive is read without restoring or changing the live system.\u001fCheck backup protection\u001fStarting restore simulation\u001fSimulation status\u001fSimulation in progress\u001fNo restore endpoint is called and no production data is written.\u001fCurrent step\u001fTechnical progress\u001fPassed checks\u001fOpen checks\u001fBlocking checks\u001fArchives read\u001fFiles read\u001fData read\u001fRuntime\u001fBlocking failures\u001fOpen simulation warnings\u001fReady\u001fReady with warnings\u001fNot ready\u001fRunning\u001fAborted by a safety limit\u001fBackup password required\u001fResult inconclusive\u001fNot run\u001fPrepare simulation\u001fSelect storage copy\u001fDownload backup\u001fRead metadata and archives\u001fCheck database\u001fEvaluate restore plan\u001fRemove temporary data\u001fComplete simulation\u001fPending\u001fRunning\u001fPassed\u001fWarning\u001fFailed\u001fNot applicable\u001fIsolated Home Assistant start\u001fAfter the structural check, the optional runner restores the verified backup into a temporary, network-isolated instance and follows its startup live.\u001fRuntime test status\u001fEphemeral test instance is running\u001fRunner progress\u001fThe test instance has no access to the home network. All temporary data is removed after the run.\u001fThe optional BackupCheckup Runtime Runner has not been detected.\u001fRunner not available\u001fNot run\u001fRunning\u001fRuntime start verified\u001fStartup failed\u001fStopped by a safety limit\u001fResult inconclusive\u001fPrepare isolated runner\u001fTransfer verified backup\u001fRestore temporary configuration\u001fStart Home Assistant\u001fWait for runtime readiness\u001fRemove temporary instance\u001fComplete runtime test\u001fDocumented test restore\u001fOptional additional evidence. A documented external restore is no longer required for structural readiness.\u001fNo test restore has been documented yet.\u001fTested on\u001fResult\u001fScope\u001fAge\u001fCurrent\u001fExpired\u001fRecord test restore\u001fSuccessful\u001fFailed\u001fFull restore\u001fPartial restore\u001fEmergency recovery plan\u001fGenerated locally from the current recovery assessment. The exports contain no passwords, tokens, paths, hostnames, IP addresses or backup names.\u001fGenerated\u001fOpen risks\u001fExport Markdown\u001fExport HTML\u001fExport JSON\u001fNo recovery plan is available yet.\u001fBackup password is retrievable\u001fAccess to external backup storage is documented\u001fThe restore procedure is known\u001fReplacement hardware or installation media is available\u001fRequired network access is documented\u001fRequired contacts and account ownership are documented\u001fExternal database\u001fMQTT broker\u001fZigbee coordinator\u001fZ-Wave controller\u001fThread / Matter infrastructure\u001fESPHome configuration\u001fNetwork storage / NAS\u001fReverse proxy\u001fCertificates\u001fCloud services and API access\u001fNot assessed\u001fConfirmed\u001fMissing\u001fNot required\u001fNot assessed\u001fProtected separately\u001fNot protected\u001fNot applicable\u001fHome Assistant device\u001fDirectly attached storage\u001fLocal network / NAS\u001fRemote storage\u001fCloud storage\u001fUnknown\u001fBackup available\u001fBackup is current\u001fBackup is complete\u001fHome Assistant data included\u001fDatabase included\u001fIntegrity verified\u001fDatabase verified\u001fIndependent copy available\u001fMultiple failure domains available\u001fCopy sizes are consistent\u001fBackup contents remain complete\u001fGuided emergency checklist complete\u001fExternal dependencies protected\u001fSimulated restore test passed\u001fSuccessful full test restore documented"),
  de: unpackNestedTranslation(RECOVERY_TEXT_PATHS_1, "Notfallvorsorge\u001fWiederherstellungsbereitschaft\u001fKann Home Assistant nach einem vollständigen Systemausfall wiederhergestellt werden?\u001fRecovery Readiness Score\u001fBackup-Schutz prüfen\u001fBestätigte Nachweisstufe\u001fNicht wiederherstellbar\u001fEingeschränkt\u001fÜberwacht\u001fStrukturell bestätigt\u001fStartfähigkeit bestätigt\u001fVollständig erprobt\u001fEs ist kein nutzbares Backup vorhanden.\u001fEin blockierendes Problem verhindert eine verlässliche Wiederherstellung.\u001fDas Backup wird überwacht, wurde aber noch nicht vollständig strukturell geprüft.\u001fDas aktuelle Backup wurde geladen, bei Bedarf entschlüsselt und vollständig eingelesen.\u001fZusätzlich konnte eine isolierte Home-Assistant-Testinstanz erfolgreich starten.\u001fEin erfolgreicher vollständiger externer Test-Restore ist dokumentiert.\u001fKompakt\u001fAusgewogen\u001fErweitert\u001fServer\u001fDynamischer Prüfumfang\u001fOffene Risiken\u001fEs wurden keine blockierenden Wiederherstellungsrisiken erkannt.\u001fDas neueste Backup ist zu alt\u001fKeine unabhängige Backup-Kopie erkannt\u001fZuvor enthaltene Backup-Inhalte fehlen\u001fEine externe Abhängigkeit ist nicht abgesichert\u001fAbsicherung einer automatisch erkannten Abhängigkeit bestätigen\u001fTechnische Details und optionale Vorsorge\u001fOptionaler zusätzlicher Nachweis\u001fEs wurde keine externe Abhängigkeit erkannt, die bestätigt werden muss.\u001fWiederherstellungsstatus\u001fWichtigste Maßnahme\u001fPrüfpunkte der Notfallvorsorge\u001fPunktabzüge\u001fFür die Wiederherstellungsbereitschaft sind keine Punktabzüge aktiv.\u001fPunkte abgezogen\u001fErfüllt\u001fHandlungsbedarf\u001fNicht bewertet\u001fDie Grundlage für eine Wiederherstellung ist bereit.\u001fEine Wiederherstellung ist möglich, aber wichtige Lücken bestehen.\u001fDie Wiederherstellungsbereitschaft ist unzureichend.\u001fDie Wiederherstellungsbereitschaft kann noch nicht bewertet werden.\u001fInhalt des neuesten Backups\u001fVergleich mit dem vorherigen vollständigen Backup\u001fAusfallsicherheit der Speicherorte\u001fEs ist noch kein vorheriges vollständiges Backup für einen Vergleich vorhanden.\u001fEs wurden keine relevanten Inhaltsänderungen erkannt.\u001fDer Sicherungsumfang wurde verändert, ohne erforderliche Inhalte zu verlieren.\u001fZuvor enthaltene Inhalte fehlen oder sind unvollständig.\u001fBackup-Referenz\u001fVergleichsbackup\u001fHome-Assistant-Daten\u001fDatenbank\u001fAdd-ons\u001fOrdner\u001fSSL\u001fShare\u001fMedien\u001fFehlgeschlagene Bestandteile\u001fBackup-Kopien\u001fKlassifizierte Kopien\u001fNicht klassifizierte Kopien\u001fUnabhängige Ausfallbereiche\u001fKopie außerhalb des Home-Assistant-Geräts\u001fUnabhängige Kopie bestätigt\u001fSpeicherklassen\u001fEnthalten\u001fFehlt\u001fUnbekannt\u001fJa\u001fNein\u001fHinzugefügt\u001fEntfernt\u001fHinzugefügte Add-ons\u001fEntfernte Add-ons\u001fHinzugefügte Ordner\u001fEntfernte Ordner\u001fFehlende kritische Ordner\u001fGeführter Notfallcheck\u001fBestätige nur, ob die benötigten Informationen verfügbar sind. Passwörter, Pfade und Notizen werden hier niemals gespeichert.\u001fExterne Abhängigkeiten\u001fBackupCheckup zeigt nur automatisch erkannte oder bereits konfigurierte Abhängigkeiten. Bestätige lediglich, ob die erkannten externen Daten separat abgesichert sind.\u001fBestätigungen laufen nach {days} Tagen ab und müssen anschließend erneut geprüft werden.\u001fErkannt\u001fPrüfung abgelaufen\u001fNur Home-Assistant-Administratoren können diese Angaben ändern.\u001fBackup-Schutzprüfung\u001fNutzt die echte geschützte Lesepipeline: Das Backup wird geladen, bei Bedarf entschlüsselt und vollständig eingelesen, ohne das laufende System wiederherzustellen oder zu verändern.\u001fBackup-Schutz prüfen\u001fWiederherstellungssimulation wird gestartet\u001fErgebnis der Simulation\u001fSimulation läuft\u001fEs wird kein Restore-Endpunkt aufgerufen und es werden keine Produktivdaten geschrieben.\u001fAktueller Schritt\u001fTechnischer Fortschritt\u001fBestandene Prüfungen\u001fOffene Prüfungen\u001fBlockierende Prüfungen\u001fGelesene Archive\u001fGelesene Dateien\u001fGelesene Daten\u001fLaufzeit\u001fBlockierende Fehler\u001fOffene Hinweise der Simulation\u001fBereit\u001fBereit mit Warnungen\u001fNicht bereit\u001fLäuft\u001fDurch Sicherheitsgrenze abgebrochen\u001fBackup-Passwort erforderlich\u001fErgebnis nicht eindeutig\u001fNoch nicht ausgeführt\u001fSimulation vorbereiten\u001fSpeicherkopie auswählen\u001fBackup herunterladen\u001fMetadaten und Archive lesen\u001fDatenbank prüfen\u001fWiederherstellungsplan bewerten\u001fTemporäre Daten entfernen\u001fSimulation abschließen\u001fAusstehend\u001fLäuft\u001fBestanden\u001fWarnung\u001fFehlgeschlagen\u001fNicht erforderlich\u001fIsolierter Home-Assistant-Start\u001fNach der Strukturprüfung stellt der optionale Runner das geprüfte Backup in einer temporären, netzwerkisolierten Instanz wieder her und zeigt deren Start live.\u001fStatus des Runtime-Tests\u001fEphemere Testinstanz läuft\u001fRunner-Fortschritt\u001fDie Testinstanz hat keinen Zugriff auf das Heimnetz. Alle temporären Daten werden nach dem Lauf entfernt.\u001fDer optionale BackupCheckup Runtime Runner wurde nicht erkannt.\u001fRunner nicht verfügbar\u001fNoch nicht ausgeführt\u001fLäuft\u001fStartfähigkeit bestätigt\u001fStart fehlgeschlagen\u001fDurch Sicherheitsgrenze beendet\u001fErgebnis nicht eindeutig\u001fIsolierten Runner vorbereiten\u001fGeprüftes Backup übertragen\u001fTemporäre Konfiguration wiederherstellen\u001fHome Assistant starten\u001fAuf Startbereitschaft warten\u001fTemporäre Instanz entfernen\u001fRuntime-Test abschließen\u001fDokumentierter Test-Restore\u001fOptionaler zusätzlicher Nachweis. Für die strukturelle Bereitschaft ist ein dokumentierter externer Restore nicht mehr erforderlich.\u001fEs wurde noch kein Test-Restore dokumentiert.\u001fDurchgeführt am\u001fErgebnis\u001fUmfang\u001fAlter\u001fAktuell\u001fAbgelaufen\u001fTest-Restore dokumentieren\u001fErfolgreich\u001fFehlgeschlagen\u001fVollständige Wiederherstellung\u001fTeilweise Wiederherstellung\u001fNotfallplan zur Wiederherstellung\u001fWird lokal aus der aktuellen Notfallbewertung erzeugt. Die Exporte enthalten keine Passwörter, Tokens, Pfade, Hostnamen, IP-Adressen oder Backup-Namen.\u001fErzeugt\u001fOffene Risiken\u001fMarkdown exportieren\u001fHTML exportieren\u001fJSON exportieren\u001fEs ist noch kein Notfallplan verfügbar.\u001fBackup-Passwort ist auffindbar\u001fZugang zum externen Backup-Speicher ist dokumentiert\u001fDer Wiederherstellungsweg ist bekannt\u001fErsatzgerät oder Installationsmedium ist verfügbar\u001fBenötigte Netzwerkzugänge sind dokumentiert\u001fBenötigte Kontakte und Kontoinhaber sind dokumentiert\u001fExterne Datenbank\u001fMQTT-Broker\u001fZigbee-Koordinator\u001fZ-Wave-Controller\u001fThread- / Matter-Infrastruktur\u001fESPHome-Konfiguration\u001fNetzwerkspeicher / NAS\u001fReverse Proxy\u001fZertifikate\u001fCloud-Dienste und API-Zugänge\u001fNicht bewertet\u001fBestätigt\u001fFehlt\u001fNicht erforderlich\u001fNicht bewertet\u001fSeparat abgesichert\u001fNicht abgesichert\u001fNicht zutreffend\u001fHome-Assistant-Gerät\u001fDirekt angeschlossener Speicher\u001fLokales Netzwerk / NAS\u001fEntfernter Speicher\u001fCloud-Speicher\u001fUnbekannt\u001fBackup vorhanden\u001fBackup aktuell\u001fBackup vollständig\u001fHome-Assistant-Daten enthalten\u001fDatenbank enthalten\u001fIntegrität geprüft\u001fDatenbank geprüft\u001fUnabhängige Kopie vorhanden\u001fMehrere Ausfallbereiche vorhanden\u001fKopiergrößen stimmen überein\u001fBackup-Inhalt weiterhin vollständig\u001fGeführter Notfallcheck vollständig\u001fExterne Abhängigkeiten abgesichert\u001fSimulierter Wiederherstellungstest bestanden\u001fErfolgreicher vollständiger Test-Restore dokumentiert"),
  da: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Gendannelse\u001fGendannelsesberedskab\u001fGendannelsesscore\u001fGendannelsesstatus\u001fVigtigste handling\u001fGendannelseskontroller\u001fPointfradrag"),
  es: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Recuperación\u001fPreparación para la recuperación\u001fPuntuación de recuperación\u001fEstado de recuperación\u001fAcción prioritaria\u001fComprobaciones de recuperación\u001fDeducciones de puntos"),
  fr: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Restauration\u001fPréparation à la restauration\u001fScore de restauration\u001fÉtat de restauration\u001fAction prioritaire\u001fContrôles de restauration\u001fDéductions de points"),
  it: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Ripristino\u001fPreparazione al ripristino\u001fPunteggio di ripristino\u001fStato di ripristino\u001fAzione prioritaria\u001fControlli di ripristino\u001fDetrazioni di punti"),
  nl: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Herstel\u001fHerstelgereedheid\u001fHerstelscore\u001fHerstelstatus\u001fBelangrijkste actie\u001fHerstelcontroles\u001fPuntaftrek"),
  pl: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Odzyskiwanie\u001fGotowość do odzyskiwania\u001fWynik odzyskiwania\u001fStan odzyskiwania\u001fNajważniejsze działanie\u001fKontrole odzyskiwania\u001fOdjęte punkty"),
  sv: unpackNestedTranslation(RECOVERY_TEXT_PATHS_2, "Återställning\u001fÅterställningsberedskap\u001fÅterställningspoäng\u001fÅterställningsstatus\u001fViktigaste åtgärd\u001fÅterställningskontroller\u001fPoängavdrag"),
});

const CONFIG_TEXT_PATHS_1 = Object.freeze("tab\u001ftitle\u001fsubtitle\u001floading\u001floadFailed\u001fsave\u001fsaving\u001fsaved\u001freset\u001freloadNotice\u001fadminOnly\u001fruntime\u001fruntimeHelp\u001fmonitoring\u001fmonitoringHelp\u001fverification\u001fverificationHelp\u001fpresentation\u001fpresentationHelp\u001fhardware\u001frecommended\u001finstallationType\u001farchitecture\u001fboard\u001fruntime_profile\u001fadaptive_polling\u001fupdate_interval_minutes\u001factive_update_interval_minutes\u001ferror_backoff_interval_minutes\u001fadaptive_error_threshold\u001fmax_verification_size_gb\u001fmax_expanded_size_gb\u001fverification_timeout_minutes\u001fdatabase_timeout_minutes\u001fmanual_verification_cooldown_minutes\u001fmonitoring_policy\u001fmax_age_days\u001fsize_check_mode\u001fminimum_backup_size_mb\u001fmaximum_size_drop_percent\u001fminimum_redundant_locations\u001frepair_issues_enabled\u001fanalytics_window_days\u001fverification_policy\u001fauto_verify_new_backups\u001fdatabase_integrity_check\u001fentity_mode\u001fexpose_backup_metadata\u001fshow_sidebar_panel\u001factivity_logging_enabled\u001factivity_log_persistence\u001factivity_log_retention_days\u001fnotifications_enabled\u001fnotification_targets\u001fnotify_on_recovery\u001fnoTargets\u001fselectMultiple\u001foptionLabels.energy_saving\u001foptionLabels.home_assistant_appliance\u001foptionLabels.performance\u001foptionLabels.server\u001foptionLabels.custom\u001foptionLabels.balanced\u001foptionLabels.strict\u001foptionLabels.manual\u001foptionLabels.automatic\u001foptionLabels.deep\u001foptionLabels.standard\u001foptionLabels.expert\u001foptionLabels.fixed\u001foptionLabels.disabled\u001ferrors.invalid_payload\u001ferrors.unknown_setting\u001ferrors.invalid_boolean\u001ferrors.invalid_integer\u001ferrors.out_of_range\u001ferrors.invalid_option\u001ferrors.invalid_notification_target\u001ferrors.notification_target_required\u001ferrors.active_interval_too_slow\u001ferrors.backoff_interval_too_fast\u001ferrors.expanded_size_too_small\u001ferrors.fixed_size_required".split(TRANSLATION_SEPARATOR));

const CONFIG_TEXT = Object.freeze({
  en: unpackNestedTranslation(CONFIG_TEXT_PATHS_1, "Settings\u001fBackupCheckup settings\u001fChange all integration options directly here. Saving reloads the integration once.\u001fLoading settings…\u001fThe settings could not be loaded.\u001fSave settings\u001fSaving…\u001fSettings saved. BackupCheckup is reloading.\u001fDiscard changes\u001fA short integration reload is required after saving.\u001fOnly Home Assistant administrators can change these settings.\u001fRuntime and performance\u001fChoose a hardware profile or configure every runtime limit manually.\u001fMonitoring and thresholds\u001fControl when BackupCheckup reports stale, small or non-redundant backups.\u001fIntegrity verification\u001fConfigure automatic checks, database inspection and safety limits.\u001fDisplay, privacy and notifications\u001fControl entities, live logging, metadata visibility and Companion App notifications.\u001fDetected hardware recommendation\u001fRecommended profile\u001fInstallation type\u001fArchitecture\u001fBoard\u001fRuntime profile\u001fAdaptive polling\u001fNormal polling interval (minutes)\u001fActive polling interval (minutes)\u001fError backoff interval (minutes)\u001fErrors before backoff\u001fMaximum backup download (GB)\u001fMaximum expanded size (GB)\u001fVerification timeout (minutes)\u001fDatabase timeout (minutes)\u001fManual verification cooldown (minutes)\u001fMonitoring policy\u001fMaximum backup age (days)\u001fSize check\u001fMinimum backup size (MB)\u001fMaximum size drop (%)\u001fRequired storage locations\u001fCreate Home Assistant repair issues\u001fAnalytics window (days)\u001fVerification policy\u001fAutomatically verify new backups\u001fInspect the backup database\u001fEntity mode\u001fExpose private backup metadata in entity attributes\u001fShow BackupCheckup in the sidebar\u001fEnable detailed live logging\u001fKeep the live log across restarts\u001fLive-log retention (days)\u001fEnable mobile notifications\u001fCompanion App devices\u001fSend recovery notifications\u001fNo Companion App notification entities are available.\u001fUse Ctrl/Cmd to select multiple devices.\u001fEnergy saving\u001fHome Assistant appliance\u001fPerformance\u001fServer\u001fCustom\u001fBalanced\u001fStrict\u001fManual\u001fAutomatic\u001fDeep verification\u001fStandard\u001fExpert\u001fFixed minimum\u001fDisabled\u001fThe submitted configuration is invalid.\u001fThe submitted configuration contains an unknown setting.\u001fSelect a valid on/off value.\u001fEnter a whole number.\u001fThe value is outside the allowed range.\u001fSelect a supported option.\u001fSelect only valid notification devices.\u001fSelect at least one device when notifications are enabled.\u001fThe active interval must not exceed the normal interval.\u001fThe error backoff must not be shorter than the normal interval.\u001fThe expanded-size limit must be at least the download limit.\u001fA fixed size check requires a minimum size above zero."),
  de: unpackNestedTranslation(CONFIG_TEXT_PATHS_1, "Einstellungen\u001fBackupCheckup-Einstellungen\u001fAlle Integrationsoptionen direkt hier ändern. Beim Speichern wird die Integration einmal neu geladen.\u001fEinstellungen werden geladen…\u001fDie Einstellungen konnten nicht geladen werden.\u001fEinstellungen speichern\u001fSpeichern…\u001fEinstellungen gespeichert. BackupCheckup wird neu geladen.\u001fÄnderungen verwerfen\u001fNach dem Speichern ist ein kurzer Neustart der Integration erforderlich.\u001fNur Home-Assistant-Administratoren können diese Einstellungen ändern.\u001fLaufzeit und Leistung\u001fHardwareprofil auswählen oder alle Laufzeitgrenzen manuell konfigurieren.\u001fÜberwachung und Grenzwerte\u001fFestlegen, wann BackupCheckup alte, kleine oder nicht redundante Backups meldet.\u001fIntegritätsprüfung\u001fAutomatische Prüfungen, Datenbankkontrolle und Sicherheitsgrenzen konfigurieren.\u001fDarstellung, Datenschutz und Benachrichtigungen\u001fEntitäten, Live-Protokoll, Metadaten und Companion-App-Benachrichtigungen steuern.\u001fErkannte Hardwareempfehlung\u001fEmpfohlenes Profil\u001fInstallationsart\u001fArchitektur\u001fHardware/Board\u001fLaufzeitprofil\u001fAdaptive Abfrage\u001fNormales Abfrageintervall (Minuten)\u001fAktives Abfrageintervall (Minuten)\u001fFehler-Warteintervall (Minuten)\u001fFehler bis zur Wartephase\u001fMaximaler Backup-Download (GB)\u001fMaximal entpackte Größe (GB)\u001fZeitlimit der Prüfung (Minuten)\u001fZeitlimit der Datenbankprüfung (Minuten)\u001fSperrzeit manueller Prüfungen (Minuten)\u001fÜberwachungsrichtlinie\u001fMaximales Backupalter (Tage)\u001fGrößenprüfung\u001fMinimale Backupgröße (MB)\u001fMaximaler Größenrückgang (%)\u001fErforderliche Speicherorte\u001fHome-Assistant-Reparaturhinweise erstellen\u001fAnalysezeitraum (Tage)\u001fPrüfstrategie\u001fNeue Backups automatisch prüfen\u001fDatenbank im Backup kontrollieren\u001fEntitätsmodus\u001fPrivate Backup-Metadaten in Entitätsattributen anzeigen\u001fBackupCheckup in der Seitenleiste anzeigen\u001fDetailliertes Live-Protokoll aktivieren\u001fLive-Protokoll über Neustarts behalten\u001fAufbewahrung des Live-Protokolls (Tage)\u001fMobile Benachrichtigungen aktivieren\u001fCompanion-App-Geräte\u001fEntwarnungsbenachrichtigungen senden\u001fKeine Benachrichtigungsentitäten der Companion App verfügbar.\u001fMit Strg/Cmd können mehrere Geräte ausgewählt werden.\u001fEnergiesparend\u001fHome-Assistant-Gerät\u001fLeistung\u001fServer\u001fBenutzerdefiniert\u001fAusgewogen\u001fStreng\u001fManuell\u001fAutomatisch\u001fTiefe Prüfung\u001fStandard\u001fExperte\u001fFester Mindestwert\u001fDeaktiviert\u001fDie übermittelte Konfiguration ist ungültig.\u001fDie Konfiguration enthält eine unbekannte Einstellung.\u001fBitte einen gültigen Ein-/Aus-Wert auswählen.\u001fBitte eine ganze Zahl eingeben.\u001fDer Wert liegt außerhalb des zulässigen Bereichs.\u001fBitte eine unterstützte Option auswählen.\u001fBitte nur gültige Benachrichtigungsgeräte auswählen.\u001fBei aktivierten Benachrichtigungen muss mindestens ein Gerät ausgewählt sein.\u001fDas aktive Intervall darf nicht größer als das normale Intervall sein.\u001fDas Fehler-Warteintervall darf nicht kürzer als das normale Intervall sein.\u001fDie Grenze der entpackten Größe muss mindestens der Downloadgrenze entsprechen.\u001fFür eine feste Größenprüfung muss die Mindestgröße größer als null sein."),
});

const DEFAULT_ENTITIES = {
  status: "sensor.backup_checkup_status",
  health_score: "sensor.backup_checkup_health_score",
  recovery_readiness: "sensor.backup_checkup_recovery_readiness",
  recovery_status: "sensor.backup_checkup_recovery_status",
  recovery_recommendation: "sensor.backup_checkup_recovery_recommendation",
  restore_simulation_status: "sensor.backup_checkup_restore_simulation_status",
  last_restore_test: "sensor.backup_checkup_last_restore_test",
  recommendation: "sensor.backup_checkup_recommendation",
  stored_backups: "sensor.backup_checkup_stored_backups",
  latest_backup_age: "sensor.backup_checkup_latest_backup_age",
  latest_backup_size: "sensor.backup_checkup_latest_backup_size",
  integrity_status: "sensor.backup_checkup_integrity_status",
  problem: "binary_sensor.backup_checkup_problem",
  verify: "button.backup_checkup_verify_latest_backup",
  recovery_assessment: "button.backup_checkup_run_recovery_assessment",
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
    this._preparednessDraft = new Map();
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
    this._configState = { status: "idle", data: null, draft: null, errors: {}, saved: false };
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
    const language = this._language();
    const selected = TEXT[language];
    const recovery = RECOVERY_TEXT[language] ?? RECOVERY_TEXT.en;
    return {
      ...TEXT.en,
      ...selected,
      activityActions: { ...TEXT.en.activityActions, ...selected.activityActions },
      activityOutcomes: { ...TEXT.en.activityOutcomes, ...selected.activityOutcomes },
      config: {
        ...CONFIG_TEXT.en,
        ...CONFIG_TEXT[language],
        optionLabels: {
          ...CONFIG_TEXT.en.optionLabels,
          ...CONFIG_TEXT[language]?.optionLabels,
        },
        errors: {
          ...CONFIG_TEXT.en.errors,
          ...CONFIG_TEXT[language]?.errors,
        },
      },
      recovery: {
        ...RECOVERY_TEXT.en,
        ...recovery,
        checkLabels: {
          ...RECOVERY_TEXT.en.checkLabels,
          ...recovery.checkLabels,
        },
        storageClassLabels: {
          ...RECOVERY_TEXT.en.storageClassLabels,
          ...recovery.storageClassLabels,
        },
        checklistLabels: {
          ...RECOVERY_TEXT.en.checklistLabels,
          ...recovery.checklistLabels,
        },
        dependencyLabels: {
          ...RECOVERY_TEXT.en.dependencyLabels,
          ...recovery.dependencyLabels,
        },
        checklistStatusLabels: {
          ...RECOVERY_TEXT.en.checklistStatusLabels,
          ...recovery.checklistStatusLabels,
        },
        dependencyStatusLabels: {
          ...RECOVERY_TEXT.en.dependencyStatusLabels,
          ...recovery.dependencyStatusLabels,
        },
        restoreResultLabels: {
          ...RECOVERY_TEXT.en.restoreResultLabels,
          ...recovery.restoreResultLabels,
        },
        evidenceLabels: {
          ...RECOVERY_TEXT.en.evidenceLabels,
          ...recovery.evidenceLabels,
        },
        evidenceDescriptions: {
          ...RECOVERY_TEXT.en.evidenceDescriptions,
          ...recovery.evidenceDescriptions,
        },
        profileLabels: {
          ...RECOVERY_TEXT.en.profileLabels,
          ...recovery.profileLabels,
        },
        riskLabels: {
          ...RECOVERY_TEXT.en.riskLabels,
          ...recovery.riskLabels,
        },
        restoreScopeLabels: {
          ...RECOVERY_TEXT.en.restoreScopeLabels,
          ...recovery.restoreScopeLabels,
        },
        simulationStatusLabels: {
          ...RECOVERY_TEXT.en.simulationStatusLabels,
          ...recovery.simulationStatusLabels,
        },
        simulationStageLabels: {
          ...RECOVERY_TEXT.en.simulationStageLabels,
          ...recovery.simulationStageLabels,
        },
        simulationStageStateLabels: {
          ...RECOVERY_TEXT.en.simulationStageStateLabels,
          ...recovery.simulationStageStateLabels,
        },
      },
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
    if (this._activeTab === "settings") return [];
    if (this._activeTab === "logs") {
      return [entities.activity_log, entities.clear_activity_log];
    }
    if (this._activeTab === "recovery") {
      return [
        entities.recovery_readiness,
        entities.recovery_status,
        entities.recovery_recommendation,
        entities.verify,
        entities.recovery_assessment,
        entities.restore_simulation_status,
        entities.last_restore_test,
        entities.refresh,
      ];
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
    remember(this);
    let current = this.parentElement || this.getRootNode?.()?.host || null;
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

  _localizedRecoveryStatus(code) {
    if (!code) return "—";
    const key = `component.backup_checkup.entity.sensor.recovery_status.state.${code}`;
    return this._hass?.localize?.(key) || this._humanize(code);
  }

  _localizedRecoveryRecommendation(code) {
    if (!code) return "—";
    const key = `component.backup_checkup.entity.sensor.recovery_recommendation.state.${code}`;
    return this._hass?.localize?.(key) || this._humanize(code);
  }

  _recoveryTone(status) {
    if (status === "ready") return "good";
    if (status === "limited") return "warning";
    if (status === "insufficient") return "danger";
    return "neutral";
  }

  _recoveryMessage(status, text) {
    if (status === "ready") return text.readyMessage;
    if (status === "limited") return text.limitedMessage;
    if (status === "insufficient") return text.insufficientMessage;
    return text.unknownMessage;
  }

  _evidenceTone(level) {
    if (["structurally_verified", "runtime_ready", "fully_tested"].includes(level)) return "good";
    if (["monitored", "limited"].includes(level)) return "warning";
    if (level === "not_recoverable") return "danger";
    return "neutral";
  }

  _riskRows(risks, text) {
    if (!Array.isArray(risks) || !risks.length) {
      return `<div class="empty success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.noOpenRisks)}</div>`;
    }
    return risks.map((risk) => `<div class="problem-row">
      <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
      <span>${this._escape(text.riskLabels?.[risk] || this._humanize(risk))}</span>
    </div>`).join("");
  }

  _recoveryCheckRows(checks, text) {
    return RECOVERY_CHECK_KEYS.map((key) => {
      const value = Object.hasOwn(checks || {}, key)
        ? checks[key] : null;
      let tone = "neutral";
      let icon = "mdi:help-circle-outline";
      let result = text.unknown;
      if (value === true) {
        tone = "good";
        icon = "mdi:check-circle-outline";
        result = text.passed;
      } else if (value === false) {
        tone = "danger";
        icon = "mdi:alert-circle-outline";
        result = text.failed;
      }
      return `<div class="recovery-check ${tone}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><strong>${this._escape(text.checkLabels?.[key] || this._humanize(key))}</strong><span>${this._escape(result)}</span></div>
      </div>`;
    }).join("");
  }

  _recoveryDeductionRows(deductions, text) {
    const rows = Object.entries(deductions || {})
      .filter(([, value]) => Number(value) > 0)
      .sort((left, right) => Number(right[1]) - Number(left[1]));
    if (!rows.length) {
      return `<div class="empty success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.noDeductions)}</div>`;
    }
    return rows.map(([key, value]) => `<div class="explanation-row">
      <span>${this._escape(text.checkLabels?.[key] || this._humanize(key))}</span>
      <strong>−${this._escape(value)} ${this._escape(text.pointsDeducted)}</strong>
    </div>`).join("");
  }

  _recoveryValue(value, text) {
    if (value === true) return text.present;
    if (value === false) return text.missing;
    return text.notKnown;
  }

  _recoveryDetailRow(label, value) {
    return `<div class="explanation-row"><span>${this._escape(label)}</span><strong>${this._escape(value)}</strong></div>`;
  }

  _contentInventoryRows(inventory, text) {
    const failed = Number(inventory?.failed_agent_count || 0)
      + Number(inventory?.failed_addon_count || 0)
      + Number(inventory?.failed_folder_count || 0);
    return [
      [text.backupReference, inventory?.backup_reference || "—"],
      [text.homeAssistant, this._recoveryValue(inventory?.homeassistant_included, text)],
      [text.database, this._recoveryValue(inventory?.database_included, text)],
      [text.addons, inventory?.addon_count ?? 0],
      [text.folders, inventory?.folder_count ?? 0],
      [text.ssl, this._recoveryValue(inventory?.ssl_included, text)],
      [text.share, this._recoveryValue(inventory?.share_included, text)],
      [text.media, this._recoveryValue(inventory?.media_included, text)],
      [text.failedComponents, failed],
    ].map(([label, value]) => this._recoveryDetailRow(label, value)).join("");
  }

  _contentComparisonRows(comparison, text) {
    if (!comparison?.baseline_available) {
      return `<div class="empty"><ha-icon icon="mdi:history"></ha-icon>${this._escape(text.baselineMissing)}</div>`;
    }
    let state = text.noContentChanges;
    if (comparison.material_regression) state = text.contentRegression;
    else if (comparison.changed) state = text.contentChanged;
    const critical = Array.isArray(comparison.critical_components_missing)
      ? comparison.critical_components_missing.map((key) => text[key] || this._humanize(key)).join(", ")
      : "";
    const rows = [
      [text.baselineReference, comparison.baseline_reference || "—"],
      [text.removedAddons, comparison.missing_addon_count ?? 0],
      [text.addedAddons, comparison.added_addon_count ?? 0],
      [text.removedFolders, comparison.missing_folder_count ?? 0],
      [text.addedFolders, comparison.added_folder_count ?? 0],
      [text.criticalMissing, critical || "—"],
    ].map(([label, value]) => this._recoveryDetailRow(label, value)).join("");
    const tone = comparison.material_regression ? "danger" : "success";
    const icon = comparison.material_regression ? "mdi:alert-circle-outline" : "mdi:check-circle-outline";
    return `<div class="empty ${tone}"><ha-icon icon="${icon}"></ha-icon>${this._escape(state)}</div>${rows}`;
  }

  _storageResilienceRows(storage, text) {
    const classes = Array.isArray(storage?.storage_classes)
      ? storage.storage_classes.map((key) => text.storageClassLabels?.[key] || this._humanize(key)).join(", ")
      : "";
    return [
      [text.copies, storage?.copy_count ?? 0],
      [text.classifiedCopies, storage?.classified_copy_count ?? 0],
      [text.unknownCopies, storage?.unknown_copy_count ?? 0],
      [text.failureDomains, storage?.failure_domain_count ?? 0],
      [text.offDeviceCopy, this._recoveryValue(storage?.off_device_copy, { ...text, present: text.yes, missing: text.no })],
      [text.independentCopy, this._recoveryValue(storage?.independent_copy, { ...text, present: text.yes, missing: text.no })],
      [text.storageClasses, classes || text.notKnown],
    ].map(([label, value]) => this._recoveryDetailRow(label, value)).join("");
  }

  _preparednessSelect(section, key, item, labels, isAdmin) {
    this._preparednessDraft ||= new Map();
    const draftKey = `${section}:${key}`;
    const selectedStatus = this._preparednessDraft.get(draftKey) || item?.status;
    const options = Object.entries(labels).map(([value, label]) =>
      `<option value="${this._escape(value)}" ${selectedStatus === value ? "selected" : ""}>${this._escape(label)}</option>`
    ).join("");
    const busyKey = `preparedness:${section}:${key}`;
    const disabled = !isAdmin || this._busy.has(busyKey) ? "disabled" : "";
    return `<select data-preparedness-section="${section}" data-preparedness-item="${this._escape(key)}" ${disabled}>${options}</select>`;
  }

  _preparednessRows(preparedness, section, text, isAdmin) {
    this._preparednessDraft ||= new Map();
    const items = preparedness?.[section] || {};
    const isChecklist = section === "checklist";
    const itemLabels = isChecklist ? text.checklistLabels : text.dependencyLabels;
    const statusLabels = isChecklist ? text.checklistStatusLabels : text.dependencyStatusLabels;
    const keys = Object.keys(itemLabels).filter((key) => {
      if (isChecklist) return true;
      const item = items[key];
      return Boolean(item?.relevant || item?.detected);
    });
    if (!keys.length) {
      return `<div class="empty success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.noDetectedDependencies)}</div>`;
    }
    return keys.map((key) => {
      const item = items[key] || { status: "unknown", effective_status: "unknown" };
      const draftKey = `${section}:${key}`;
      if (this._preparednessDraft.get(draftKey) === item.status) {
        this._preparednessDraft.delete(draftKey);
      }
      const displayStatus = this._preparednessDraft.get(draftKey) || item.effective_status;
      const detected = !isChecklist && item.detected;
      const expired = Boolean(item.expired);
      const effectiveLabel = statusLabels[displayStatus] || text.unknown;
      const detectedBadge = detected
        ? `<span class="preparedness-badge detected">${this._escape(text.detected)}</span>`
        : "";
      const expiredBadge = expired
        ? `<span class="preparedness-badge expired">${this._escape(text.expired)}</span>`
        : "";
      return `<div class="preparedness-row ${expired ? "expired" : ""}">
        <div class="preparedness-copy"><strong>${this._escape(itemLabels[key])}</strong><span>${this._escape(effectiveLabel)}</span></div>
        <div class="preparedness-badges">${detectedBadge}${expiredBadge}</div>
        ${this._preparednessSelect(section, key, item, statusLabels, isAdmin)}
      </div>`;
    }).join("");
  }

  _preparednessReviewText(preparedness, text) {
    const days = preparedness?.review_interval_days || 180;
    return String(text.reviewInterval).replace("{days}", days);
  }

  _simulationRows(simulation, text, compact = false) {
    const status = simulation?.status || "not_run";
    let tone = "neutral";
    if (status === "passed") tone = "good";
    else if (["running", "warning", "aborted", "password_required", "inconclusive"].includes(status)) tone = "warning";
    else if (status === "failed") tone = "danger";
    const statusLabel = text.simulationStatusLabels?.[status] || this._humanize(status);
    const progress = Math.min(100, Math.max(0, Number(simulation?.progress_percent) || 0));
    const stage = simulation?.stage || "prepare";
    const stageLabel = text.simulationStageLabels?.[stage] || this._humanize(stage);
    const checks = Object.values(simulation?.checks || {});
    const passed = checks.filter((value) => value === true).length;
    const failed = checks.filter((value) => value === false).length;
    const open = checks.filter((value) => value == null).length;
    const allStageEntries = Object.entries(simulation?.stages || {});
    const importantStages = allStageEntries.filter(([, value]) =>
      ["running", "failed", "warning"].includes(value)
    );
    let stageEntries = allStageEntries;
    if (compact) {
      stageEntries = importantStages.length ? importantStages : allStageEntries.slice(-1);
    }
    const stageRows = stageEntries.map(([key, value]) => {
      const icons = {
        passed: "mdi:check-circle",
        failed: "mdi:close-circle",
        running: "mdi:progress-clock",
        warning: "mdi:alert-circle",
        not_applicable: "mdi:minus-circle-outline",
      };
      const icon = icons[value] || "mdi:clock-outline";
      const label = text.simulationStageLabels?.[key] || this._humanize(key);
      const stateLabel = text.simulationStageStateLabels?.[value] || this._humanize(value);
      return `<div class="simulation-stage ${this._escape(value)}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><strong>${this._escape(label)}</strong><span>${this._escape(stateLabel)}</span></div>
      </div>`;
    }).join("");
    const sizeMb = Number(simulation?.verified_size) > 0
      ? `${(Number(simulation.verified_size) / 1_000_000).toLocaleString(this._language(), { maximumFractionDigits: 1 })} MB`
      : "—";
    const duration = Number(simulation?.duration_seconds) >= 0
      ? `${Number(simulation.duration_seconds).toLocaleString(this._language(), { maximumFractionDigits: 1 })} s`
      : "—";
    const detailedMetrics = compact ? "" : `<div class="simulation-metrics">
        <div><ha-icon icon="mdi:archive-outline"></ha-icon><span>${this._escape(text.simulationArchives)}</span><strong>${Number(simulation?.archive_count) || 0}</strong></div>
        <div><ha-icon icon="mdi:file-multiple-outline"></ha-icon><span>${this._escape(text.simulationFiles)}</span><strong>${Number(simulation?.file_count) || 0}</strong></div>
        <div><ha-icon icon="mdi:database-arrow-down-outline"></ha-icon><span>${this._escape(text.simulationSize)}</span><strong>${this._escape(sizeMb)}</strong></div>
        <div><ha-icon icon="mdi:timer-outline"></ha-icon><span>${this._escape(text.simulationDuration)}</span><strong>${this._escape(duration)}</strong></div>
      </div>
      <div class="simulation-check-summary">
        <div class="good"><strong>${passed}</strong><span>${this._escape(text.simulationChecksPassed)}</span></div>
        <div class="warning"><strong>${open}</strong><span>${this._escape(text.simulationChecksOpen)}</span></div>
        <div class="danger"><strong>${failed}</strong><span>${this._escape(text.simulationChecksFailed)}</span></div>
      </div>`;
    return `<div class="simulation-dashboard ${tone}">
      <div class="simulation-head">
        <div class="simulation-state"><span></span><div><small>${this._escape(simulation?.running ? text.simulationLive : text.simulationStatus)}</small><strong>${this._escape(statusLabel)}</strong></div></div>
        <div class="simulation-current"><small>${this._escape(text.simulationStage)}</small><strong>${this._escape(stageLabel)}</strong></div>
      </div>
      <div class="simulation-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}">
        <div style="width:${progress}%"></div>
      </div>
      <div class="simulation-progress-label"><span>${this._escape(text.simulationProgress)}</span><strong>${progress}%</strong></div>
      <div class="simulation-pipeline">${stageRows}</div>
      ${detailedMetrics}
      <p class="simulation-safety"><ha-icon icon="mdi:shield-lock-outline"></ha-icon>${this._escape(text.simulationSafety)}</p>
    </div>`;
  }

  _runtimeRows(runtime, text) {
    const status = runtime?.status || "not_available";
    if (status === "not_available") {
      return `<div class="empty runtime-empty"><ha-icon icon="mdi:server-off"></ha-icon>${this._escape(text.runtimeUnavailable)}</div>`;
    }
    let tone = "neutral";
    if (status === "passed") tone = "good";
    else if (["running", "aborted", "inconclusive"].includes(status)) tone = "warning";
    else if (status === "failed") tone = "danger";
    const terminal = ["passed", "failed", "aborted", "inconclusive"].includes(status);
    const storedProgress = runtime?.progress_percent;
    const progress = Math.min(100, Math.max(
      0,
      Number(storedProgress ?? (terminal ? 100 : 0)) || 0,
    ));
    const stage = runtime?.stage || "runtime_prepare";
    const statusLabel = text.runtimeStatusLabels?.[status] || this._humanize(status);
    const stageLabel = text.runtimeStageLabels?.[stage] || this._humanize(stage);
    const stageRows = Object.entries(runtime?.stages || {}).map(([key, value]) => {
      const icons = {
        passed: "mdi:check-circle",
        failed: "mdi:close-circle",
        running: "mdi:progress-clock",
      };
      const icon = icons[value] || "mdi:clock-outline";
      const label = text.runtimeStageLabels?.[key] || this._humanize(key);
      const stateLabel = text.simulationStageStateLabels?.[value] || this._humanize(value);
      return `<div class="simulation-stage ${this._escape(value)}">
        <ha-icon icon="${icon}"></ha-icon>
        <div><strong>${this._escape(label)}</strong><span>${this._escape(stateLabel)}</span></div>
      </div>`;
    }).join("");
    return `<div class="runtime-phase">
      <div class="runtime-heading"><ha-icon icon="mdi:home-clock-outline"></ha-icon><div><strong>${this._escape(text.runtimeTitle)}</strong><span>${this._escape(text.runtimeIntro)}</span></div></div>
      <div class="simulation-dashboard ${tone}">
        <div class="simulation-head">
          <div class="simulation-state"><span></span><div><small>${this._escape(runtime?.running ? text.runtimeLive : text.runtimeStatus)}</small><strong>${this._escape(statusLabel)}</strong></div></div>
          <div class="simulation-current"><small>${this._escape(text.simulationStage)}</small><strong>${this._escape(stageLabel)}</strong></div>
        </div>
        <div class="simulation-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${progress}"><div style="width:${progress}%"></div></div>
        <div class="simulation-progress-label"><span>${this._escape(text.runtimeProgress)}</span><strong>${progress}%</strong></div>
        <div class="simulation-pipeline">${stageRows}</div>
        <p class="simulation-safety"><ha-icon icon="mdi:shield-lock-outline"></ha-icon>${this._escape(text.runtimeSafety)}</p>
      </div>
    </div>`;
  }

  _restoreTestRows(restoreTest, text) {
    if (!restoreTest?.tested_at) {
      return `<div class="empty"><ha-icon icon="mdi:history"></ha-icon>${this._escape(text.restoreTestMissing)}</div>`;
    }
    const result = text.restoreResultLabels?.[restoreTest.result] || this._humanize(restoreTest.result);
    const scope = text.restoreScopeLabels?.[restoreTest.scope] || this._humanize(restoreTest.scope);
    const validity = restoreTest.expired ? text.restoreTestExpired : text.restoreTestValid;
    return [
      [text.restoreTestDate, this._date(restoreTest.tested_at)],
      [text.restoreTestResult, result],
      [text.restoreTestScope, scope],
      [text.restoreTestAge, restoreTest.age_days == null ? "—" : `${restoreTest.age_days} d`],
      [text.status || "Status", validity],
    ].map(([label, value]) => this._recoveryDetailRow(label, value)).join("");
  }

  _restoreTestControls(text, isAdmin) {
    if (!isAdmin) return "";
    const disabled = this._busy.has("record_restore_test") ? "disabled" : "";
    const resultOptions = Object.entries(text.restoreResultLabels || {}).map(([value, label]) =>
      `<option value="${this._escape(value)}">${this._escape(label)}</option>`
    ).join("");
    const scopeOptions = Object.entries(text.restoreScopeLabels || {}).map(([value, label]) =>
      `<option value="${this._escape(value)}">${this._escape(label)}</option>`
    ).join("");
    return `<div class="restore-test-controls">
      <select data-restore-result ${disabled}>${resultOptions}</select>
      <select data-restore-scope ${disabled}>${scopeOptions}</select>
      <button class="action primary" data-record-restore ${disabled}><ha-icon icon="mdi:content-save-check-outline"></ha-icon>${this._escape(text.recordRestoreTest)}</button>
    </div>`;
  }

  _planRows(plan, text) {
    if (!plan?.generated_at) {
      return `<div class="empty"><ha-icon icon="mdi:file-document-outline"></ha-icon>${this._escape(text.noPlan)}</div>`;
    }
    const warnings = Array.isArray(plan.warnings) ? plan.warnings.length : 0;
    return `${this._recoveryDetailRow(text.planGenerated, this._date(plan.generated_at))}
      ${this._recoveryDetailRow(text.planWarnings, warnings)}
      <p class="preparedness-intro">${this._escape(plan.summary || "")}</p>`;
  }

  _planExportButtons(plan, text) {
    if (!plan?.exports) return "";
    return `<div class="plan-actions">
      <button class="action secondary" data-export-plan="markdown"><ha-icon icon="mdi:language-markdown-outline"></ha-icon>${this._escape(text.exportMarkdown)}</button>
      <button class="action secondary" data-export-plan="html"><ha-icon icon="mdi:language-html5"></ha-icon>${this._escape(text.exportHtml)}</button>
      <button class="action secondary" data-export-plan="json"><ha-icon icon="mdi:code-json"></ha-icon>${this._escape(text.exportJson)}</button>
    </div>`;
  }

  _storageRows(agents, text) {
    if (!agents.length) return `<div class="empty">${this._escape(text.noStorage)}</div>`;
    return agents.map((agent) => {
      const tone = this._storageTone(agent);
      let state = "online";
      if (agent.error) state = "offline";
      else if (agent.stale) state = "stale";
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
    const advice = recommendation
      ? `<span>${this._escape(text.nextStep)}: ${this._escape(recommendation)}</span>`
      : "";
    return `${detailRows}<div class="result-advice"><strong>${this._escape(this._friendlyError(error, text))}</strong>${advice}</div>`;
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
    const recoveryReadiness = this._state("recovery_readiness");
    const recoveryStatus = this._state("recovery_status");
    const recoveryRecommendation = this._state("recovery_recommendation");
    const restoreSimulationState = this._state("restore_simulation_status");
    const lastRestoreTestState = this._state("last_restore_test");
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
    const recoveryScoreValue = Number(recoveryReadiness?.state);
    const recoveryScore = Number.isFinite(recoveryScoreValue)
      ? Math.min(100, Math.max(0, recoveryScoreValue))
      : null;
    const recoveryStatusCode = recoveryStatus?.state
      || recoveryReadiness?.attributes?.status
      || "unknown";
    const recoveryRecommendationCode = recoveryRecommendation?.state
      || recoveryReadiness?.attributes?.recommendation
      || "none";
    const recoveryEvidence = recoveryReadiness?.attributes?.evidence || {};
    const evidenceLevel = recoveryEvidence.level || "monitored";
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
      recoveryScore,
      recoveryScoreLabel: this._formatState(recoveryReadiness),
      recoveryStatusCode,
      recoveryStatusLabel: this._localizedRecoveryStatus(recoveryStatusCode),
      recoveryRecommendationCode,
      recoveryRecommendationLabel: this._localizedRecoveryRecommendation(
        recoveryRecommendationCode
      ),
      recoveryTone: this._recoveryTone(recoveryStatusCode),
      recoveryMessage: this._recoveryMessage(recoveryStatusCode, text.recovery),
      recoveryEvidence,
      evidenceLevel,
      evidenceLabel: text.recovery.evidenceLabels?.[evidenceLevel]
        || this._humanize(evidenceLevel),
      evidenceDescription: text.recovery.evidenceDescriptions?.[evidenceLevel]
        || "",
      evidenceTone: this._evidenceTone(evidenceLevel),
      adaptivePolicy: recoveryReadiness?.attributes?.adaptive_policy || {},
      recoveryOpenRisks: recoveryReadiness?.attributes?.open_risks || [],
      recoveryChecks: recoveryReadiness?.attributes?.checks
        || recoveryStatus?.attributes?.checks
        || {},
      recoveryDeductions: recoveryReadiness?.attributes?.deductions
        || recoveryRecommendation?.attributes?.deductions
        || {},
      recoveryContentInventory: recoveryReadiness?.attributes?.content_inventory || {},
      recoveryContentComparison: recoveryReadiness?.attributes?.content_comparison || {},
      recoveryStorageResilience: recoveryReadiness?.attributes?.storage_resilience || {},
      recoveryPreparedness: recoveryReadiness?.attributes?.preparedness || {},
      restoreSimulation: recoveryReadiness?.attributes?.restore_simulation
        || restoreSimulationState?.attributes || {},
      runtimeTest: recoveryReadiness?.attributes?.runtime_test || {
        status: "not_available",
      },
      restoreTest: recoveryReadiness?.attributes?.restore_test
        || lastRestoreTestState?.attributes || {},
      recoveryPlan: recoveryReadiness?.attributes?.recovery_plan || {},
      isAdmin: Boolean(this._hass.user?.is_admin),
      verifyState: this._state("verify"),
      recoveryAssessmentState: this._state("recovery_assessment"),
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

  _actionFooter(model, showVerify = true) {
    if (!model.isAdmin) return "";
    const refreshDisabled = this._buttonDisabled(model.refreshState, "refresh")
      ? "disabled" : "";
    const verifyDisabled = this._buttonDisabled(model.recoveryAssessmentState, "recovery_assessment")
      ? "disabled" : "";
    const verifyAction = showVerify ? `<button class="action primary" data-action="recovery_assessment" ${verifyDisabled}>
        <ha-icon icon="mdi:shield-search"></ha-icon>${this._escape(model.text.recovery.protectionCheck)}
      </button>` : "";
    return `<footer>
      <button class="action secondary" data-action="refresh" ${refreshDisabled}>
        <ha-icon icon="mdi:refresh"></ha-icon>${this._escape(model.text.refresh)}
      </button>
      ${verifyAction}
    </footer>`;
  }

  _tabs(text, isAdmin) {
    const overviewActive = this._activeTab === "overview" ? "active" : "";
    const recoveryActive = this._activeTab === "recovery" ? "active" : "";
    const logsActive = this._activeTab === "logs" ? "active" : "";
    const settingsActive = this._activeTab === "settings" ? "active" : "";
    const settingsTab = isAdmin ? `<button class="tab ${settingsActive}" data-tab="settings">
      <ha-icon icon="mdi:cog-outline"></ha-icon>${this._escape(text.config.tab)}
    </button>` : "";
    return `<nav class="tabs" aria-label="BackupCheckup">
      <button class="tab ${overviewActive}" data-tab="overview">
        <ha-icon icon="mdi:view-dashboard-outline"></ha-icon>${this._escape(text.overviewTab)}
      </button>
      <button class="tab ${recoveryActive}" data-tab="recovery">
        <ha-icon icon="mdi:lifebuoy"></ha-icon>${this._escape(text.recovery.tab)}
      </button>
      <button class="tab ${logsActive}" data-tab="logs">
        <ha-icon icon="mdi:text-box-search-outline"></ha-icon>${this._escape(text.logTab)}
      </button>
      ${settingsTab}
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
      ${this._metric("mdi:lifebuoy", model.text.recovery.evidenceTitle, model.evidenceLabel, model.evidenceTone)}
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

  _recoveryTemplate(model) {
    const text = model.text.recovery;
    const assessmentDisabled = this._buttonDisabled(
      model.recoveryAssessmentState, "recovery_assessment"
    ) ? "disabled" : "";
    const presentation = model.adaptivePolicy?.presentation || "balanced";
    const compact = presentation === "compact";
    const enterprise = presentation === "enterprise";
    const profileLabel = text.profileLabels?.[presentation] || this._humanize(presentation);
    return `<section class="hero ${model.evidenceTone}">
      <div class="hero-copy">
        <div class="eyebrow"><span></span>${this._escape(text.evidenceTitle)}</div>
        <h2>${this._escape(model.evidenceLabel)}</h2>
        <p>${this._escape(model.evidenceDescription)}</p>
      </div>
      <div class="evidence-orb ${model.evidenceTone}">
        <ha-icon icon="mdi:shield-home-outline"></ha-icon>
      </div>
    </section>
    <section class="metrics recovery-summary">
      ${this._metric("mdi:shield-check-outline", text.evidenceTitle, model.evidenceLabel, model.evidenceTone)}
      ${this._metric("mdi:clipboard-check-outline", text.recommendation, model.recoveryRecommendationLabel, model.recoveryRecommendationCode === "none" ? "good" : "warning")}
      ${compact ? "" : this._metric("mdi:tune-variant", text.adaptiveTitle, profileLabel, "neutral")}
    </section>
    <section class="content-grid recovery-grid">
      <article class="card storage-card simulation-card primary-recovery-card">
        <div class="card-title"><ha-icon icon="mdi:shield-search"></ha-icon><h3>${this._escape(text.simulationTitle)}</h3></div>
        <p class="preparedness-intro">${this._escape(text.simulationIntro)}</p>
        ${this._simulationRows(model.restoreSimulation, text, compact)}
        ${this._runtimeRows(model.runtimeTest, text)}
        ${model.isAdmin ? `<div class="card-actions"><button class="action primary" data-action="recovery_assessment" ${assessmentDisabled}><ha-icon icon="mdi:shield-search"></ha-icon>${this._escape(text.protectionCheck)}</button></div>` : ""}
      </article>
      <article class="card">
        <div class="card-title"><ha-icon icon="mdi:alert-decagram-outline"></ha-icon><h3>${this._escape(text.openRisksTitle)}</h3></div>
        <div class="rows">${this._riskRows(model.recoveryOpenRisks, text)}</div>
      </article>
      <article class="card preparedness-card">
        <div class="card-title"><ha-icon icon="mdi:connection"></ha-icon><h3>${this._escape(text.dependenciesTitle)}</h3></div>
        <p class="preparedness-intro">${this._escape(text.dependenciesIntro)}</p>
        <div class="preparedness-list">${this._preparednessRows(model.recoveryPreparedness, "dependencies", text, model.isAdmin)}</div>
        <p class="preparedness-note">${this._escape(this._preparednessReviewText(model.recoveryPreparedness, text))}${model.isAdmin ? "" : ` ${this._escape(text.adminOnly)}`}</p>
      </article>
    </section>
    <details class="card advanced-recovery" ${enterprise ? "open" : ""}>
      <summary><ha-icon icon="mdi:information-outline"></ha-icon>${this._escape(text.technicalDetails)}</summary>
      <section class="content-grid recovery-details">
        <article class="detail-panel">
          <div class="card-title"><ha-icon icon="mdi:archive-eye-outline"></ha-icon><h3>${this._escape(text.inventoryTitle)}</h3></div>
          <div class="rows">${this._contentInventoryRows(model.recoveryContentInventory, text)}</div>
        </article>
        <article class="detail-panel">
          <div class="card-title"><ha-icon icon="mdi:compare-horizontal"></ha-icon><h3>${this._escape(text.comparisonTitle)}</h3></div>
          <div class="rows">${this._contentComparisonRows(model.recoveryContentComparison, text)}</div>
        </article>
        <article class="detail-panel">
          <div class="card-title"><ha-icon icon="mdi:server-security"></ha-icon><h3>${this._escape(text.storageTitle)}</h3></div>
          <div class="rows">${this._storageResilienceRows(model.recoveryStorageResilience, text)}</div>
        </article>
        <article class="detail-panel preparedness-card">
          <div class="card-title"><ha-icon icon="mdi:clipboard-check-multiple-outline"></ha-icon><h3>${this._escape(text.preparednessTitle)}</h3></div>
          <p class="preparedness-intro">${this._escape(text.preparednessIntro)}</p>
          <div class="preparedness-list">${this._preparednessRows(model.recoveryPreparedness, "checklist", text, model.isAdmin)}</div>
        </article>
        <article class="detail-panel">
          <div class="card-title"><ha-icon icon="mdi:restore-clock"></ha-icon><h3>${this._escape(text.optionalEvidence)}</h3></div>
          <p class="preparedness-intro">${this._escape(text.restoreTestIntro)}</p>
          <div class="rows">${this._restoreTestRows(model.restoreTest, text)}</div>
          ${this._restoreTestControls(text, model.isAdmin)}
        </article>
        <article class="detail-panel">
          <div class="card-title"><ha-icon icon="mdi:file-document-check-outline"></ha-icon><h3>${this._escape(text.planTitle)}</h3></div>
          <p class="preparedness-intro">${this._escape(text.planIntro)}</p>
          <div class="rows">${this._planRows(model.recoveryPlan, text)}</div>
          ${this._planExportButtons(model.recoveryPlan, text)}
        </article>
        <article class="detail-panel storage-card">
          <div class="card-title"><ha-icon icon="mdi:chart-donut"></ha-icon><h3>${this._escape(text.score)}: ${this._escape(model.recoveryScoreLabel)}</h3></div>
          <div class="rows">${this._recoveryDeductionRows(model.recoveryDeductions, text)}</div>
        </article>
      </section>
    </details>
    ${this._actionFooter(model, false)}`;
  }

  _activityMessage(record, text) {
    const action = record.action === "service_simulate_restore"
      ? text.recovery.simulationActivity
      : text.activityActions[record.action] || this._humanize(record.action);
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
    if (action.includes("integrity") || action.includes("verification") || action.includes("simulate_restore")) return "check";
    return "system";
  }

  _activityAdvice(record, text) {
    if (!["failed", "skipped", "cancelled"].includes(record.outcome)) return "";
    const code = record.details?.error_code || record.details?.reason || record.details?.error_type;
    if (!code) return "";
    const message = this._friendlyError(code, text);
    const recommendation = this._friendlyRecommendation(code, text);
    const advice = recommendation
      ? `<span>${this._escape(text.nextStep)}: ${this._escape(recommendation)}</span>`
      : "";
    return `<div class="log-advice"><strong>${this._escape(message)}</strong>${advice}</div>`;
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

  _configError(key, text) {
    const code = this._configState.errors?.[key];
    return code ? `<span class="config-error">${this._escape(text.errors[code] || code)}</span>` : "";
  }

  _configSelect(key, options, text) {
    const value = this._configState.draft?.[key];
    const choices = (options || []).map((option) => `<option value="${this._escape(option)}" ${option === value ? "selected" : ""}>${this._escape(text.optionLabels[option] || this._humanize(option))}</option>`).join("");
    return `<label class="config-field"><span>${this._escape(text[key] || key)}</span><select data-config-key="${this._escape(key)}">${choices}</select>${this._configError(key, text)}</label>`;
  }

  _configNumber(key, text, limits) {
    const value = this._configState.draft?.[key];
    const limit = limits?.[key] || {};
    return `<label class="config-field"><span>${this._escape(text[key] || key)}</span><input type="number" step="1" min="${this._escape(limit.min ?? "")}" max="${this._escape(limit.max ?? "")}" value="${this._escape(value ?? "")}" data-config-key="${this._escape(key)}">${this._configError(key, text)}</label>`;
  }

  _configToggle(key, text) {
    const checked = this._configState.draft?.[key] ? "checked" : "";
    return `<label class="config-toggle"><input type="checkbox" data-config-key="${this._escape(key)}" ${checked}><span><strong>${this._escape(text[key] || key)}</strong></span></label>${this._configError(key, text)}`;
  }

  _notificationTargetField(data, text) {
    const targets = data?.options?.notification_targets || [];
    const selected = new Set(this._configState.draft?.notification_targets || []);
    if (!targets.length) return `<div class="config-field"><span>${this._escape(text.notification_targets)}</span><p class="config-hint">${this._escape(text.noTargets)}</p>${this._configError("notification_targets", text)}</div>`;
    const options = targets.map((target) => `<option value="${this._escape(target.value)}" ${selected.has(target.value) ? "selected" : ""}>${this._escape(target.label)}</option>`).join("");
    return `<label class="config-field"><span>${this._escape(text.notification_targets)}</span><select multiple size="${Math.min(6, Math.max(2, targets.length))}" data-config-key="notification_targets">${options}</select><small>${this._escape(text.selectMultiple)}</small>${this._configError("notification_targets", text)}</label>`;
  }

  _configSection(title, help, content) {
    return `<article class="card config-card"><div class="card-title"><ha-icon icon="mdi:tune-variant"></ha-icon><div><h3>${this._escape(title)}</h3><p>${this._escape(help)}</p></div></div><div class="config-grid">${content}</div></article>`;
  }

  _settingsTemplate(model) {
    const text = model.text.config;
    const state = this._configState;
    if (!model.isAdmin) return `<article class="card config-message"><ha-icon icon="mdi:shield-lock-outline"></ha-icon><p>${this._escape(text.adminOnly)}</p></article>`;
    if (["idle", "loading"].includes(state.status)) return `<article class="card config-message"><ha-circular-progress active></ha-circular-progress><p>${this._escape(text.loading)}</p></article>`;
    if (state.status === "error" || !state.data || !state.draft) return `<article class="card config-message danger"><ha-icon icon="mdi:alert-circle-outline"></ha-icon><p>${this._escape(text.loadFailed)}</p><button class="action secondary" data-config-retry><ha-icon icon="mdi:refresh"></ha-icon>${this._escape(model.text.refresh)}</button></article>`;

    const data = state.data;
    const draft = state.draft;
    const limits = data.limits || {};
    const options = data.options || {};
    const hardware = data.hardware || {};
    const runtimeCustom = draft.runtime_profile === "custom";
    const monitoringCustom = draft.monitoring_policy === "custom";
    const verificationCustom = draft.verification_policy === "custom";
    const hardwareCard = `<article class="card config-hardware"><div class="card-title"><ha-icon icon="mdi:chip"></ha-icon><h3>${this._escape(text.hardware)}</h3></div><div class="rows">
      ${this._recoveryDetailRow(text.recommended, text.optionLabels[hardware.recommended_profile] || this._humanize(hardware.recommended_profile || "—"))}
      ${this._recoveryDetailRow(text.installationType, hardware.installation_type || "—")}
      ${this._recoveryDetailRow(text.architecture, hardware.architecture || "—")}
      ${this._recoveryDetailRow(text.board, hardware.board || "—")}
    </div></article>`;

    let runtimeFields = this._configSelect("runtime_profile", options.runtime_profiles, text) + this._configToggle("adaptive_polling", text);
    if (runtimeCustom) runtimeFields += ["update_interval_minutes", "active_update_interval_minutes", "error_backoff_interval_minutes", "adaptive_error_threshold", "max_verification_size_gb", "max_expanded_size_gb", "verification_timeout_minutes", "database_timeout_minutes", "manual_verification_cooldown_minutes"].map((key) => this._configNumber(key, text, limits)).join("");
    runtimeFields += this._configError("runtime", text);

    let monitoringFields = this._configSelect("monitoring_policy", options.monitoring_policies, text);
    if (monitoringCustom) monitoringFields += this._configNumber("max_age_days", text, limits) + this._configSelect("size_check_mode", options.size_check_modes, text) + this._configNumber("minimum_backup_size_mb", text, limits) + this._configNumber("maximum_size_drop_percent", text, limits) + this._configNumber("minimum_redundant_locations", text, limits) + this._configToggle("repair_issues_enabled", text) + this._configNumber("analytics_window_days", text, limits);
    monitoringFields += this._configError("monitoring", text);

    let verificationFields = this._configSelect("verification_policy", options.verification_policies, text) + this._configNumber("manual_verification_cooldown_minutes", text, limits);
    if (verificationCustom) verificationFields += this._configToggle("auto_verify_new_backups", text) + this._configToggle("database_integrity_check", text);

    const presentationFields = this._configSelect("entity_mode", options.entity_modes, text)
      + this._configToggle("expose_backup_metadata", text)
      + this._configToggle("show_sidebar_panel", text)
      + this._configToggle("activity_logging_enabled", text)
      + this._configToggle("activity_log_persistence", text)
      + this._configNumber("activity_log_retention_days", text, limits)
      + this._configToggle("notifications_enabled", text)
      + this._notificationTargetField(data, text)
      + this._configToggle("notify_on_recovery", text);

    const baseError = this._configError("base", text);
    const saved = state.saved ? `<div class="config-success"><ha-icon icon="mdi:check-circle-outline"></ha-icon>${this._escape(text.saved)}</div>` : "";
    const saving = state.status === "saving";
    const disabled = saving ? "disabled" : "";
    const saveLabel = saving ? text.saving : text.save;
    return `<section class="config-page"><section class="config-intro"><div><h2>${this._escape(text.title)}</h2><p>${this._escape(text.subtitle)}</p></div><span><ha-icon icon="mdi:reload"></ha-icon>${this._escape(text.reloadNotice)}</span></section>${saved}${baseError}<section class="content-grid config-top">${hardwareCard}${this._configSection(text.runtime, text.runtimeHelp, runtimeFields)}</section>${this._configSection(text.monitoring, text.monitoringHelp, monitoringFields)}${this._configSection(text.verification, text.verificationHelp, verificationFields)}${this._configSection(text.presentation, text.presentationHelp, presentationFields)}<footer class="config-footer"><button class="action secondary" data-config-reset ${disabled}><ha-icon icon="mdi:undo-variant"></ha-icon>${this._escape(text.reset)}</button><button class="action primary" data-config-save ${disabled}><ha-icon icon="mdi:content-save-outline"></ha-icon>${this._escape(saveLabel)}</button></footer></section>`;
  }

  async _callWS(message) {
    if (typeof this._hass?.callWS === "function") return this._hass.callWS(message);
    const response = await this._hass.connection.sendMessagePromise(message);
    return response?.result ?? response;
  }

  _clone(value) {
    if (Array.isArray(value)) return value.map((item) => this._clone(item));
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [key, this._clone(item)])
      );
    }
    return value;
  }

  async _loadConfiguration(force = false) {
    if (!this._hass?.user?.is_admin || (!force && ["loading", "ready", "saving"].includes(this._configState.status))) return;
    this._configState = { ...this._configState, status: "loading", errors: {}, saved: false };
    this._scheduleRender();
    try {
      const data = await this._callWS({ type: "backup_checkup/config/get", entry_id: this._panel?.config?.entry_id });
      this._configState = { status: "ready", data, draft: this._clone(data.values || {}), errors: {}, saved: false };
    } catch (error) {
      console.warn("BackupCheckup configuration loading failed", error);
      this._configState = { status: "error", data: null, draft: null, errors: {}, saved: false };
    }
    this._scheduleRender();
  }

  _setConfigValue(element) {
    const key = element.dataset.configKey;
    if (!key || !this._configState.draft) return;
    let value;
    if (element.type === "checkbox") value = element.checked;
    else if (element.multiple) value = [...element.selectedOptions].map((option) => option.value);
    else if (element.type === "number") value = Number(element.value);
    else value = element.value;
    this._configState.draft[key] = value;
    delete this._configState.errors[key];
    delete this._configState.errors.runtime;
    delete this._configState.errors.monitoring;
    this._configState.saved = false;
    this._scheduleRender();
  }

  _resetConfiguration() {
    if (!this._configState.data) return;
    this._configState = { ...this._configState, status: "ready", draft: this._clone(this._configState.data.values || {}), errors: {}, saved: false };
    this._scheduleRender();
  }

  async _saveConfiguration() {
    if (!this._hass?.user?.is_admin || this._configState.status === "saving" || !this._configState.draft) return;
    this._configState = { ...this._configState, status: "saving", errors: {}, saved: false };
    this._scheduleRender();
    try {
      const result = await this._callWS({ type: "backup_checkup/config/update", entry_id: this._panel?.config?.entry_id, values: this._configState.draft });
      if (!result?.success) {
        this._configState = { ...this._configState, status: "ready", errors: result?.errors || { base: "invalid_payload" }, saved: false };
      } else {
        const data = { ...this._configState.data, values: result.values };
        this._configState = { status: "ready", data, draft: this._clone(result.values || {}), errors: {}, saved: true };
        this.dispatchEvent(new CustomEvent("hass-notification", { bubbles: true, composed: true, detail: { message: this._text().config.saved } }));
      }
    } catch (error) {
      console.warn("BackupCheckup configuration saving failed", error);
      this._configState = { ...this._configState, status: "ready", errors: { base: "invalid_payload" }, saved: false };
    }
    this._scheduleRender();
  }

  _logTemplate(model) {
    if (!model.activityEnabled) {
      return `<section class="log-disabled">
        <ha-icon icon="mdi:text-box-remove-outline"></ha-icon>
        <p>${this._escape(model.text.loggingDisabled)}</p>
      </section>`;
    }
    const clearDisabled = this._buttonDisabled(model.clearActivityState, "clear_activity_log")
      ? "disabled"
      : "";
    const clearButton = model.isAdmin
      ? `<button class="log-action danger" data-action="clear_activity_log" ${clearDisabled}><ha-icon icon="mdi:delete-sweep-outline"></ha-icon>${this._escape(model.text.clearLog)}</button>`
      : "";
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
          ${clearButton}
        </div></div>
        <div class="log-lines">${this._logRows(model.activityEntries, model.text)}</div>
      </article>
    </section>`;
  }

  _updateLogRenderState(model, previousLogState) {
    if (this._activeTab !== "logs") return;
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

  _activeTemplate(model) {
    if (this._activeTab === "settings") return this._settingsTemplate(model);
    if (this._activeTab === "logs") return this._logTemplate(model);
    if (this._activeTab === "recovery") return this._recoveryTemplate(model);
    return this._overviewTemplate(model);
  }

  _bindConfigurationEvents() {
    this.shadowRoot.querySelector('[data-nav="settings"]')?.addEventListener("click", () => this._openSettings());
    this.shadowRoot.querySelector("[data-config-retry]")?.addEventListener("click", () => this._loadConfiguration(true));
    this.shadowRoot.querySelector("[data-config-reset]")?.addEventListener("click", () => this._resetConfiguration());
    this.shadowRoot.querySelector("[data-config-save]")?.addEventListener("click", () => this._saveConfiguration());
    this.shadowRoot.querySelectorAll("[data-config-key]").forEach((element) => {
      element.addEventListener("change", () => this._setConfigValue(element));
    });
  }

  _bindNavigationEvents(model) {
    this.shadowRoot.querySelectorAll("[data-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        this._activeTab = button.dataset.tab;
        if (this._activeTab === "logs") {
          this._scrollLogToBottom = true;
          this._pendingLogEntries = 0;
        }
        if (this._activeTab === "settings") this._loadConfiguration();
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
  }

  _bindRecoveryEvents(model) {
    this.shadowRoot.querySelectorAll("[data-preparedness-section]").forEach((select) => {
      select.addEventListener("change", () => {
        this._setRecoveryPreparedness(
          select.dataset.preparednessSection,
          select.dataset.preparednessItem,
          select.value
        );
      });
    });
    this.shadowRoot.querySelector("[data-record-restore]")?.addEventListener("click", () => {
      const result = this.shadowRoot.querySelector("[data-restore-result]")?.value;
      const scope = this.shadowRoot.querySelector("[data-restore-scope]")?.value;
      this._recordRestoreTest(result, scope);
    });
    this.shadowRoot.querySelectorAll("[data-export-plan]").forEach((button) => {
      button.addEventListener("click", () => this._exportRecoveryPlan(model, button.dataset.exportPlan));
    });
  }

  _bindLogEvents(model, restoreSearchFocus, previousLogState) {
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
    this._restoreLogPosition(previousLogState);
  }

  _restoreLogPosition(previousLogState) {
    const currentLog = this.shadowRoot.querySelector(".log-lines");
    if (!currentLog) return;
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
    this._updateLogRenderState(model, previousLogState);
    if (this._activeTab === "settings" && !model.isAdmin) this._activeTab = "overview";
    const content = this._activeTemplate(model);
    const settingsButton = this._settingsButton(model.isAdmin, model.text);

    this.shadowRoot.innerHTML = `
      <style>${BackupCheckupPanel.styles}</style>
      <main>
        <header>
          <div class="brand"><ha-icon icon="mdi:backup-restore"></ha-icon></div>
          <div><h1>${this._escape(model.text.dashboard)}</h1><p>${this._escape(model.text.subtitle)}</p></div>
          ${settingsButton}
        </header>
        ${this._tabs(model.text, model.isAdmin)}
        ${content}
      </main>`;

    this._bindConfigurationEvents();
    this._bindNavigationEvents(model);
    this._bindRecoveryEvents(model);
    this._bindLogEvents(model, restoreSearchFocus, previousLogState);
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

  async _setRecoveryPreparedness(section, item, status) {
    this._preparednessDraft ||= new Map();
    const action = `preparedness:${section}:${item}`;
    const draftKey = `${section}:${item}`;
    if (!this._hass?.user?.is_admin || this._busy.has(action)) return;
    this._preparednessDraft.set(draftKey, status);
    this._busy.add(action);
    this._scheduleRender();
    try {
      await this._hass.callService("backup_checkup", "set_recovery_preparedness", { section, item, status });
    } catch (_error) {
      this._preparednessDraft.delete(draftKey);
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

  async _recordRestoreTest(result, scope) {
    const action = "record_restore_test";
    if (!this._hass?.user?.is_admin || this._busy.has(action) || !result || !scope) return;
    this._busy.add(action);
    this._scheduleRender();
    try {
      await this._hass.callService("backup_checkup", "record_restore_test", { result, scope });
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

  _exportRecoveryPlan(model, format) {
    const content = model.recoveryPlan?.exports?.[format];
    if (!content) return;
    const types = { markdown: "text/markdown", html: "text/html", json: "application/json" };
    const extensions = { markdown: "md", html: "html", json: "json" };
    const blob = new Blob([content], { type: `${types[format] || "text/plain"};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `backup-checkup-recovery-plan-${new Date().toISOString().slice(0, 10)}.${extensions[format] || "txt"}`;
    link.click();
    URL.revokeObjectURL(url);
  }

  _openSettings() {
    if (!this._hass?.user?.is_admin) return;
    this._activeTab = "settings";
    this._relevantStateChanged(this._hass);
    this._loadConfiguration();
    this._scheduleRender();
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
      .hero.warning { --tone:#e79a24; --tone-soft:rgba(231,154,36,.18); }
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
      .evidence-orb { --evidence:#607d8b; flex:0 0 auto; width:132px; height:132px; margin-left:32px; display:grid; place-items:center; border-radius:50%; color:var(--evidence); background:color-mix(in srgb, var(--evidence) 14%, var(--card-background-color)); border:2px solid color-mix(in srgb, var(--evidence) 48%, var(--divider-color)); position:relative; z-index:1; }
      .evidence-orb.good { --evidence:#2e9d68; } .evidence-orb.warning { --evidence:#e79a24; } .evidence-orb.danger { --evidence:#d84b55; }
      .evidence-orb ha-icon { --mdc-icon-size:54px; }
      .metrics { display:grid; grid-template-columns:repeat(auto-fit, minmax(175px, 1fr)); gap:13px; margin:18px 0; }
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
      .recovery-summary { grid-template-columns:repeat(3, minmax(0, 1fr)); }
      .recovery-grid { grid-template-columns:minmax(0, 1.15fr) minmax(0, .85fr); }
      .primary-recovery-card { grid-column:1 / -1; }
      .advanced-recovery { margin-top:18px; }
      .advanced-recovery > summary { display:flex; align-items:center; gap:10px; cursor:pointer; font-weight:650; list-style:none; }
      .advanced-recovery > summary::-webkit-details-marker { display:none; }
      .advanced-recovery > summary::after { content:"⌄"; margin-left:auto; color:var(--secondary-text-color); font-size:20px; }
      .advanced-recovery[open] > summary::after { content:"⌃"; }
      .advanced-recovery > .content-grid { margin-top:22px; }
      .detail-panel { min-width:0; padding:18px; border:1px solid var(--divider-color); border-radius:15px; background:color-mix(in srgb, var(--card-background-color) 96%, var(--primary-color)); }
      .recovery-checks-card, .recovery-deductions-card { grid-column:1 / -1; }
      .recovery-check-grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px; }
      .recovery-check { min-height:72px; display:flex; align-items:center; gap:11px; padding:13px; border:1px solid var(--divider-color); border-radius:13px; background:color-mix(in srgb, var(--card-background-color) 94%, var(--primary-color)); }
      .recovery-check ha-icon { flex:0 0 auto; color:#607d8b; --mdc-icon-size:23px; }
      .recovery-check.good ha-icon { color:#2e9d68; }
      .recovery-check.danger ha-icon { color:#d84b55; }
      .recovery-check div { min-width:0; display:flex; flex-direction:column; gap:4px; }
      .recovery-check strong { font-size:13px; line-height:1.3; }
      .recovery-check span { color:var(--secondary-text-color); font-size:11px; }
      .preparedness-intro, .preparedness-note { margin:0 0 15px; color:var(--secondary-text-color); font-size:12px; line-height:1.5; }
      .preparedness-note { margin:14px 0 0; }
      .preparedness-list { display:flex; flex-direction:column; }
      .preparedness-row { display:grid; grid-template-columns:minmax(0, 1fr) auto minmax(160px, auto); align-items:center; gap:12px; min-height:66px; border-top:1px solid var(--divider-color); }
      .preparedness-row:first-child { border-top:0; }
      .preparedness-copy { min-width:0; display:flex; flex-direction:column; gap:4px; }
      .preparedness-copy strong { font-size:13px; line-height:1.35; }
      .preparedness-copy span { color:var(--secondary-text-color); font-size:11px; }
      .preparedness-badges { display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end; }
      .preparedness-badge { padding:4px 7px; border-radius:999px; font-size:10px; font-weight:700; }
      .preparedness-badge.detected { background:rgba(33,150,243,.13); color:#1976d2; }
      .preparedness-badge.expired { background:rgba(231,154,36,.14); color:#b87300; }
      .preparedness-row select { width:100%; min-height:38px; padding:6px 9px; border:1px solid var(--divider-color); border-radius:9px; background:var(--card-background-color); color:var(--primary-text-color); font:inherit; font-size:12px; }
      .preparedness-row select:disabled { opacity:.68; }
      .simulation-dashboard { --simulation-tone:#607d8b; --simulation-soft:rgba(96,125,139,.12); display:flex; flex-direction:column; gap:14px; padding:18px; border:1px solid color-mix(in srgb, var(--simulation-tone) 26%, var(--divider-color)); border-radius:16px; background:linear-gradient(145deg, var(--simulation-soft), transparent 48%); }
      .simulation-dashboard.good { --simulation-tone:#2e9d68; --simulation-soft:rgba(46,157,104,.12); }
      .simulation-dashboard.warning { --simulation-tone:#e79a24; --simulation-soft:rgba(231,154,36,.12); }
      .simulation-dashboard.danger { --simulation-tone:#d84b55; --simulation-soft:rgba(216,75,85,.12); }
      .simulation-head { display:flex; align-items:center; justify-content:space-between; gap:18px; }
      .simulation-state { display:flex; align-items:center; gap:11px; }
      .simulation-state > span { width:12px; height:12px; border-radius:50%; background:var(--simulation-tone); box-shadow:0 0 0 6px var(--simulation-soft); }
      .simulation-state div, .simulation-current { display:flex; flex-direction:column; gap:3px; }
      .simulation-state small, .simulation-current small { color:var(--secondary-text-color); font-size:11px; }
      .simulation-state strong { color:var(--simulation-tone); font-size:17px; }
      .simulation-current { align-items:flex-end; text-align:right; }
      .simulation-current strong { font-size:13px; }
      .simulation-progress { height:10px; overflow:hidden; border-radius:999px; background:color-mix(in srgb, var(--divider-color) 72%, transparent); }
      .simulation-progress > div { height:100%; min-width:0; border-radius:inherit; background:linear-gradient(90deg, color-mix(in srgb, var(--simulation-tone) 72%, white), var(--simulation-tone)); transition:width 1.2s cubic-bezier(.22, 1, .36, 1); }
      .simulation-progress-label { display:flex; justify-content:space-between; margin-top:-8px; color:var(--secondary-text-color); font-size:11px; }
      .simulation-progress-label strong { color:var(--simulation-tone); }
      .simulation-pipeline { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:9px; }
      .simulation-stage { min-height:66px; display:flex; align-items:center; gap:9px; padding:10px; border:1px solid var(--divider-color); border-radius:11px; background:var(--card-background-color); }
      .simulation-stage ha-icon { flex:0 0 auto; color:#90a4ae; --mdc-icon-size:21px; }
      .simulation-stage.passed ha-icon { color:#2e9d68; }
      .simulation-stage.failed ha-icon { color:#d84b55; }
      .simulation-stage.warning ha-icon, .simulation-stage.running ha-icon { color:#e79a24; }
      .simulation-stage.running { border-color:color-mix(in srgb, var(--simulation-tone) 55%, var(--divider-color)); box-shadow:0 0 0 2px var(--simulation-soft); }
      .simulation-stage div { min-width:0; display:flex; flex-direction:column; gap:3px; }
      .simulation-stage strong { font-size:11px; line-height:1.25; }
      .simulation-stage span { color:var(--secondary-text-color); font-size:10px; }
      .simulation-metrics { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:9px; }
      .simulation-metrics > div { display:grid; grid-template-columns:auto 1fr; gap:3px 8px; align-items:center; padding:11px; border-radius:11px; background:color-mix(in srgb, var(--card-background-color) 88%, var(--simulation-tone)); }
      .simulation-metrics ha-icon { grid-row:1 / 3; color:var(--simulation-tone); --mdc-icon-size:22px; }
      .simulation-metrics span { color:var(--secondary-text-color); font-size:10px; }
      .simulation-metrics strong { font-size:14px; }
      .simulation-check-summary { display:grid; grid-template-columns:repeat(3, 1fr); gap:9px; }
      .simulation-check-summary > div { display:flex; align-items:center; gap:9px; padding:10px 12px; border-radius:10px; background:var(--card-background-color); }
      .simulation-check-summary strong { font-size:20px; }
      .simulation-check-summary span { color:var(--secondary-text-color); font-size:11px; }
      .simulation-check-summary .good strong { color:#2e9d68; }
      .simulation-check-summary .warning strong { color:#e79a24; }
      .simulation-check-summary .danger strong { color:#d84b55; }
      .simulation-safety { display:flex; align-items:center; gap:8px; margin:0; color:var(--secondary-text-color); font-size:11px; line-height:1.45; }
      .simulation-safety ha-icon { flex:0 0 auto; color:#2e9d68; --mdc-icon-size:19px; }
      .runtime-phase { display:flex; flex-direction:column; gap:12px; margin-top:18px; padding-top:18px; border-top:1px solid var(--divider-color); }
      .runtime-heading { display:flex; gap:11px; align-items:flex-start; }
      .runtime-heading > ha-icon { flex:0 0 auto; color:var(--primary-color); --mdc-icon-size:24px; }
      .runtime-heading > div { display:flex; flex-direction:column; gap:4px; }
      .runtime-heading strong { font-size:14px; }
      .runtime-heading span { color:var(--secondary-text-color); font-size:12px; line-height:1.45; }
      .runtime-empty { margin-top:18px; border-top:1px solid var(--divider-color); padding-top:18px; }
      .restore-test-controls, .plan-actions, .card-actions { display:flex; flex-wrap:wrap; gap:9px; margin-top:16px; }
      .restore-test-controls select { min-height:42px; min-width:170px; flex:1; padding:6px 10px; border:1px solid var(--divider-color); border-radius:10px; background:var(--card-background-color); color:var(--primary-text-color); font:inherit; }
      .restore-test-controls .action { flex:1 1 220px; justify-content:center; }
      .plan-actions .action, .card-actions .action { justify-content:center; }
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
      .empty.danger ha-icon { color:#d84b55; }
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
      @media (max-width:900px) { .metrics { grid-template-columns:repeat(2, minmax(0, 1fr)); } .recovery-check-grid { grid-template-columns:repeat(2, minmax(0, 1fr)); } .content-grid, .recovery-grid { grid-template-columns:1fr; } .storage-card { grid-column:auto; } .primary-recovery-card { grid-column:auto; } .simulation-pipeline, .simulation-metrics { grid-template-columns:repeat(2, minmax(0, 1fr)); } .log-row { grid-template-columns:165px 1fr; } .log-row span { grid-column:2; } }
      @media (max-width:620px) { .restore-test-controls, .plan-actions, .card-actions { flex-direction:column; } .restore-test-controls select { width:100%; } .preparedness-row { grid-template-columns:1fr; gap:7px; padding:11px 0; } .preparedness-badges { justify-content:flex-start; } .simulation-head { align-items:flex-start; flex-direction:column; } .simulation-current { align-items:flex-start; text-align:left; } .simulation-pipeline, .simulation-metrics { grid-template-columns:1fr; } .simulation-check-summary { grid-template-columns:1fr; } main { padding:18px 12px 28px; } header { padding:0 4px; } header p { display:none; } .tabs { margin-top:0; } .hero { min-height:0; padding:24px 21px; } .score, .evidence-orb { width:104px; height:104px; margin-left:14px; } .evidence-orb ha-icon { --mdc-icon-size:42px; } .score::before { inset:8px; } .score strong { font-size:27px; } .hero h2 { font-size:23px; } .metrics { grid-template-columns:1fr 1fr; gap:10px; } .metrics.recovery-summary, .recovery-check-grid { grid-template-columns:1fr; } .metric { min-height:95px; padding:15px; } .content-grid { gap:12px; } .card { padding:18px; } .log-toolbar { align-items:stretch; flex-direction:column; } .live-indicator { align-self:flex-end; } .log-row { grid-template-columns:1fr; gap:3px; padding:10px 13px; } .log-row span { grid-column:auto; } footer { flex-direction:column-reverse; } .action { justify-content:center; } }
      @media (max-width:390px) { .hero { align-items:flex-start; } .score { width:88px; height:88px; } .score span { display:none; } .metrics { grid-template-columns:1fr; } }

      .config-page { display:flex; flex-direction:column; gap:18px; }
      .config-intro { display:flex; justify-content:space-between; align-items:flex-start; gap:24px; padding:26px 28px; border-radius:20px; background:var(--card-background-color); box-shadow:var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,.08)); }
      .config-intro h2 { margin:0 0 8px; font-size:25px; }
      .config-intro p { margin:0; color:var(--secondary-text-color); }
      .config-intro > span { display:flex; align-items:center; gap:8px; max-width:330px; padding:10px 13px; border-radius:12px; background:color-mix(in srgb, var(--primary-color) 10%, transparent); color:var(--secondary-text-color); font-size:12px; }
      .config-top { grid-template-columns:minmax(260px, .7fr) minmax(0, 1.3fr); }
      .config-card { margin:0; }
      .config-card > .card-title { align-items:flex-start; }
      .config-card .card-title p { margin:5px 0 0; color:var(--secondary-text-color); font-size:12px; font-weight:400; }
      .config-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(245px, 1fr)); gap:16px 18px; margin-top:20px; }
      .config-field { display:flex; flex-direction:column; gap:7px; min-width:0; }
      .config-field > span { font-size:13px; font-weight:600; }
      .config-field small, .config-hint { margin:0; color:var(--secondary-text-color); font-size:11px; }
      .config-field input, .config-field select { width:100%; min-height:42px; padding:9px 11px; border:1px solid var(--divider-color); border-radius:10px; background:var(--card-background-color); color:var(--primary-text-color); font:inherit; }
      .config-field select[multiple] { min-height:96px; }
      .config-toggle { display:flex; align-items:flex-start; gap:11px; min-height:42px; padding:10px 12px; border:1px solid var(--divider-color); border-radius:10px; cursor:pointer; }
      .config-toggle input { width:18px; height:18px; margin:1px 0 0; accent-color:var(--primary-color); }
      .config-toggle strong { font-size:13px; line-height:1.35; }
      .config-error { display:block; grid-column:1/-1; color:var(--error-color, #db4437); font-size:12px; font-weight:600; }
      .config-success { display:flex; align-items:center; gap:9px; padding:13px 16px; border-radius:12px; background:rgba(46,157,104,.14); color:#2e9d68; font-weight:600; }
      .config-message { min-height:180px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px; text-align:center; }
      .config-message > ha-icon { --mdc-icon-size:36px; }
      .config-message.danger { color:var(--error-color, #db4437); }
      .config-footer { position:sticky; bottom:0; z-index:3; display:flex; justify-content:flex-end; gap:12px; padding:16px 0 4px; background:linear-gradient(transparent, var(--primary-background-color) 24%); }
    `;
  }
}

if (!customElements.get(PANEL_ELEMENT_NAME)) {
  customElements.define(PANEL_ELEMENT_NAME, BackupCheckupPanel);
}
