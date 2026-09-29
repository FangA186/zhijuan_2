export function freshRequest(record) {
  return { id:record.request_id, metadata:record, raw:'', content:'', reasoning:'', tools:new Map(), frames:0, done:false };
}
export function applyRecord(request, record) {
  if (record.kind === 'request') request.metadata = record;
  if (record.kind === 'response') request.response = record;
  if (record.kind === 'capture_stopped') request.notice = record.reason;
  if (record.kind === 'hermes_output') {
    request.metadata = {...request.metadata, source:'hermes-adapter'};
    request.raw += (typeof record.raw === 'string' ? record.raw : JSON.stringify(record, null, 2));
    request.frames++;
    try {
      const data = typeof record.raw === 'string' ? JSON.parse(record.raw) : record;
      request.usage = data.usage || request.usage;
      if (data.hermes_status) request.finishReason = data.hermes_status;
      if (data.output) {
        try { const out=JSON.parse(data.output); request.content += JSON.stringify(out, null, 2); } catch { request.content += data.output; }
      }
      request.done = true;
    } catch { /* ignore parse errors */ }
    return request;
  }
  if (typeof record.raw !== 'string') return request;
  request.raw += record.raw;
  request.frames++;
  const messages = record.kind === 'sse' ? record.raw.split(/\r?\n/).filter(line=>line.startsWith('data:')).map(line=>line.slice(5).trim()) : [record.raw];
  for (const text of messages) {
    if (text === '[DONE]') { request.done=true; continue; }
    let chunk;
    try { chunk=JSON.parse(text); } catch { continue; }
    if (record.kind === 'body') request.done = true;
    request.usage = chunk.usage || request.usage;
    request.error = chunk.error || request.error;
    for (const choice of chunk.choices || []) {
      const delta = choice.delta || choice.message || {};
      request.content += delta.content || '';
      request.reasoning += delta.reasoning_content || '';
      if (choice.finish_reason) request.finishReason = choice.finish_reason;
      for (const [position,call] of (delta.tool_calls || []).entries()) {
        const key = `${choice.index || 0}:${call.index ?? position}`;
        const tool = request.tools.get(key) || { id:'',name:'',arguments:'' };
        tool.id += call.id || '';
        tool.name += call.function?.name || '';
        tool.arguments += call.function?.arguments || '';
        request.tools.set(key,tool);
      }
    }
  }
  return request;
}

export function freshSession() {
  return { requests:new Map(), raw:[], frames:0, version:0 };
}
export function applySessionRecord(session, record) {
  if (!session.requests.has(record.request_id)) session.requests.set(record.request_id,freshRequest(record));
  applyRecord(session.requests.get(record.request_id),record);
  if (typeof record.raw === 'string') { session.raw.push(record.raw); session.frames++; }
  session.version++;
  return session;
}
export function sessionView(session) {
  const requests=[...session.requests.values()];
  const provider=requests.filter(r=>r.metadata.source==='deepseek-upstream');
  const modes={enabled:0,disabled:0,unknown:0};
  for(const r of provider) modes[['enabled','disabled'].includes(r.metadata.thinking?.type)?r.metadata.thinking.type:'unknown']++;
  const label=r=>`[${r.metadata.source || 'unknown'} · ${r.metadata.role || '未声明角色'} · ${r.id}]`;
  const texts=field=>requests.filter(r=>r[field]).map(r=>`${label(r)}\n${r[field]}`).join('\n\n');
  const latest=provider.at(-1)?.metadata;
  const tools=requests.filter(r=>r.tools.size).map(r=>({request_id:r.id,source:r.metadata.source,tools:[...r.tools.values()]}));
  const results=requests.map(r=>({request_id:r.id,source:r.metadata.source,finish_reason:r.finishReason,usage:r.usage,error:r.error,done:r.done}));
  return { raw:session.raw.join(''),reasoning:texts('reasoning'),content:texts('content'),
    tools:tools.length?JSON.stringify(tools,null,2):'',results:requests.length?JSON.stringify(results,null,2):'',
    count:requests.length,providerCount:provider.length,modes,latest,
    notices:requests.map(r=>r.notice).filter(Boolean).join('\n') };
}
