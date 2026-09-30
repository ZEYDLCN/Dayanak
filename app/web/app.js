const iconPaths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>',
  message: '<path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H6l-3 2v-9.5A7.5 7.5 0 0 1 10.5 4h2A7.5 7.5 0 0 1 20 11.5Z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  file: '<path d="M6 3h8l5 5v13H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M14 3v6h5M8 13h8M8 17h6"/>',
  sparkles: '<path d="m12 2 1.6 6.4L20 10l-6.4 1.6L12 18l-1.6-6.4L4 10l6.4-1.6L12 2ZM19 17l.6 2.4L22 20l-2.4.6L19 23l-.6-2.4L16 20l2.4-.6L19 17Z"/>',
  'arrow-up-right': '<path d="M5 19 19 5M8 5h11v11"/>',
  'arrow-right': '<path d="M4 12h16m-7-7 7 7-7 7"/>',
  'arrow-left': '<path d="M20 12H4m7-7-7 7 7 7"/>',
  'arrow-up': '<path d="M12 20V4m-7 7 7-7 7 7"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
  box: '<path d="m3 7 9-4 9 4v10l-9 4-9-4V7Z"/><path d="m3 7 9 4 9-4M12 11v10"/>',
  truck: '<path d="M3 6h11v10H3V6Zm11 3h4l3 3v4h-7V9Z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 9a7 7 0 0 1 12-2L20 12M4 12l2.5 5A7 7 0 0 0 19 15"/>',
  card: '<rect x="2" y="5" width="20" height="14" rx="3"/><path d="M2 10h20M6 15h4"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  headset: '<path d="M4 13v-2a8 8 0 0 1 16 0v2M4 13h3v6H5a2 2 0 0 1-2-2v-2a2 2 0 0 1 1-2Zm16 0h-3v6h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-1-2Z"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.6 2.6 0 1 1 4.5 2c-1.1 1-2 1.5-2 3M12 17h.01"/>',
  wifi: '<path d="M2 9a15 15 0 0 1 20 0M5 12a10 10 0 0 1 14 0M8 15a5 5 0 0 1 8 0"/><circle cx="12" cy="19" r="1"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/>'
};

const icon = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const formatAnswer = (value) => escapeHtml(value).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
const el = id => document.getElementById(id);

const topicMeta = {
  'kurulum-kilavuzu': {name:'Kurulum & Cihaz', icon:'box', description:'Lumora Hub kurulumu ve bağlantı'},
  'hesap-ve-sifre': {name:'Hesap & Şifre', icon:'lock', description:'Giriş, güvenlik ve hesap yönetimi'},
  'iade-proseduru': {name:'İade İşlemleri', icon:'refresh', description:'İade süresi ve geri ödeme'},
  'garanti-ve-servis': {name:'Garanti & Servis', icon:'shield', description:'Garanti kapsamı ve onarım'},
  'kargo-ve-teslimat': {name:'Kargo & Teslimat', icon:'truck', description:'Siparişin yolculuğu ve teslimat'},
  'abonelik-ve-faturalama': {name:'Abonelik & Ödeme', icon:'card', description:'Lumora+ planları ve faturalar'},
  'destek-kanallari-sla': {name:'Destek Kanalları', icon:'headset', description:'Bize ulaşma yolları ve süreler'},
  'gizlilik-ve-veri-silme': {name:'Gizlilik & Veri', icon:'lock', description:'Veri güvenliği ve silme talepleri'},
  'sorun-giderme': {name:'Sorun Giderme', icon:'wifi', description:'Yaygın sorunlara hızlı çözümler'}
};
const suggestions = ['İade süresi kaç gün?', 'Lumora Hub hangi Wi-Fi ağına bağlanır?', 'Garanti süresi ne kadar?', 'Aboneliğimi nasıl iptal ederim?'];
const state = {documents:[], health:null, filter:'current', sessions:loadSessions(), currentSessionId:null, busy:false, view:'home'};
let toastTimer;

function loadSessions(){try{const value=JSON.parse(localStorage.getItem('lumora-sessions-v1')||'[]');return Array.isArray(value)?value.filter(s=>s && Array.isArray(s.messages)).slice(0,30):[]}catch{return []}}
function saveSessions(){try{localStorage.setItem('lumora-sessions-v1',JSON.stringify(state.sessions.slice(0,30)))}catch{}}
function toast(message){const node=el('toast');node.textContent=message;node.classList.add('is-visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.classList.remove('is-visible'),3800)}
function route(){const value=location.hash.replace('#/','').split('/')[0];return ['topics','chat'].includes(value)?value:'home'}
function navigate(view){if(location.hash!==`#/${view==='home'?'':view}`)location.hash=`#/${view==='home'?'':view}`;else renderView()}
function renderView(){state.view=route();for(const view of ['home','topics','chat'])el(`${view}-view`).hidden=view!==state.view;el('breadcrumb-current').textContent={home:'Genel bakış',topics:'Konular',chat:'Asistan'}[state.view];document.querySelectorAll('[data-nav]').forEach(item=>{const active=item.dataset.nav===state.view;item.classList.toggle('is-active',active);if(item.classList.contains('nav-item'))item.setAttribute('aria-current',active?'page':'false')});if(state.view==='chat')renderChat();window.scrollTo(0,0)}
function formatDate(timestamp){return new Intl.DateTimeFormat('tr-TR',{day:'numeric',month:'short'}).format(new Date(timestamp))}
function topicName(doc){return topicMeta[doc.family]?.name || doc.title.replace(/\s*\(v\d+\)$/i,'')}
function topicDescription(doc){return topicMeta[doc.family]?.description || (doc.sections || []).slice(0,2).join(' · ')}
function topicIcon(doc){return topicMeta[doc.family]?.icon || 'file'}
function cardMarkup(doc){const archived=doc.status==='superseded';return `<button type="button" class="topic-card" data-topic="${escapeHtml(doc.doc_id)}"><span class="topic-card-top"><span class="topic-icon">${icon(topicIcon(doc))}</span><span class="card-arrow">↗</span></span><strong>${escapeHtml(topicName(doc))}${archived?' <small>v'+escapeHtml(doc.version)+'</small>':''}</strong><p>${escapeHtml(topicDescription(doc))}</p><span class="topic-card-foot"><span>${escapeHtml((doc.sections||[]).length)} bölüm · ${archived?'Arşiv':'Güncel'}</span><span>Keşfet ↗</span></span></button>`}
function renderTopics(){const query=el('topic-search').value.trim().toLocaleLowerCase('tr');const docs=state.documents.filter(doc=>(state.filter==='all'||doc.status===state.filter) && [doc.title,doc.family,...(doc.sections||[]),topicName(doc)].join(' ').toLocaleLowerCase('tr').includes(query));el('topic-grid').innerHTML=docs.length?docs.slice(0,6).map(cardMarkup).join(''):`<div class="empty-state">${state.documents.length?'Bu aramaya uygun konu bulunamadı.':'Belgeler yüklenemedi. Sayfayı yenileyip tekrar deneyin.'}</div>`;document.querySelectorAll('.filter-tab').forEach(tab=>{const active=tab.dataset.filter===state.filter;tab.classList.toggle('is-active',active);tab.setAttribute('aria-selected',String(active))})}
function renderLibrary(){const query=el('library-search').value.trim().toLocaleLowerCase('tr');const docs=state.documents.filter(doc=>[doc.title,doc.family,...(doc.sections||[]),topicName(doc)].join(' ').toLocaleLowerCase('tr').includes(query));el('library-count').textContent=`${docs.length} belge`;el('library-grid').innerHTML=docs.length?docs.map(cardMarkup).join(''):'<div class="empty-state">Bu aramaya uygun belge bulunamadı.</div>'}
function renderStats(){if(!state.health)return;el('stat-documents').textContent=state.health.documents;el('stat-sections').textContent=state.health.chunks;el('stat-mode').textContent=state.health.mode==='llm'?'Yapay zekâ':'Kaynak';el('sidebar-status-text').textContent=`${state.health.documents} belge erişilebilir`}
function session(){return state.sessions.find(s=>s.id===state.currentSessionId)}
function createSession(){state.currentSessionId=null;renderHistory();renderChat();navigate('chat');el('chat-input').focus()}
function openSession(id){state.currentSessionId=id;renderHistory();navigate('chat');renderChat()}
function renderHistory(){const rows=state.sessions.slice(0,5);el('sidebar-history').innerHTML=rows.length?rows.map(s=>`<button type="button" class="history-item ${s.id===state.currentSessionId?'is-active':''}" data-session="${escapeHtml(s.id)}">${icon('message')}<span>${escapeHtml(s.title)}</span></button>`).join(''):'<div class="history-empty">İlk sohbetini başlat, burada görünsün.</div>';el('recent-list').innerHTML=rows.length?rows.slice(0,3).map(s=>`<button type="button" class="recent-item" data-session="${escapeHtml(s.id)}"><span>${icon('message')}</span><div><strong>${escapeHtml(s.title)}</strong><small>${formatDate(s.updatedAt)}</small></div></button>`).join(''):'<p class="recent-empty">Henüz bir sohbet yok. İlk sorunu sorduğunda burada göreceksin.</p>'}
function messageMarkup(message){const isUser=message.role==='user';const time=formatDate(message.time);let details='';if(!isUser && (message.sources?.length||message.conflicts?.length)){details='<div class="message-detail">';if(message.sources?.length){details+=`<details class="source-disclosure"><summary><span class="summary-label">${icon('file')} ${message.sources.length} belge kaynağı</span>${icon('chevron').replace('<svg','<svg class="chevron"')}</summary>${message.sources.map(source=>`<div class="source-body"><strong>${escapeHtml(source.title)} · ${escapeHtml(source.section)} · v${escapeHtml(source.version)}</strong><p>${escapeHtml(source.snippet)}</p></div>`).join('')}</details>`}if(message.conflicts?.length){details+=`<details class="conflict-disclosure"><summary><span class="summary-label">${icon('shield')} Sürüm seçimi</span>${icon('chevron').replace('<svg','<svg class="chevron"')}</summary>${message.conflicts.map(conflict=>`<div class="conflict-body">${escapeHtml(conflict.reason)}</div>`).join('')}</details>`}details+='</div>'}return `<div class="message-block ${isUser?'user':'assistant'}"><div class="message-bubble ${!isUser&&!message.answerable?'is-unanswered':''}">${isUser?escapeHtml(message.text):formatAnswer(message.text)}</div><div class="message-meta">${!isUser?icon('sparkles'):''}${isUser?'Sen':(message.mode==='llm'?'Lumora Asistanı':'Kaynaklı yanıt')} · ${time}</div>${details}</div>`}
function renderChat(){const current=session();const area=el('chat-messages');if(!current||!current.messages.length){area.innerHTML=`<div class="chat-empty"><div class="empty-bot">${icon('sparkles')}</div><h2>Merhaba, nasıl yardımcı<br>olabilirim?</h2><p>Bir soru sor veya aşağıdaki örneklerden biriyle başla. Yanıtı ilgili belgeyle birlikte göstereceğim.</p><div class="suggestions">${suggestions.map(text=>`<button type="button" class="suggestion" data-suggestion="${escapeHtml(text)}">${escapeHtml(text)} ↗</button>`).join('')}</div></div>`}else{area.innerHTML=current.messages.map(messageMarkup).join('')+(state.busy?'<div class="message-block assistant"><div class="typing" aria-label="Yanıt hazırlanıyor"><span></span><span></span><span></span></div></div>':'');area.scrollTop=area.scrollHeight}el('send-button').disabled=state.busy}
function useTopic(docId){const doc=state.documents.find(item=>item.doc_id===docId);if(!doc)return;createSession();const section=doc.sections?.[0];el('chat-input').value=section?`${section} hakkında bilgi verir misin?`:`${topicName(doc)} hakkında bilgi verir misin?`;autoResize()}
function autoResize(){const input=el('chat-input');input.style.height='auto';input.style.height=Math.min(input.scrollHeight,116)+'px'}
async function sendQuestion(question){if(state.busy)return;const clean=question.trim();if(clean.length<3){toast('Lütfen en az 3 karakterlik bir soru yaz.');return}if(clean.length>500){toast('Soru en fazla 500 karakter olabilir.');return}let current=session();if(!current){current={id:globalThis.crypto?.randomUUID?.()||`${Date.now()}-${Math.random()}`,title:clean,updatedAt:new Date().toISOString(),messages:[]};state.sessions.unshift(current);state.currentSessionId=current.id}current.messages.push({role:'user',text:clean,time:new Date().toISOString()});current.updatedAt=new Date().toISOString();state.busy=true;el('chat-input').value='';autoResize();saveSessions();renderHistory();navigate('chat');renderChat();try{const body={question:clean};if(el('as-of-date').value)body.as_of=el('as-of-date').value;const response=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!response.ok){if(response.status===422)throw new Error('Soru biçimi geçersiz. Lütfen tekrar dene.');throw new Error(`Sunucu yanıt vermedi (${response.status}).`)}const data=await response.json();current.messages.push({role:'assistant',text:data.answer||'Yanıt alınamadı.',answerable:data.answerable,sources:data.sources||[],conflicts:data.conflicts||[],mode:data.mode,time:new Date().toISOString()})}catch(error){current.messages.push({role:'assistant',text:`Şu anda yanıt alınamadı. ${error.message||'Lütfen biraz sonra tekrar dene.'}`,answerable:false,sources:[],conflicts:[],mode:'error',time:new Date().toISOString()});toast('Bağlantı sırasında bir sorun oluştu.')}finally{current.updatedAt=new Date().toISOString();state.busy=false;saveSessions();renderHistory();renderChat()}}
async function loadData(){try{const [docsResponse,healthResponse]=await Promise.all([fetch('/documents'),fetch('/health')]);if(!docsResponse.ok||!healthResponse.ok)throw new Error('API yanıt vermedi');state.documents=await docsResponse.json();state.health=await healthResponse.json();renderStats();renderTopics();renderLibrary()}catch{el('topic-grid').innerHTML='<div class="empty-state">Belgelere şu anda ulaşılamıyor. Sayfayı yenileyip tekrar deneyin.</div>';el('library-grid').innerHTML='<div class="empty-state">Belgelere şu anda ulaşılamıyor.</div>';el('sidebar-status-text').textContent='Bağlantı kurulamadı';toast('Bilgi merkezi yüklenemedi.')}}

document.querySelectorAll('[data-icon]').forEach(node=>node.innerHTML=icon(node.dataset.icon));
document.querySelectorAll('[data-nav]').forEach(button=>button.addEventListener('click',()=>navigate(button.dataset.nav)));
document.querySelectorAll('.filter-tab').forEach(button=>button.addEventListener('click',()=>{state.filter=button.dataset.filter;renderTopics()}));
el('topic-search').addEventListener('input',renderTopics);el('library-search').addEventListener('input',renderLibrary);
document.addEventListener('click',event=>{const topic=event.target.closest('[data-topic]');if(topic)useTopic(topic.dataset.topic);const history=event.target.closest('[data-session]');if(history)openSession(history.dataset.session);const suggestion=event.target.closest('[data-suggestion]');if(suggestion)sendQuestion(suggestion.dataset.suggestion)});
for(const id of ['sidebar-new-chat','chat-new','hero-ask','promo-ask','assistant-card-button'])el(id).addEventListener('click',createSession);
el('see-all-topics').addEventListener('click',()=>navigate('topics'));el('chat-back').addEventListener('click',()=>navigate('home'));
el('chat-form').addEventListener('submit',event=>{event.preventDefault();sendQuestion(el('chat-input').value)});
el('chat-input').addEventListener('input',autoResize);el('chat-input').addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();el('chat-form').requestSubmit()}});
document.addEventListener('keydown',event=>{if(event.key==='/'&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)&&state.view!=='chat'){event.preventDefault();el(state.view==='topics'?'library-search':'topic-search').focus()}});
el('today-date').textContent=new Intl.DateTimeFormat('tr-TR',{day:'numeric',month:'long',year:'numeric'}).format(new Date());
window.addEventListener('hashchange',renderView);
renderHistory();renderView();loadData();
