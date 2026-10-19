'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');
const { parse: parseFlatted } = require('/usr/local/lib/node_modules/n8n/node_modules/flatted');

const name = path.basename(process.argv[2] || '');
if (!name.endsWith('.json') || !name.startsWith('flujo-real-')) {
  console.error('Pass one flujo-real-*.json artifact name; no database data was exported.');
  process.exit(2);
}
const artifactPath = path.join('/workflows/evidencias/real', name);
const artifact = JSON.parse(fs.readFileSync(artifactPath, 'utf8'));
artifact.metadata = {
  note: 'Metadata selectiva extraída de ejecuciones n8n: cada request_id, modelo, estado HTTP, finish_reason y usage está asociado a su caso en results[].n8n_execution.provider_calls; los totales agregados están en llm_usage_totals. No se exportan headers ni credenciales.',
};
const workflowPath = '/workflows/solicitudes.json';
const workflowBytes = fs.readFileSync(workflowPath);
const workflow = JSON.parse(workflowBytes.toString('utf8'));
const systemNode = workflow.nodes.find(n => n.name === 'DeepSeek extracción intento 1');
const expression = systemNode?.parameters?.jsonBody || '';
const promptMatch = expression.match(/role:'system',content:("(?:\\.|[^"\\])*")/s);
if (!promptMatch) {
  console.error('Could not isolate the system prompt literal; no database data was exported.');
  process.exit(2);
}
const inlinePrompt = JSON.parse(promptMatch[1]);
const hash = value => crypto.createHash('sha256').update(value).digest('hex');

const expected = new Map(artifact.results.map(r => [r.request.idempotency_key, r.case]));
const db = new DatabaseSync('/home/node/.n8n/database.sqlite', { readOnly: true });
const rows = db.prepare(`
  SELECT e.id, e.status, e.startedAt, d.data
  FROM execution_entity AS e
  JOIN execution_data AS d ON d.executionId=e.id
  WHERE e.workflowId=?
  ORDER BY e.id DESC
  LIMIT 50
`).all(workflow.id);
const executions = new Map();
const providerNodeNames = ['DeepSeek extracci\u00f3n intento 1', 'DeepSeek correcci\u00f3n intento 2'];
for (const row of rows) {
  let data;
  try { data = parseFlatted(row.data); } catch { continue; }
  const runData = data?.resultData?.runData ?? data?.executionData?.resultData?.runData ?? data?.data?.resultData?.runData;
  const triggerRun = runData?.['Webhook solicitud']?.[0];
  const triggerItem = triggerRun?.data?.main?.[0]?.[0]?.json;
  const key = triggerItem?.headers?.['idempotency-key'] ?? triggerItem?.headers?.['Idempotency-Key'];
  if (!expected.has(key)) continue;

  const providerCalls = [];
  for (const nodeName of providerNodeNames) {
    for (const run of runData?.[nodeName] ?? []) {
      const items = run?.data?.main?.[0] ?? [];
      for (const item of items) {
        const output = item?.json ?? {};
        const body = output.body ?? {};
        providerCalls.push({
          node: nodeName,
          http_status: output.statusCode ?? null,
          request_id: body.id ?? null,
          model: body.model ?? null,
          usage: body.usage ?? null,
          finish_reason: body.choices?.[0]?.finish_reason ?? null,
        });
      }
    }
  }
  executions.set(key, {
    case: expected.get(key),
    execution_id: row.id,
    execution_status: row.status,
    started_at: row.startedAt,
    provider_calls: providerCalls,
  });
}
db.close();

let promptTokens=0, completionTokens=0, totalTokens=0, cachedTokens=0, callCount=0;
for (const result of artifact.results) {
  const execution = executions.get(result.request.idempotency_key) ?? null;
  result.n8n_execution = execution;
  const calls = execution?.provider_calls ?? [];
  for (const call of calls) {
    callCount++;
    const usage = call.usage ?? {};
    promptTokens += usage.prompt_tokens ?? 0;
    completionTokens += usage.completion_tokens ?? 0;
    totalTokens += usage.total_tokens ?? 0;
    cachedTokens += usage.prompt_tokens_details?.cached_tokens ?? 0;
  }
}
artifact.workflow_id = workflow.id;
artifact.workflow_sha256 = hash(workflowBytes);
artifact.inline_system_prompt_sha256 = hash(inlinePrompt);
artifact.metadata_extracted_at_utc = new Date().toISOString();
artifact.llm_usage_totals = {
  calls: callCount,
  prompt_tokens: promptTokens,
  completion_tokens: completionTokens,
  total_tokens: totalTokens,
  cached_prompt_tokens: cachedTokens,
  uncached_prompt_tokens: Math.max(0, promptTokens-cachedTokens),
};
process.stdout.write(JSON.stringify(artifact, null, 2) + '\n');
