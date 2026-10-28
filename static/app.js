let course, progress, token, current, view = 'theory', pendingSave, saving = Promise.resolve(), busy = false;
const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
let toastTimer;
function toast(text) { $('#toast').textContent = text; $('#toast').style.display = 'block'; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').style.display = 'none', 6000); }
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json','X-QA-Token':token},body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Ошибка запроса');
  return result;
}
function entry(id = current) { return progress[id] ||= {code:course.find(l => l.id === id).starter,hints:0,passed:0,attempts:0}; }
function nav() {
  let previous = '';
  $('#lessons').innerHTML = course.map((lesson, i) => {
    const heading = lesson.module !== previous ? `<div class="module-title">${esc(lesson.module)}</div>` : '';
    previous = lesson.module;
    return heading + `<button class="lesson-link ${lesson.id===current?'active':''} ${progress[lesson.id]?.passed?'done':''}" data-id="${lesson.id}" ${lesson.id===current?'aria-current="step"':''}><span class="lesson-num">${progress[lesson.id]?.passed?'✓':String(i+1).padStart(2,'0')}</span>${esc(lesson.title)}</button>`;
  }).join('');
  const count = course.filter(l => progress[l.id]?.passed).length;
  $('#progress-label').textContent = `${count} / ${course.length}`;
  $('#progress').max = course.length; $('#progress').value = count;
  const stats = $('#panel .next-row p');
  if (view === 'practice' && stats) stats.textContent = `Попыток: ${entry().attempts || 0} · Подсказок: ${entry().hints || 0}`;
  document.querySelectorAll('[data-id]').forEach(button => button.onclick = async () => { if (busy) return toast('Дождись завершения проверки.'); await flush(); current = button.dataset.id; localStorage.setItem('qa-path-lesson', current); view = 'theory'; render(); window.scrollTo(0,0); });
}
function render() {
  localStorage.setItem('qa-path-lesson', current);
  nav();
  const lesson = course.find(l => l.id === current), index = course.indexOf(lesson), item = entry();
  $('#module-label').textContent = lesson.module.slice(5);
  $('#content').innerHTML = `<section class="hero"><div class="eyebrow"><span class="pill">УРОК ${String(index+1).padStart(2,'0')}</span> ${item.passed?'ПРАКТИКА ВЫПОЛНЕНА':'ШАГ ЗА ШАГОМ'}</div><h1>${esc(lesson.title)}</h1><p>${esc(lesson.goal)}</p><div class="lesson-meta"><span>◷ ${lesson.minutes} минут</span><span>⌘ Пример + практика</span><span>↳ ${index+1} из ${course.length} уроков</span></div></section><div class="tabs"><button class="tab ${view==='theory'?'active':''}" data-view="theory">01 · Разобраться</button><button class="tab ${view==='practice'?'active':''}" data-view="practice">02 · Попробовать</button><button class="tab ${view==='history'?'active':''}" data-view="history">История попыток</button></div><div id="panel"></div>`;
  document.querySelectorAll('[data-view]').forEach(button => button.onclick = async () => { if (busy) return; await flush(); view = button.dataset.view; render(); });
  if (view === 'theory') {
    $('#panel').innerHTML = `<div class="lesson-grid"><div><section class="card"><div class="section-label">Главная идея</div><h3>Что происходит и зачем</h3>${lesson.theory.map(p=>`<p>${esc(p)}</p>`).join('')}<div class="code-wrap"><div class="code-title"><span>Пример · ${lesson.id==='08-git'?'терминал':'Python'}</span><span>Читаем сверху вниз</span></div><pre>${esc(lesson.example)}</pre></div><div class="section-label">Разбираем по шагам</div><ol class="breakdown">${lesson.breakdown.map((p,i)=>`<li><span>${String(i+1).padStart(2,'0')}</span>${esc(p)}</li>`).join('')}</ol></section><div class="next-row"><p>Понимание закрепляется в действии.</p><button class="primary" id="to-practice">Перейти к практике →</button></div></div><aside class="side-info"><div class="tip"><div class="section-label">✦ Простая ассоциация</div><strong>Запомни через знакомое</strong><p>${esc(lesson.tip)}</p></div><div class="aside-note"><strong>Не нужно запоминать всё</strong>Прочитай пример, объясни его своими словами, затем попробуй написать решение. Возвращаться к теории — нормально.</div><div class="aside-note"><strong>Один понятный шаг</strong>Задание считается выполненным после успешной проверки. Подсказки сохраняются отдельно.</div></aside></div>`;
    $('#to-practice').onclick = () => {view='practice';render();};
  } else if (view === 'practice') {
    $('#panel').innerHTML = `<section class="card"><div class="exercise-top"><div class="section-label">Твоя задача</div><span id="save-state" class="save-state">Сохранение при изменении</span></div><h3>Теперь твоя очередь</h3><p>${esc(lesson.task)}</p><div class="editor"><div class="code-title editor-head"><span>${lesson.id}.py</span><span>Python · Tab = 4 пробела</span></div><textarea id="editor" aria-label="Код решения" spellcheck="false" autocapitalize="off" autocomplete="off">${esc(item.code)}</textarea></div><div class="actions"><button class="primary" id="check">▶ Проверить решение</button><button class="secondary" id="hint">Подсказка · ${item.hints}/${lesson.hints.length}</button><button class="secondary" id="write-file">Сохранить файл для IDE</button><button class="secondary" id="read-file">Прочитать из файла</button></div><div id="hints"></div><div id="result" aria-live="polite"></div><p style="margin-top:20px;font-size:11px">Код выполняется локально с правами твоего пользователя. Запускай здесь только свои учебные решения. Проверка ограничена 8 секундами; это не защищённая песочница.</p></section><div class="next-row"><p>Попыток: ${item.attempts || 0} · Подсказок: ${item.hints || 0}</p><button class="secondary" id="next">${index===course.length-1?'Вернуться к началу':'Следующий урок →'}</button></div>`;
    const editor = $('#editor');
    editor.oninput = () => { entry().code=editor.value; $('#save-state').textContent='Сохраняем…'; clearTimeout(pendingSave); pendingSave=setTimeout(()=>flush(),500); };
    editor.onkeydown = event => {if(event.key==='Tab'){event.preventDefault(); const start=editor.selectionStart,end=editor.selectionEnd;editor.setRangeText('    ',start,end,'end');editor.dispatchEvent(new Event('input'));}};
    $('#hint').onclick = async () => {entry().hints=Math.min(lesson.hints.length,entry().hints+1);showHints();await flush();};
    $('#write-file').onclick = async () => {try{await flush();const result=await api('/api/file',{lesson:current,code:entry().code});toast(`Файл сохранён: ${result.path}`);}catch(e){toast(e.message);}};
    $('#read-file').onclick = async () => {try{if(!confirm('Заменить текст в редакторе содержимым файла из workspace?'))return;const result=await api('/api/file',{lesson:current,read:true});editor.value=result.code;editor.dispatchEvent(new Event('input'));toast('Код загружен. Нажми «Проверить решение».');}catch(e){toast(e.message);}};
    $('#check').onclick = runCheck;
    $('#next').onclick = async () => {await flush();current=course[(index+1)%course.length].id;localStorage.setItem('qa-path-lesson',current);view='theory';render();window.scrollTo(0,0);};
    showHints();
  } else {
    $('#panel').innerHTML='<section class="card"><h3>История последних попыток</h3><div id="history">Загружаем…</div></section>';
    api('/api/history').then(rows=>{const target=$('#history');if(!target)return;const filtered=rows.filter(r=>r.lesson===current);target.innerHTML=filtered.length?filtered.map(row=>`<div class="history-row"><span>${row.passed?'✓ Выполнено':'↻ Нужна доработка'}</span><span>${esc(row.created)} UTC</span></div>`).join(''):'<p class="empty">Здесь появятся результаты проверок этого урока. Учитываются последние 30 попыток по всему курсу.</p>';}).catch(e=>toast(e.message));
  }
}
function showHints(){const lesson=course.find(l=>l.id===current);$('#hints').innerHTML=entry().hints?`<div class="hint-box">${lesson.hints.slice(0,entry().hints).map((hint,i)=>`<p><strong>Подсказка ${i+1}.</strong> ${esc(hint)}</p>`).join('')}</div>`:'';$('#hint').textContent=`Подсказка · ${entry().hints}/${lesson.hints.length}`;}
function flush(){clearTimeout(pendingSave);if(!current)return Promise.resolve();const id=current, item={...entry()};saving=saving.catch(()=>{}).then(()=>api('/api/save',{lesson:id,code:item.code,hints:item.hints})).then(()=>{if(current===id&&$('#save-state'))$('#save-state').textContent='✓ Сохранено на компьютере';}).catch(e=>{if($('#save-state'))$('#save-state').textContent='Не сохранено';toast(e.message);});return saving;}
async function runCheck(){if(busy)return;busy=true;const button=$('#check');button.disabled=true;button.textContent='Проверяем…';$('#editor').readOnly=true;try{await flush();const result=await api('/api/check',{lesson:current,code:entry().code,hints:entry().hints});progress=result.progress;nav();const r=result.result;$('#result').innerHTML=`<div class="result ${r.passed?'success':''}"><h3>${r.passed?'✓ Получилось. Задание выполнено!':'Пока не всё — разберёмся'}</h3>${r.checks.map(c=>`<div class="check ${c.passed?'pass':'fail'}">${c.passed?'✓':'×'} ${esc(c.label)}</div>`).join('')}${r.error?`<pre class="error">${esc(r.error)}</pre><p>Читай ошибку снизу вверх: тип → сообщение → строка solution.py.</p>`:''}${r.output?`<pre>${esc(r.output)}</pre>`:''}${r.passed?'<p>Объясни себе, почему решение работает, и переходи к следующему уроку.</p>':'<p>Сравни результат с условием. Если застрял, открой одну подсказку.</p>'}</div>`;}catch(e){toast(e.message);}finally{busy=false;button.disabled=false;button.textContent='▶ Проверить решение';$('#editor').readOnly=false;}}
$('#backup').onclick=async()=>{try{await flush();const data=await api('/api/export');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='qa-path-progress.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){toast(e.message);}};
$('#restore').onchange=async event=>{try{const file=event.target.files[0];if(!file)return;if(file.size>500000)throw new Error('Файл слишком большой.');const data=JSON.parse(await file.text());if(!confirm('Импорт заменит сохранённый код соответствующих уроков. Достижения будут объединены. Продолжить?'))return;await flush();const result=await api('/api/import',data);progress=result.progress;render();toast('Прогресс восстановлен.');}catch(e){toast(e.message);}finally{event.target.value='';}};
window.addEventListener('beforeunload',()=>{if(!current)return;const item=entry();fetch('/api/save',{method:'POST',headers:{'Content-Type':'application/json','X-QA-Token':token},body:JSON.stringify({lesson:current,code:item.code,hints:item.hints}),keepalive:true});});
document.addEventListener('click', event => {
  if (busy && event.target.closest('button, .import-label')) {
    event.preventDefault();
    event.stopImmediatePropagation();
    toast('Дождись завершения проверки.');
  }
}, true);
api('/api/course').then(data=>{course=data.lessons;progress=data.progress;token=data.token;const saved=localStorage.getItem('qa-path-lesson');current=course.some(l=>l.id===saved)?saved:course.find(l=>!progress[l.id]?.passed)?.id||course[0].id;render();}).catch(e=>{$('#content').innerHTML=`<div class="card"><h2>Не удалось открыть курс</h2><p>${esc(e.message)}</p><p>Убедись, что app.py работает, и обнови страницу.</p></div>`;});
