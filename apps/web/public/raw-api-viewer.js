import {freshSession,applySessionRecord,sessionView} from './raw-api-core.js';
const $=id=>document.getElementById(id);
let session=freshSession(),source=null,lastId='0',timer=null,renderedVersion=-1;
const baseUrl='/v1/raw-api';

function render(){
  timer=null;
  if(renderedVersion!==session.version){
    const view=sessionView(session);
    $('metadata').textContent=`累计 ${view.count} 次调用 · DeepSeek ${view.providerCount} 次 · ${session.frames} 条响应记录\nDeepSeek thinking：开启 ${view.modes.enabled} / 关闭 ${view.modes.disabled} / 未声明 ${view.modes.unknown}\n最近一次上游请求：${view.latest?.timestamp || '暂无'} · thinking: ${view.latest?.thinking?.type || '未知'}`;
    $('raw').value=view.raw;
    $('reasoning').textContent=view.reasoning || (view.providerCount && view.modes.disabled===view.providerCount
      ? '这些上游请求均关闭了 thinking，因此没有返回思考内容。开启配置只影响后续新请求。' : '尚未收到 reasoning_content');
    $('content').textContent=view.content || '尚未收到 content；可查看下方工具调用参数';
    $('tools').textContent=view.tools || '尚未收到 tool_calls';
    $('result').textContent=view.results || '尚无执行记录';
    $('count').textContent=`${session.frames} 条返回`;
    $('copy').disabled=!view.raw;
    if(view.notices)$('hint').textContent=view.notices;
    renderedVersion=session.version;
  }
  if($('follow').checked)for(const id of ['raw','reasoning','content','tools'])$(id).scrollTop=$(id).scrollHeight;
}
function connect(){
  source?.close();$('connection').textContent='连接中…';
  source=new EventSource(`${baseUrl}/events?after=${encodeURIComponent(lastId)}`);
  source.onopen=()=>{$('connection').textContent='已连接 · 全部记录连续展示';};
  source.onerror=()=>{$('connection').textContent='后台未连接 · 自动重连中';};
  source.onmessage=event=>{
    if(Number(event.lastEventId)<=Number(lastId))return;
    lastId=event.lastEventId;
    applySessionRecord(session,JSON.parse(event.data));
    $('connection').textContent=`已接收 ${session.requests.size} 次调用 · 同一套记录`;
    if(!timer)timer=setTimeout(render,300);
  };
}
async function checkStatus(){
  try{
    const resp=await fetch(`${baseUrl}/status`);
    if(!resp.ok)throw new Error(resp.statusText);
    const status=await resp.json();
    const receipt=status.thinking_mode && status.thinking_mode!=='unknown'?`启动回执 thinking: ${status.thinking_mode}。`:'未取得启动回执，以实际请求元信息为准。';
    $('hint').textContent=`${receipt} 全部请求在同一套记录中展示；切换模式不会改写旧记录。`;
  }catch{$('hint').textContent='后台（端口 8000）未连接，请先启动后台。';}
}
$('reconnect').onclick=()=>{checkStatus();connect();};
$('follow').onchange=render;
$('copy').onclick=async()=>{
  try{await navigator.clipboard.writeText(session.raw.join(''));$('hint').textContent='已复制全部原始响应（保持接收顺序）';}
  catch{$('hint').textContent='复制失败，可在原始数据区域手动选择复制';}
};
$('clear').onclick=async()=>{
  try{
    const resp=await fetch(`${baseUrl}/clear`,{method:'POST'});
    if(!resp.ok)throw new Error();
    source?.close();session=freshSession();lastId='0';renderedVersion=-1;render();
    $('hint').textContent='旧记录已归档；开始新的抓取记录';connect();
  }catch{$('hint').textContent='归档失败，现有记录保留';}
};
window.addEventListener('pagehide',()=>source?.close());
checkStatus().then(connect);
