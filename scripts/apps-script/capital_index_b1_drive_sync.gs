/**
 * CAPITAL INDEX 2026 - Stage B1 Drive -> Files sync.
 *
 * Purpose:
 * 1. Scan Google Drive metadata.
 * 2. Compare Drive file IDs with the `Files` sheet.
 * 3. Append only missing files.
 * 4. Mark new rows with the next safe enrichment status.
 *
 * Required Apps Script setup:
 * - Extensions -> Apps Script -> Services -> enable "Drive API" advanced service.
 * - Google Cloud project APIs: Drive API enabled.
 *
 * This script does not read file content, does not call Gemini, and does not delete files.
 */

const CONFIG_B1 = {
  SS_ID: '1tJ72mlke07KGEEVUYWxcKpGRdo6nx8xF7_bHVDv7dpM',
  SHEET_NAME: 'Files',
  MAX_RUNTIME_MS: 240000,
  PAGE_SIZE: 100,
  MAX_FILES_PER_RUN: 3000,
  MAX_APPEND_PER_RUN: 500,
  RECENT_DAYS: 7,
  TRIGGER_HANDLER: 'syncDriveFilesToSheet',
  PAGE_TOKEN_PROPERTY: 'CAPITAL_INDEX_B1_PAGE_TOKEN',
  CHANGES_TOKEN_PROPERTY: 'CAPITAL_INDEX_B1_CHANGES_TOKEN',
  RUN_COUNT_PROPERTY: 'CAPITAL_INDEX_B1_RUN_COUNT',
  CHANGES_RUN_COUNT_PROPERTY: 'CAPITAL_INDEX_B1_CHANGES_RUN_COUNT',
  TOTAL_SCANNED_PROPERTY: 'CAPITAL_INDEX_B1_TOTAL_SCANNED',
  TOTAL_APPENDED_PROPERTY: 'CAPITAL_INDEX_B1_TOTAL_APPENDED',
  TOTAL_DUPLICATE_SKIPPED_PROPERTY: 'CAPITAL_INDEX_B1_TOTAL_DUPLICATE_SKIPPED',
  LAST_TOKEN_HASH_PROPERTY: 'CAPITAL_INDEX_B1_LAST_TOKEN_HASH',
  RECENT_MY_DRIVE_REPORT_SHEET: 'RECENT_MY_DRIVE_FILES',
  DEBUG_SEARCH_REPORT_SHEET: 'DRIVE_FILE_DEBUG_SEARCH'
};

const FILES_HEADERS = [
  'file_name',
  'file_id',
  'file_url',
  'parent_folder_name',
  'parent_folder_id',
  'mime_type',
  'created',
  'modified',
  'size_bytes',
  'owner',
  'project',
  'sub_topic',
  'type',
  'status',
  'summary_50w',
  'linked_projects',
  'value_score',
  'action',
  'enrichment_status'
];

function startDriveFilesSync() {
  cleanupDriveSyncTriggers();
  syncDriveFilesToSheet();
}

function resumeDriveFilesSync() {
  cleanupDriveSyncTriggers();
  syncDriveFilesToSheet();
}

function resetDriveFilesSync() {
  cleanupDriveSyncTriggers();
  resetDriveFilesSyncState_();
  syncDriveFilesToSheet();
}

function syncRecentDriveFilesToSheet() {
  return syncRecentMyDriveFilesToSheet();
}

function syncRecentMyDriveFilesToSheet() {
  const startTime = Date.now();
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = headerIndexes_(headers);
  const knownFileIds = loadKnownFileIds_(sheet, idx.file_id);

  const cutoff = new Date(Date.now() - CONFIG_B1.RECENT_DAYS * 24 * 60 * 60 * 1000).toISOString();
  let pageToken = null;
  let scanned = 0;
  let appended = 0;
  let duplicateSkipped = 0;
  let incompleteSearch = false;
  const rowsToAppend = [];

  do {
    const response = listRecentMyDriveFilesPage_(pageToken, cutoff);
    incompleteSearch = incompleteSearch || Boolean(response.incompleteSearch);
    const files = response.files || [];
    for (const file of files) {
      if (Date.now() - startTime > CONFIG_B1.MAX_RUNTIME_MS) break;
      scanned++;
      if (knownFileIds.has(file.id)) {
        duplicateSkipped++;
        continue;
      }
      rowsToAppend.push(makeFilesRow_(file, headers, idx));
      knownFileIds.add(file.id);
      appended++;
      if (rowsToAppend.length >= CONFIG_B1.MAX_APPEND_PER_RUN) break;
    }
    pageToken = response.nextPageToken || null;
    if (rowsToAppend.length >= CONFIG_B1.MAX_APPEND_PER_RUN) break;
    if (scanned >= CONFIG_B1.MAX_FILES_PER_RUN) break;
  } while (pageToken && Date.now() - startTime < CONFIG_B1.MAX_RUNTIME_MS);

  if (rowsToAppend.length > 0) {
    const startRow = sheet.getLastRow() + 1;
    sheet.getRange(startRow, 1, rowsToAppend.length, headers.length).setValues(rowsToAppend);
  }

  console.log(JSON.stringify({
    stage: 'B1_RECENT_MY_DRIVE_SYNC',
    recentDays: CONFIG_B1.RECENT_DAYS,
    cutoff,
    scanned,
    appended,
    duplicateSkipped,
    incompleteSearch,
    nextPageTokenPresent: Boolean(pageToken),
    sheetRows: sheet.getLastRow()
  }));
}

function auditRecentDriveFiles() {
  return auditRecentMyDriveFiles();
}

function auditRecentMyDriveFiles() {
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const cutoff = new Date(Date.now() - CONFIG_B1.RECENT_DAYS * 24 * 60 * 60 * 1000).toISOString();
  const rows = [[
    'file_id',
    'file_name',
    'mime_type',
    'parent_folder_id',
    'created_iso',
    'modified_iso',
    'owned_by_me',
    'parents',
    'owner',
    'file_url'
  ]];
  let pageToken = null;
  let scanned = 0;
  let incompleteSearch = false;

  do {
    const response = listRecentMyDriveFilesPage_(pageToken, cutoff);
    incompleteSearch = incompleteSearch || Boolean(response.incompleteSearch);
    const files = response.files || [];
    files.forEach(file => {
      scanned++;
      const row = driveFileCoverageRow_(file);
      rows.push([
        row.file_id,
        row.file_name,
        row.mime_type,
        row.parent_folder_id,
        row.created_iso,
        row.modified_iso,
        row.owned_by_me,
        row.parents,
        row.owner,
        row.file_url
      ]);
    });
    pageToken = response.nextPageToken || null;
    if (scanned >= CONFIG_B1.MAX_FILES_PER_RUN) break;
  } while (pageToken);

  writeReplaceRows_(ss, CONFIG_B1.RECENT_MY_DRIVE_REPORT_SHEET, rows);
  console.log(JSON.stringify({
    stage: 'RECENT_MY_DRIVE_FILES_AUDIT',
    recentDays: CONFIG_B1.RECENT_DAYS,
    cutoff,
    scanned,
    incompleteSearch,
    reportSheet: CONFIG_B1.RECENT_MY_DRIVE_REPORT_SHEET
  }));
}

function showDriveFilesSyncState() {
  const props = PropertiesService.getScriptProperties();
  const state = {
    pageTokenExists: Boolean(props.getProperty(CONFIG_B1.PAGE_TOKEN_PROPERTY)),
    pageTokenHash: tokenHash_(props.getProperty(CONFIG_B1.PAGE_TOKEN_PROPERTY)),
    lastTokenHash: props.getProperty(CONFIG_B1.LAST_TOKEN_HASH_PROPERTY) || '',
    runs: Number(props.getProperty(CONFIG_B1.RUN_COUNT_PROPERTY) || 0),
    totalScanned: Number(props.getProperty(CONFIG_B1.TOTAL_SCANNED_PROPERTY) || 0),
    totalAppended: Number(props.getProperty(CONFIG_B1.TOTAL_APPENDED_PROPERTY) || 0),
    totalDuplicateSkipped: Number(props.getProperty(CONFIG_B1.TOTAL_DUPLICATE_SKIPPED_PROPERTY) || 0)
  };
  console.log(JSON.stringify({stage: 'B1_DRIVE_SYNC_STATE', ...state}));
  return state;
}

function syncDriveFilesToSheet() {
  const startTime = Date.now();
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = headerIndexes_(headers);
  const knownFileIds = loadKnownFileIds_(sheet, idx.file_id);

  const props = PropertiesService.getScriptProperties();
  let pageToken = props.getProperty(CONFIG_B1.PAGE_TOKEN_PROPERTY) || null;
  const startTokenHash = tokenHash_(pageToken);
  let scanned = 0;
  let appended = 0;
  let duplicateSkipped = 0;
  let rowsToAppend = [];

  while (Date.now() - startTime < CONFIG_B1.MAX_RUNTIME_MS && scanned < CONFIG_B1.MAX_FILES_PER_RUN) {
    const response = listDriveFilesPage_(pageToken);
    const files = response.files || [];

    for (const file of files) {
      if (Date.now() - startTime > CONFIG_B1.MAX_RUNTIME_MS) break;
      scanned++;

      if (knownFileIds.has(file.id)) {
        duplicateSkipped++;
        continue;
      }

      const row = makeFilesRow_(file, headers, idx);
      rowsToAppend.push(row);
      knownFileIds.add(file.id);
      appended++;

      if (rowsToAppend.length >= CONFIG_B1.MAX_APPEND_PER_RUN) break;
    }

    if (rowsToAppend.length >= CONFIG_B1.MAX_APPEND_PER_RUN) {
      pageToken = response.nextPageToken || pageToken;
      break;
    }

    pageToken = response.nextPageToken || null;
    if (!pageToken) break;
  }

  if (rowsToAppend.length > 0) {
    const startRow = sheet.getLastRow() + 1;
    sheet.getRange(startRow, 1, rowsToAppend.length, headers.length).setValues(rowsToAppend);
  }

  cleanupDriveSyncTriggers();
  if (pageToken) {
    props.setProperty(CONFIG_B1.PAGE_TOKEN_PROPERTY, pageToken);
    props.setProperty(CONFIG_B1.LAST_TOKEN_HASH_PROPERTY, tokenHash_(pageToken));
    ScriptApp.newTrigger(CONFIG_B1.TRIGGER_HANDLER).timeBased().after(60000).create();
  } else {
    props.deleteProperty(CONFIG_B1.PAGE_TOKEN_PROPERTY);
    props.deleteProperty(CONFIG_B1.LAST_TOKEN_HASH_PROPERTY);
  }

  const runCount = incrementNumberProperty_(props, CONFIG_B1.RUN_COUNT_PROPERTY, 1);
  const totalScanned = incrementNumberProperty_(props, CONFIG_B1.TOTAL_SCANNED_PROPERTY, scanned);
  const totalAppended = incrementNumberProperty_(props, CONFIG_B1.TOTAL_APPENDED_PROPERTY, appended);
  const totalDuplicateSkipped = incrementNumberProperty_(
    props,
    CONFIG_B1.TOTAL_DUPLICATE_SKIPPED_PROPERTY,
    duplicateSkipped
  );

  console.log(JSON.stringify({
    stage: 'B1_DRIVE_SYNC',
    run: runCount,
    scanned,
    appended,
    duplicateSkipped,
    totalScanned,
    totalAppended,
    totalDuplicateSkipped,
    startTokenHash,
    nextTokenHash: tokenHash_(pageToken),
    nextPageTokenSaved: Boolean(pageToken),
    sheetRows: sheet.getLastRow(),
    message: pageToken
      ? 'Scan is still moving through Drive. Continue with startDriveFilesSync.'
      : 'Drive scan reached the end. Run auditFilesSheetDuplicates next.'
  }));
}

function auditFilesSheetDuplicates() {
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const idx = headerIndexes_(headers);
  const duplicateFileIds = groupedDuplicates_(values, row => String(row[idx.file_id] || '').trim());
  const duplicateSignatures = groupedDuplicates_(values, row => {
    const name = String(row[idx.file_name] || '').trim().toLowerCase();
    const parentId = String(row[idx.parent_folder_id] || '').trim();
    const size = String(row[idx.size_bytes] || '').trim();
    if (!name || !parentId) return '';
    return `${name}|${parentId}|${size}`;
  });

  const report = [
    ['duplicate_type', 'key', 'count', 'rows', 'file_ids', 'file_names']
  ];
  appendDuplicateReport_(report, 'same_file_id', duplicateFileIds, values, idx);
  appendDuplicateReport_(report, 'same_name_parent_size', duplicateSignatures, values, idx);

  const reportSheet = getOrCreateSheet_(ss, 'DUPLICATE_AUDIT');
  reportSheet.clearContents();
  reportSheet.getRange(1, 1, report.length, report[0].length).setValues(report);
  reportSheet.autoResizeColumns(1, report[0].length);

  console.log(JSON.stringify({
    stage: 'FILES_DUPLICATE_AUDIT',
    sameFileIdGroups: duplicateFileIds.length,
    sameNameParentSizeGroups: duplicateSignatures.length,
    reportRows: report.length - 1
  }));
}

function auditDriveVsSheetCoverage() {
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const idx = headerIndexes_(headers);
  const sheetIndex = buildSheetFileIndex_(values, idx);
  const driveIndex = scanUniqueDriveFileIndex_();

  const missingFromSheet = [];
  const presentInBoth = [];
  Object.keys(driveIndex.byId).forEach(fileId => {
    if (sheetIndex.byId[fileId]) {
      presentInBoth.push(fileId);
    } else {
      missingFromSheet.push(driveIndex.byId[fileId]);
    }
  });

  const staleInSheet = [];
  Object.keys(sheetIndex.byId).forEach(fileId => {
    if (!driveIndex.byId[fileId]) {
      staleInSheet.push(sheetIndex.byId[fileId]);
    }
  });

  const summary = [
    ['metric', 'value'],
    ['sheet_rows_excluding_header', values.length - 1],
    ['unique_file_ids_in_sheet', Object.keys(sheetIndex.byId).length],
    ['duplicate_file_id_groups_in_sheet', sheetIndex.duplicateGroups.length],
    ['unique_file_ids_seen_in_drive', Object.keys(driveIndex.byId).length],
    ['present_in_both', presentInBoth.length],
    ['missing_from_sheet', missingFromSheet.length],
    ['stale_or_not_seen_in_drive', staleInSheet.length],
    ['drive_pages_scanned', driveIndex.pagesScanned],
    ['drive_items_scanned', driveIndex.itemsScanned]
  ];

  const summarySheet = getOrCreateSheet_(ss, 'DRIVE_SHEET_COVERAGE');
  summarySheet.clearContents();
  summarySheet.getRange(1, 1, summary.length, summary[0].length).setValues(summary);
  summarySheet.autoResizeColumns(1, summary[0].length);

  writeCoverageRows_(ss, 'MISSING_FROM_SHEET', missingFromSheet, [
    'file_id',
    'file_name',
    'mime_type',
    'parent_folder_id',
    'created',
    'modified',
    'owner',
    'file_url'
  ]);
  writeCoverageRows_(ss, 'STALE_IN_SHEET', staleInSheet.slice(0, 2000), [
    'file_id',
    'file_name',
    'row_numbers',
    'enrichment_status',
    'action',
    'project'
  ]);
  writeDuplicateFileIdRows_(ss, sheetIndex.duplicateGroups, values, idx);

  console.log(JSON.stringify({
    stage: 'DRIVE_SHEET_COVERAGE',
    uniqueFileIdsInSheet: Object.keys(sheetIndex.byId).length,
    duplicateFileIdGroupsInSheet: sheetIndex.duplicateGroups.length,
    uniqueFileIdsSeenInDrive: Object.keys(driveIndex.byId).length,
    presentInBoth: presentInBoth.length,
    missingFromSheet: missingFromSheet.length,
    staleOrNotSeenInDrive: staleInSheet.length,
    drivePagesScanned: driveIndex.pagesScanned,
    driveItemsScanned: driveIndex.itemsScanned
  }));
}

function dedupeFilesSheetByFileId() {
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const values = sheet.getDataRange().getValues();
  const headers = values[0];
  const idx = headerIndexes_(headers);
  const sheetIndex = buildSheetFileIndex_(values, idx);
  const duplicateGroups = sheetIndex.duplicateGroups;

  if (duplicateGroups.length === 0) {
    console.log(JSON.stringify({
      stage: 'FILES_DEDUPLICATION',
      duplicateGroups: 0,
      deletedRows: 0,
      message: 'No duplicate file_id rows found.'
    }));
    return;
  }

  const archiveRows = [[
    'deduped_at',
    'file_id',
    'kept_row',
    'deleted_row',
    'reason',
    ...headers
  ]];
  const planRows = [[
    'file_id',
    'kept_row',
    'deleted_rows',
    'duplicate_count',
    'keep_reason'
  ]];
  const rowsToDelete = [];
  const dedupedAt = new Date().toISOString();

  duplicateGroups.forEach(group => {
    const candidates = group.rows.map(rowNumber => ({
      rowNumber,
      row: values[rowNumber - 1],
      score: dedupeKeepScore_(values[rowNumber - 1], idx)
    }));
    candidates.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      return a.rowNumber - b.rowNumber;
    });

    const keep = candidates[0];
    const deleteCandidates = candidates.slice(1);
    const deletedRows = deleteCandidates.map(item => item.rowNumber);
    rowsToDelete.push(...deletedRows);

    planRows.push([
      group.fileId,
      keep.rowNumber,
      deletedRows.join(', '),
      group.rows.length,
      dedupeKeepReason_(keep.row, idx)
    ]);

    deleteCandidates.forEach(item => {
      archiveRows.push([
        dedupedAt,
        group.fileId,
        keep.rowNumber,
        item.rowNumber,
        `duplicate file_id; kept row ${keep.rowNumber}`,
        ...item.row
      ]);
    });
  });

  writeAppendOnlyRows_(ss, 'DEDUPLICATED_ROWS_ARCHIVE', archiveRows);
  writeReplaceRows_(ss, 'DEDUPLICATION_RESULT', planRows);

  Array.from(new Set(rowsToDelete))
    .sort((a, b) => b - a)
    .forEach(rowNumber => sheet.deleteRow(rowNumber));

  console.log(JSON.stringify({
    stage: 'FILES_DEDUPLICATION',
    duplicateGroups: duplicateGroups.length,
    deletedRows: rowsToDelete.length,
    archiveSheet: 'DEDUPLICATED_ROWS_ARCHIVE',
    resultSheet: 'DEDUPLICATION_RESULT',
    remainingSheetRows: sheet.getLastRow()
  }));
}

function findDriveFileForIndexDebug(query) {
  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = headerIndexes_(headers);
  const knownFileIds = loadKnownFileIds_(sheet, idx.file_id);
  const normalizedQuery = String(query || '').trim();
  if (!normalizedQuery) throw new Error('Pass a file name or name fragment.');

  const rows = [[
    'file_id',
    'file_name',
    'mime_type',
    'parent_folder_id',
    'created_iso',
    'modified_iso',
    'owned_by_me',
    'parents',
    'owner',
    'in_files_sheet',
    'file_url'
  ]];
  let pageToken = null;
  let scanned = 0;
  let incompleteSearch = false;

  do {
    const response = Drive.Files.list({
      q: `trashed = false and name contains '${escapeDriveQueryText_(normalizedQuery)}'`,
      corpora: 'user',
      includeItemsFromAllDrives: true,
      supportsAllDrives: true,
      spaces: 'drive',
      pageSize: CONFIG_B1.PAGE_SIZE,
      pageToken: pageToken || undefined,
      orderBy: 'modifiedTime desc',
      fields: driveListFields_()
    });
    incompleteSearch = incompleteSearch || Boolean(response.incompleteSearch);
    const files = response.files || [];
    files.forEach(file => {
      scanned++;
      const row = driveFileCoverageRow_(file);
      rows.push([
        row.file_id,
        row.file_name,
        row.mime_type,
        row.parent_folder_id,
        row.created_iso,
        row.modified_iso,
        row.owned_by_me,
        row.parents,
        row.owner,
        knownFileIds.has(row.file_id) ? 'yes' : 'no',
        row.file_url
      ]);
    });
    pageToken = response.nextPageToken || null;
    if (scanned >= CONFIG_B1.MAX_FILES_PER_RUN) break;
  } while (pageToken);

  writeReplaceRows_(ss, CONFIG_B1.DEBUG_SEARCH_REPORT_SHEET, rows);
  console.log(JSON.stringify({
    stage: 'B1_DRIVE_FILE_DEBUG_SEARCH',
    query: normalizedQuery,
    scanned,
    matches: rows.length - 1,
    incompleteSearch,
    reportSheet: CONFIG_B1.DEBUG_SEARCH_REPORT_SHEET
  }));
}

function syncDriveFileById(fileIdOrUrl) {
  const fileId = extractDriveFileId_(fileIdOrUrl);
  if (!fileId) throw new Error('Pass a Drive file ID or URL.');

  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = headerIndexes_(headers);
  const file = getDriveFileById_(fileId);
  const rowMap = buildSheetFileRowMap_(sheet, idx);

  if (rowMap[file.id]) {
    updateExistingFileMetadata_(sheet, rowMap[file.id], file, idx);
    if (file.trashed) markSheetFileDriveReview_(sheet, idx, rowMap[file.id], 'DRIVE_TRASHED_REVIEW');
    console.log(JSON.stringify({
      stage: 'B1_SYNC_FILE_BY_ID',
      fileId: file.id,
      fileName: file.name || '',
      appended: 0,
      updated: 1,
      trashed: Boolean(file.trashed),
      message: 'File already existed in Files; metadata refreshed.'
    }));
    return;
  }

  const row = makeFilesRow_(file, headers, idx);
  if (file.trashed) {
    row[idx.status] = 'drive_trashed_review';
    row[idx.enrichment_status] = 'DRIVE_TRASHED_REVIEW';
    row[idx.action] = 'REVIEW';
  }
  sheet.getRange(sheet.getLastRow() + 1, 1, 1, headers.length).setValues([row]);
  console.log(JSON.stringify({
    stage: 'B1_SYNC_FILE_BY_ID',
    fileId: file.id,
    fileName: file.name || '',
    appended: 1,
    updated: 0,
    trashed: Boolean(file.trashed)
  }));
}

function initDriveChangesToken() {
  const response = Drive.Changes.getStartPageToken({
    supportsAllDrives: true,
    fields: 'startPageToken'
  });
  const token = response.startPageToken;
  if (!token) throw new Error('Drive Changes did not return startPageToken.');
  PropertiesService.getScriptProperties().setProperty(CONFIG_B1.CHANGES_TOKEN_PROPERTY, token);
  console.log(JSON.stringify({
    stage: 'B1_CHANGES_TOKEN_INIT',
    tokenHash: tokenHash_(token),
    message: 'Changes token initialized. Create or modify a file, then run syncDriveChangesToSheet.'
  }));
  return token;
}

function syncDriveChangesToSheet() {
  const startTime = Date.now();
  const props = PropertiesService.getScriptProperties();
  let pageToken = props.getProperty(CONFIG_B1.CHANGES_TOKEN_PROPERTY);
  if (!pageToken) {
    const token = initDriveChangesToken();
    console.log(JSON.stringify({
      stage: 'B1_DRIVE_CHANGES_SYNC',
      initialized: true,
      tokenHash: tokenHash_(token),
      message: 'Token was missing, so it was initialized. Run again after new Drive changes.'
    }));
    return;
  }

  const ss = SpreadsheetApp.openById(CONFIG_B1.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B1.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B1.SHEET_NAME}`);

  ensureFilesHeaders_(sheet);
  const headers = sheet.getRange(1, 1, 1, sheet.getLastColumn()).getValues()[0];
  const idx = headerIndexes_(headers);
  const rowMap = buildSheetFileRowMap_(sheet, idx);
  const rowsToAppend = [];
  let changesScanned = 0;
  let appended = 0;
  let updated = 0;
  let markedForReview = 0;
  let nextPageToken = null;
  let newStartPageToken = null;
  let tokenToSave = pageToken;

  do {
    const currentPageToken = pageToken;
    const response = Drive.Changes.list(currentPageToken, {
      includeItemsFromAllDrives: true,
      supportsAllDrives: true,
      spaces: 'drive',
      pageSize: CONFIG_B1.PAGE_SIZE,
      fields: 'nextPageToken,newStartPageToken,changes(fileId,removed,time,type,changeType,file(id,name,mimeType,parents,createdTime,modifiedTime,size,webViewLink,owners(emailAddress),ownedByMe,trashed,driveId))'
    });
    const changes = response.changes || [];
    let pageFullyProcessed = true;

    for (const change of changes) {
      if (Date.now() - startTime > CONFIG_B1.MAX_RUNTIME_MS) {
        pageFullyProcessed = false;
        break;
      }
      changesScanned++;
      const fileId = change.fileId || (change.file && change.file.id);
      if (!fileId) continue;

      const existingRowNumber = rowMap[fileId];
      if (change.removed || !change.file || change.file.trashed) {
        if (existingRowNumber) {
          markSheetFileDriveReview_(
            sheet,
            idx,
            existingRowNumber,
            change.removed ? 'DRIVE_REMOVED_REVIEW' : 'DRIVE_TRASHED_REVIEW'
          );
          markedForReview++;
        }
        continue;
      }

      if (existingRowNumber) {
        updateExistingFileMetadata_(sheet, existingRowNumber, change.file, idx);
        updated++;
      } else {
        rowsToAppend.push(makeFilesRow_(change.file, headers, idx));
        rowMap[fileId] = sheet.getLastRow() + rowsToAppend.length;
        appended++;
      }

      if (rowsToAppend.length >= CONFIG_B1.MAX_APPEND_PER_RUN) {
        pageFullyProcessed = false;
        break;
      }
    }

    if (!pageFullyProcessed) {
      tokenToSave = currentPageToken;
      nextPageToken = currentPageToken;
      break;
    }

    nextPageToken = response.nextPageToken || null;
    newStartPageToken = response.newStartPageToken || newStartPageToken;
    tokenToSave = nextPageToken || newStartPageToken || currentPageToken;
    pageToken = nextPageToken;
  } while (nextPageToken && Date.now() - startTime < CONFIG_B1.MAX_RUNTIME_MS);

  if (rowsToAppend.length > 0) {
    sheet.getRange(sheet.getLastRow() + 1, 1, rowsToAppend.length, headers.length).setValues(rowsToAppend);
  }

  if (tokenToSave) props.setProperty(CONFIG_B1.CHANGES_TOKEN_PROPERTY, tokenToSave);
  const runCount = incrementNumberProperty_(props, CONFIG_B1.CHANGES_RUN_COUNT_PROPERTY, 1);

  console.log(JSON.stringify({
    stage: 'B1_DRIVE_CHANGES_SYNC',
    run: runCount,
    changesScanned,
    appended,
    updated,
    markedForReview,
    nextPageTokenSaved: Boolean(nextPageToken),
    changesTokenHash: tokenHash_(tokenToSave),
    sheetRows: sheet.getLastRow()
  }));
}

function listDriveFilesPage_(pageToken) {
  return Drive.Files.list({
    q: 'trashed = false',
    corpora: 'allDrives',
    includeItemsFromAllDrives: true,
    supportsAllDrives: true,
    pageSize: CONFIG_B1.PAGE_SIZE,
    pageToken: pageToken || undefined,
    fields: 'nextPageToken, files(id,name,mimeType,parents,createdTime,modifiedTime,size,webViewLink,owners(emailAddress),ownedByMe,trashed,driveId)'
  });
}

function listRecentDriveFilesPage_(pageToken, cutoffIso) {
  return listRecentMyDriveFilesPage_(pageToken, cutoffIso);
}

function listRecentMyDriveFilesPage_(pageToken, cutoffIso) {
  return Drive.Files.list({
    q: `trashed = false and (createdTime >= '${cutoffIso}' or modifiedTime >= '${cutoffIso}')`,
    corpora: 'user',
    includeItemsFromAllDrives: true,
    supportsAllDrives: true,
    spaces: 'drive',
    pageSize: CONFIG_B1.PAGE_SIZE,
    pageToken: pageToken || undefined,
    orderBy: 'modifiedTime desc',
    fields: driveListFields_()
  });
}

function driveListFields_() {
  return 'nextPageToken,incompleteSearch,files(id,name,mimeType,parents,createdTime,modifiedTime,size,webViewLink,owners(emailAddress),ownedByMe,trashed,driveId)';
}

function getDriveFileById_(fileId) {
  return Drive.Files.get(fileId, {
    supportsAllDrives: true,
    fields: 'id,name,mimeType,parents,createdTime,modifiedTime,size,webViewLink,owners(emailAddress),ownedByMe,trashed,driveId'
  });
}

function buildSheetFileRowMap_(sheet, idx) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return {};

  const values = sheet.getRange(2, idx.file_id + 1, lastRow - 1, 1).getValues();
  const byId = {};
  values.forEach((row, offset) => {
    const fileId = String(row[0] || '').trim();
    if (fileId && !byId[fileId]) byId[fileId] = offset + 2;
  });
  return byId;
}

function buildSheetFileIndex_(values, idx) {
  const byId = {};
  const rowsById = {};
  for (let i = 1; i < values.length; i++) {
    const row = values[i];
    const fileId = String(row[idx.file_id] || '').trim();
    if (!fileId) continue;
    if (!rowsById[fileId]) rowsById[fileId] = [];
    rowsById[fileId].push(i + 1);
    if (!byId[fileId]) {
      byId[fileId] = {
        file_id: fileId,
        file_name: row[idx.file_name] || '',
        row_numbers: rowsById[fileId],
        enrichment_status: row[idx.enrichment_status] || '',
        action: row[idx.action] || '',
        project: row[idx.project] || ''
      };
    } else {
      byId[fileId].row_numbers = rowsById[fileId];
    }
  }

  const duplicateGroups = Object.keys(rowsById)
    .filter(fileId => rowsById[fileId].length > 1)
    .map(fileId => ({fileId, rows: rowsById[fileId]}));

  return {byId, rowsById, duplicateGroups};
}

function scanUniqueDriveFileIndex_() {
  const byId = {};
  let pageToken = null;
  let pagesScanned = 0;
  let itemsScanned = 0;

  do {
    const response = listDriveFilesPage_(pageToken);
    pagesScanned++;
    const files = response.files || [];
    files.forEach(file => {
      itemsScanned++;
      if (!file.id || byId[file.id]) return;
      byId[file.id] = driveFileCoverageRow_(file);
    });
    pageToken = response.nextPageToken || null;
  } while (pageToken);

  return {byId, pagesScanned, itemsScanned};
}

function driveFileCoverageRow_(file) {
  const parentId = file.parents && file.parents.length ? file.parents[0] : 'root';
  return {
    file_id: file.id || '',
    file_name: file.name || '',
    mime_type: file.mimeType || '',
    parent_folder_id: parentId,
    created: formatSheetDate_(file.createdTime),
    modified: formatSheetDate_(file.modifiedTime),
    created_iso: file.createdTime || '',
    modified_iso: file.modifiedTime || '',
    owned_by_me: file.ownedByMe === undefined ? '' : Boolean(file.ownedByMe),
    parents: file.parents && file.parents.length ? file.parents.join(',') : '',
    owner: ownerEmail_(file),
    file_url: file.webViewLink || driveUrl_(file)
  };
}

function writeCoverageRows_(ss, sheetName, rows, columns) {
  const sheet = getOrCreateSheet_(ss, sheetName);
  sheet.clearContents();
  const values = [columns].concat(rows.map(row => columns.map(column => {
    const value = row[column];
    return Array.isArray(value) ? value.join(', ') : value;
  })));
  sheet.getRange(1, 1, values.length, columns.length).setValues(values);
  sheet.autoResizeColumns(1, columns.length);
}

function writeDuplicateFileIdRows_(ss, duplicateGroups, values, idx) {
  const sheet = getOrCreateSheet_(ss, 'DUPLICATE_FILE_IDS');
  sheet.clearContents();
  const output = [['file_id', 'count', 'rows', 'file_names']];
  duplicateGroups.forEach(group => {
    const names = group.rows.map(rowNumber => values[rowNumber - 1][idx.file_name]).filter(Boolean);
    output.push([
      group.fileId,
      group.rows.length,
      group.rows.join(', '),
      Array.from(new Set(names)).join(' | ')
    ]);
  });
  sheet.getRange(1, 1, output.length, output[0].length).setValues(output);
  sheet.autoResizeColumns(1, output[0].length);
}

function dedupeKeepScore_(row, idx) {
  let score = 0;
  const enrichmentStatus = String(row[idx.enrichment_status] || '').trim();
  const action = String(row[idx.action] || '').trim();
  const summary = String(row[idx.summary_50w] || '').trim();
  const project = String(row[idx.project] || '').trim();
  const valueScore = Number(row[idx.value_score] || 0);

  if (enrichmentStatus === 'AI_DONE') score += 1000;
  if (enrichmentStatus === 'NEEDS_AI') score += 200;
  if (enrichmentStatus === 'RULE_DONE') score += 100;
  if (action === 'KEEP') score += 500;
  if (action === 'REVIEW') score += 200;
  if (action === 'DELETE') score += 50;
  if (summary) score += 150;
  if (project && project !== 'UNCATEGORIZED') score += 100;
  if (valueScore) score += valueScore * 10;
  return score;
}

function dedupeKeepReason_(row, idx) {
  const parts = [];
  const enrichmentStatus = String(row[idx.enrichment_status] || '').trim();
  const action = String(row[idx.action] || '').trim();
  const summary = String(row[idx.summary_50w] || '').trim();
  const project = String(row[idx.project] || '').trim();
  if (enrichmentStatus) parts.push(`enrichment_status=${enrichmentStatus}`);
  if (action) parts.push(`action=${action}`);
  if (project) parts.push(`project=${project}`);
  if (summary) parts.push('has_summary');
  return parts.join('; ') || 'first row fallback';
}

function writeAppendOnlyRows_(ss, sheetName, rows) {
  if (!rows || rows.length <= 1) return;
  const sheet = getOrCreateSheet_(ss, sheetName);
  const startRow = sheet.getLastRow() + 1;
  const output = sheet.getLastRow() === 0 ? rows : rows.slice(1);
  sheet.getRange(startRow, 1, output.length, output[0].length).setValues(output);
  sheet.autoResizeColumns(1, output[0].length);
}

function writeReplaceRows_(ss, sheetName, rows) {
  const sheet = getOrCreateSheet_(ss, sheetName);
  sheet.clearContents();
  sheet.getRange(1, 1, rows.length, rows[0].length).setValues(rows);
  sheet.autoResizeColumns(1, rows[0].length);
}

function ensureFilesHeaders_(sheet) {
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, FILES_HEADERS.length).setValues([FILES_HEADERS]);
    return;
  }

  const currentHeaders = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), FILES_HEADERS.length)).getValues()[0];
  const missing = FILES_HEADERS.filter(header => currentHeaders.indexOf(header) === -1);
  if (missing.length > 0) {
    throw new Error(`Files sheet is missing required headers: ${missing.join(', ')}`);
  }
}

function headerIndexes_(headers) {
  const idx = {};
  FILES_HEADERS.forEach(header => {
    idx[header] = headers.indexOf(header);
    if (idx[header] === -1) throw new Error(`Missing header: ${header}`);
  });
  return idx;
}

function loadKnownFileIds_(sheet, fileIdIndex) {
  const lastRow = sheet.getLastRow();
  if (lastRow < 2) return new Set();

  const values = sheet.getRange(2, fileIdIndex + 1, lastRow - 1, 1).getValues();
  return new Set(values.map(row => String(row[0] || '').trim()).filter(Boolean));
}

function groupedDuplicates_(values, keyFn) {
  const groups = {};
  for (let i = 1; i < values.length; i++) {
    const key = keyFn(values[i]);
    if (!key) continue;
    if (!groups[key]) groups[key] = [];
    groups[key].push(i + 1);
  }
  return Object.keys(groups)
    .filter(key => groups[key].length > 1)
    .map(key => ({key, rows: groups[key]}));
}

function appendDuplicateReport_(report, duplicateType, groups, values, idx) {
  groups.forEach(group => {
    const fileIds = group.rows.map(rowNumber => values[rowNumber - 1][idx.file_id]).filter(Boolean);
    const fileNames = group.rows.map(rowNumber => values[rowNumber - 1][idx.file_name]).filter(Boolean);
    report.push([
      duplicateType,
      group.key,
      group.rows.length,
      group.rows.join(', '),
      Array.from(new Set(fileIds)).join(', '),
      Array.from(new Set(fileNames)).join(' | ')
    ]);
  });
}

function getOrCreateSheet_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function makeFilesRow_(file, headers, idx) {
  const row = new Array(headers.length).fill('');
  const parentId = file.parents && file.parents.length ? file.parents[0] : 'root';

  row[idx.file_name] = file.name || '';
  row[idx.file_id] = file.id || '';
  row[idx.file_url] = file.webViewLink || driveUrl_(file);
  row[idx.parent_folder_name] = parentId === 'root' ? '_ROOT_' : '';
  row[idx.parent_folder_id] = parentId;
  row[idx.mime_type] = file.mimeType || '';
  row[idx.created] = formatSheetDate_(file.createdTime);
  row[idx.modified] = formatSheetDate_(file.modifiedTime);
  row[idx.size_bytes] = file.size || '';
  row[idx.owner] = ownerEmail_(file);
  row[idx.project] = 'UNCATEGORIZED';
  row[idx.type] = initialFileType_(file);
  row[idx.value_score] = 1;
  row[idx.action] = 'REVIEW';
  row[idx.enrichment_status] = initialEnrichmentStatus_(file);

  return row;
}

function initialFileType_(file) {
  const mime = String(file.mimeType || '');
  const name = String(file.name || '').toLowerCase();
  if (mime === 'application/vnd.google-apps.document') return 'document';
  if (mime === 'application/vnd.google-apps.spreadsheet') return 'spreadsheet';
  if (mime === 'application/vnd.google-apps.presentation') return 'presentation';
  if (mime === 'application/pdf') return 'pdf';
  if (mime.indexOf('image/') === 0) return 'image';
  if (mime.indexOf('video/') === 0 || mime.indexOf('audio/') === 0) return 'media';
  if (mime.indexOf('text/') === 0 || name.endsWith('.md') || name.endsWith('.json')) return 'text';
  return 'file';
}

function initialEnrichmentStatus_(file) {
  const mime = String(file.mimeType || '');
  const name = String(file.name || '').toLowerCase();
  if (mime === 'application/vnd.google-apps.document') return 'NEEDS_AI';
  if (mime === 'application/vnd.google-apps.spreadsheet') return 'NEEDS_AI';
  if (mime.indexOf('text/') === 0) return 'NEEDS_AI';
  if (name.endsWith('.md') || name.endsWith('.json') || name.endsWith('.txt') || name.endsWith('.csv')) return 'NEEDS_AI';
  if (mime.indexOf('image/') === 0) return 'NEEDS_IMAGE_REVIEW';
  if (mime === 'application/pdf') return 'NEEDS_PDF_REVIEW';
  if (mime === 'application/vnd.google-apps.presentation') return 'NEEDS_PRESENTATION_REVIEW';
  if (mime.indexOf('video/') === 0 || mime.indexOf('audio/') === 0) return 'NEEDS_MEDIA_REVIEW';
  return 'NEEDS_FILE_REVIEW';
}

function updateExistingFileMetadata_(sheet, rowNumber, file, idx) {
  const row = sheet.getRange(rowNumber, 1, 1, sheet.getLastColumn()).getValues()[0];
  const parentId = file.parents && file.parents.length ? file.parents[0] : 'root';

  row[idx.file_name] = file.name || row[idx.file_name] || '';
  row[idx.file_url] = file.webViewLink || driveUrl_(file);
  row[idx.parent_folder_name] = parentId === 'root' ? '_ROOT_' : row[idx.parent_folder_name] || '';
  row[idx.parent_folder_id] = parentId;
  row[idx.mime_type] = file.mimeType || row[idx.mime_type] || '';
  row[idx.created] = formatSheetDate_(file.createdTime) || row[idx.created] || '';
  row[idx.modified] = formatSheetDate_(file.modifiedTime) || row[idx.modified] || '';
  row[idx.size_bytes] = file.size || row[idx.size_bytes] || '';
  row[idx.owner] = ownerEmail_(file) || row[idx.owner] || '';

  sheet.getRange(rowNumber, 1, 1, row.length).setValues([row]);
}

function markSheetFileDriveReview_(sheet, idx, rowNumber, reason) {
  if (idx.status !== -1) sheet.getRange(rowNumber, idx.status + 1).setValue(String(reason || '').toLowerCase());
  if (idx.enrichment_status !== -1) sheet.getRange(rowNumber, idx.enrichment_status + 1).setValue(reason);
  if (idx.action !== -1) sheet.getRange(rowNumber, idx.action + 1).setValue('REVIEW');
}

function ownerEmail_(file) {
  if (!file.owners || !file.owners.length) return '';
  return file.owners.map(owner => owner.emailAddress).filter(Boolean).join(', ');
}

function driveUrl_(file) {
  if (!file.id) return '';
  if (file.mimeType === 'application/vnd.google-apps.document') return `https://docs.google.com/document/d/${file.id}/edit`;
  if (file.mimeType === 'application/vnd.google-apps.spreadsheet') return `https://docs.google.com/spreadsheets/d/${file.id}/edit`;
  if (file.mimeType === 'application/vnd.google-apps.presentation') return `https://docs.google.com/presentation/d/${file.id}/edit`;
  return `https://drive.google.com/file/d/${file.id}/view`;
}

function formatSheetDate_(isoValue) {
  if (!isoValue) return '';
  return Utilities.formatDate(new Date(isoValue), Session.getScriptTimeZone(), 'dd.MM.yyyy');
}

function extractDriveFileId_(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  const byPath = text.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (byPath) return byPath[1];
  const byIdParam = text.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (byIdParam) return byIdParam[1];
  const raw = text.match(/^[a-zA-Z0-9_-]{10,}$/);
  return raw ? raw[0] : '';
}

function escapeDriveQueryText_(value) {
  return String(value || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

function cleanupDriveSyncTriggers() {
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === CONFIG_B1.TRIGGER_HANDLER) {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}

function resetDriveFilesSyncState_() {
  const props = PropertiesService.getScriptProperties();
  [
    CONFIG_B1.PAGE_TOKEN_PROPERTY,
    CONFIG_B1.RUN_COUNT_PROPERTY,
    CONFIG_B1.TOTAL_SCANNED_PROPERTY,
    CONFIG_B1.TOTAL_APPENDED_PROPERTY,
    CONFIG_B1.TOTAL_DUPLICATE_SKIPPED_PROPERTY,
    CONFIG_B1.LAST_TOKEN_HASH_PROPERTY
  ].forEach(name => props.deleteProperty(name));
}

function incrementNumberProperty_(props, name, amount) {
  const nextValue = Number(props.getProperty(name) || 0) + amount;
  props.setProperty(name, String(nextValue));
  return nextValue;
}

function tokenHash_(token) {
  if (!token) return '';
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, token);
  return digest.map(byte => {
    const value = byte < 0 ? byte + 256 : byte;
    return value.toString(16).padStart(2, '0');
  }).join('').substring(0, 12);
}
