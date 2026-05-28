/**
 * CAPITAL INDEX 2026 - Stage B2 Sheet AI tagging via Cloud Run.
 *
 * This Apps Script file intentionally contains no Gemini/API key.
 * It sends row data to a Cloud Run endpoint. Cloud Run reads AI credentials
 * from Google Secret Manager.
 */

const CONFIG_B2_CLOUD = {
  SS_ID: '1tJ72mlke07KGEEVUYWxcKpGRdo6nx8xF7_bHVDv7dpM',
  SHEET_NAME: 'Files',
  CLASSIFIER_URL: 'https://capital-entity-extractor-745677061768.europe-west1.run.app/classify-sheet-row',
  MAX_RUNTIME_MS: 240000,
  MAX_ROWS_PER_RUN: 80,
  TRIGGER_HANDLER: 'processAiQueueViaCloudRun'
};

function startAiTaggingViaCloudRun() {
  cleanupAiCloudTriggers();
  processAiQueueViaCloudRun();
}

function processAiQueueViaCloudRun() {
  const startTime = Date.now();
  const ss = SpreadsheetApp.openById(CONFIG_B2_CLOUD.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B2_CLOUD.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B2_CLOUD.SHEET_NAME}`);

  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const idx = b2HeaderIndexes_(headers);
  let processed = 0;
  let errors = 0;
  let authFailures = 0;

  for (let i = 1; i < data.length; i++) {
    if (Date.now() - startTime > CONFIG_B2_CLOUD.MAX_RUNTIME_MS) break;
    if (processed >= CONFIG_B2_CLOUD.MAX_ROWS_PER_RUN) break;
    if (data[i][idx.status] !== 'NEEDS_AI' && data[i][idx.status] !== 'AI_RATE_LIMITED') continue;

    try {
      const content = extractFileTextForCloudRun_(data[i][idx.file_id], data[i][idx.mime], data[i][idx.file_name]);
      const result = classifyRowViaCloudRun_({
        file_id: data[i][idx.file_id],
        file_name: data[i][idx.file_name],
        parent_folder_name: data[i][idx.parent],
        mime_type: data[i][idx.mime],
        content
      });

      const ai = result.classification || result;
      const rowValues = data[i];
      rowValues[idx.project] = ai.project || 'UNCATEGORIZED';
      rowValues[idx.sub] = ai.sub_topic || '';
      rowValues[idx.type] = ai.type || '';
      rowValues[idx.summary] = ai.summary_50w || '';
      rowValues[idx.linked] = ai.linked_projects || '';
      rowValues[idx.value] = ai.value_score || 1;
      rowValues[idx.action] = ai.action || 'REVIEW';
      rowValues[idx.status] = 'AI_DONE';
      sheet.getRange(i + 1, 1, 1, headers.length).setValues([rowValues]);
      processed++;
    } catch (e) {
      errors++;
      const message = String(e.message || '');
      if (isCloudAuthError_(message)) {
        authFailures++;
        console.error(`Cloud AI auth error row ${i + 1}; stopped queue: ${message}`);
        sheet.getRange(i + 1, idx.status + 1).setValue('NEEDS_AI');
        break;
      }
      if (isTransientCloudAiError_(message)) {
        console.warn(`Cloud AI transient error row ${i + 1}; will retry later: ${message}`);
        sheet.getRange(i + 1, idx.status + 1).setValue('AI_RATE_LIMITED');
        continue;
      }
      console.error(`Cloud AI error row ${i + 1}: ${message}`);
      sheet.getRange(i + 1, idx.status + 1).setValue('AI_ERROR');
    }
  }

  const remaining = countRemainingAiRows_(sheet, idx.status);
  cleanupAiCloudTriggers();
  if (remaining > 0 && authFailures === 0) {
    ScriptApp.newTrigger(CONFIG_B2_CLOUD.TRIGGER_HANDLER).timeBased().after(60000).create();
  }

  console.log(JSON.stringify({
    stage: 'B2_CLOUD_RUN_AI_TAGGING',
    processed,
    errors,
    authFailures,
    remaining,
    nextTriggerCreated: remaining > 0 && authFailures === 0
  }));
}

function restoreAiErrorsToNeedsAi() {
  const ss = SpreadsheetApp.openById(CONFIG_B2_CLOUD.SS_ID);
  const sheet = ss.getSheetByName(CONFIG_B2_CLOUD.SHEET_NAME);
  if (!sheet) throw new Error(`Sheet not found: ${CONFIG_B2_CLOUD.SHEET_NAME}`);

  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const idx = b2HeaderIndexes_(headers);
  let restored = 0;

  for (let i = 1; i < data.length; i++) {
    const status = data[i][idx.status];
    const summary = String(data[i][idx.summary] || '').trim();
    if (status === 'AI_ERROR' && !summary) {
      sheet.getRange(i + 1, idx.status + 1).setValue('NEEDS_AI');
      restored++;
    }
  }

  cleanupAiCloudTriggers();
  console.log(JSON.stringify({
    stage: 'B2_RESTORE_AI_ERRORS',
    restored,
    message: 'Run startAiTaggingViaCloudRun after Cloud Run auth is fixed.'
  }));
}

function classifyRowViaCloudRun_(row) {
  const response = UrlFetchApp.fetch(CONFIG_B2_CLOUD.CLASSIFIER_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      Authorization: `Bearer ${getCloudRunBearerToken_()}`
    },
    payload: JSON.stringify({row}),
    muteHttpExceptions: true
  });

  const code = response.getResponseCode();
  const body = response.getContentText();
  if (code < 200 || code >= 300) {
    throw new Error(`Cloud Run classifier failed ${code}: ${body}`);
  }
  return JSON.parse(body);
}

function getCloudRunBearerToken_() {
  try {
    const identityToken = ScriptApp.getIdentityToken();
    if (identityToken) return identityToken;
  } catch (e) {
    console.warn(`Identity token unavailable; falling back to OAuth token: ${e.message}`);
  }
  return ScriptApp.getOAuthToken();
}

function isCloudAuthError_(message) {
  return message.indexOf('failed 401') !== -1 ||
    message.indexOf('failed 403') !== -1 ||
    message.indexOf('Unauthorized') !== -1 ||
    message.indexOf('Forbidden') !== -1;
}

function isTransientCloudAiError_(message) {
  const normalized = String(message || '').toLowerCase();
  return normalized.indexOf('failed 429') !== -1 ||
    normalized.indexOf('failed 500') !== -1 ||
    normalized.indexOf('failed 502') !== -1 ||
    normalized.indexOf('failed 503') !== -1 ||
    normalized.indexOf('failed 504') !== -1 ||
    normalized.indexOf('timed out') !== -1 ||
    normalized.indexOf('timeout') !== -1 ||
    normalized.indexOf('connectionpool') !== -1 ||
    normalized.indexOf('rate') !== -1 ||
    normalized.indexOf('quota') !== -1;
}

function extractFileTextForCloudRun_(id, mime, fileName) {
  try {
    if (mime === 'application/vnd.google-apps.document') {
      return DocumentApp.openById(id).getBody().getText().substring(0, 2500);
    }
    if (mime === 'application/vnd.google-apps.spreadsheet') {
      return SpreadsheetApp.openById(id)
        .getSheets()[0]
        .getDataRange()
        .getValues()
        .slice(0, 30)
        .map(row => row.join(' '))
        .join('\n')
        .substring(0, 2500);
    }
    if (isPlainTextLikeFile_(mime, fileName)) {
      return DriveApp.getFileById(id).getBlob().getDataAsString().substring(0, 2500);
    }
    return 'Binary/media file or unsupported format.';
  } catch (e) {
    return 'Content unavailable to Apps Script.';
  }
}

function isPlainTextLikeFile_(mime, fileName) {
  const normalizedMime = String(mime || '').toLowerCase();
  const normalizedName = String(fileName || '').toLowerCase();
  if (normalizedMime.indexOf('text/') === 0) return true;
  return normalizedName.endsWith('.md') ||
    normalizedName.endsWith('.txt') ||
    normalizedName.endsWith('.json') ||
    normalizedName.endsWith('.csv');
}

function b2HeaderIndexes_(headers) {
  const idx = {
    file_id: headers.indexOf('file_id'),
    file_name: headers.indexOf('file_name'),
    parent: headers.indexOf('parent_folder_name'),
    mime: headers.indexOf('mime_type'),
    project: headers.indexOf('project'),
    sub: headers.indexOf('sub_topic'),
    type: headers.indexOf('type'),
    summary: headers.indexOf('summary_50w'),
    linked: headers.indexOf('linked_projects'),
    value: headers.indexOf('value_score'),
    action: headers.indexOf('action'),
    status: headers.indexOf('enrichment_status')
  };
  Object.keys(idx).forEach(key => {
    if (idx[key] === -1) throw new Error(`Missing Files header: ${key}`);
  });
  return idx;
}

function countRemainingAiRows_(sheet, statusIndex) {
  const values = sheet.getRange(2, statusIndex + 1, Math.max(sheet.getLastRow() - 1, 1), 1).getValues();
  return values.filter(row => row[0] === 'NEEDS_AI' || row[0] === 'AI_RATE_LIMITED').length;
}

function cleanupAiCloudTriggers() {
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === CONFIG_B2_CLOUD.TRIGGER_HANDLER) {
      ScriptApp.deleteTrigger(trigger);
    }
  });
}
