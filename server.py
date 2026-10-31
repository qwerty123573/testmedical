#!/usr/bin/env python3
"""testmedical.kg: сервер на чистом Python (без установки библиотек).

Запуск:   python server.py            (порт 8000)
          python server.py 8080        (другой порт)

Руководитель сохраняет тесты, они хранятся в файле tests.json рядом со скриптом.
Студенты открывают тот же адрес и видят общие тесты.
Регистрация руководителя и изменение тестов требуют секретный код.
"""
import hmac, json, os, socket, sys, threading, time
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "tests.json")
LOCK = threading.Lock()
# Секретный код руководителя. Лучше задать свой: LEADER_CODE=12345 python server.py
LEADER_CODE = os.environ.get("LEADER_CODE", "92737")


def ok_code(c):
    return hmac.compare_digest(str(c).encode(), LEADER_CODE.encode())

HTML = r'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>testmedical.kg</title>
<style>
:root{--bg:#F4F8F7;--card:#fff;--ink:#0F2A2E;--mut:#4A5F63;--line:#D5E3E1;--pri:#0E7C7B;--pt:#fff;--soft:#DDF1EF;--bad:#B3261E;--ok:#1B7A3E;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0E1A1C;--card:#152427;--ink:#E6F2F1;--mut:#9DB5B3;--line:#264245;--pri:#2BB5B0;--pt:#06201F;--soft:#1B3335;--bad:#FF8A80;--ok:#7BDC9B;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0E1A1C;--card:#152427;--ink:#E6F2F1;--mut:#9DB5B3;--line:#264245;--pri:#2BB5B0;--pt:#06201F;--soft:#1B3335;--bad:#FF8A80;--ok:#7BDC9B;color-scheme:dark}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.45}
.nav{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px 20px;background:var(--card);border-bottom:1px solid var(--line)}
.logo{font-weight:800;font-size:20px;margin-right:auto}.logo b{color:var(--pri)}
.wrap{max-width:1000px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:32px;margin:0 0 6px;line-height:1.15}h2{font-size:22px;margin:0 0 12px}h3{margin:0 0 6px;font-size:19px}
p{margin:0;color:var(--mut)}
.btn{min-height:44px;padding:0 18px;border-radius:10px;border:1.5px solid var(--pri);background:var(--card);color:var(--pri);font:600 15px inherit;font-family:inherit;cursor:pointer}
.btn.p{background:var(--pri);color:var(--pt)}.btn.d{border-color:var(--bad);color:var(--bad)}.btn.s{min-height:38px;padding:0 12px;font-size:14px}
.tab{background:none;border:0;color:var(--mut);min-height:44px;padding:0 10px;font:600 15px inherit;font-family:inherit;cursor:pointer}.tab.on{color:var(--pri);box-shadow:inset 0 -3px var(--pri)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;display:flex;flex-direction:column;gap:10px;margin-bottom:14px}
.grid .card{margin:0}
.in{width:100%;min-height:44px;border:1.5px solid var(--line);border-radius:10px;padding:0 12px;font:16px inherit;font-family:inherit;background:var(--bg);color:var(--ink)}
label{font-size:14px;font-weight:600;display:flex;flex-direction:column;gap:6px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.sp{justify-content:space-between}
.opt{display:flex;gap:8px;align-items:center}.opt input[type=radio]{width:22px;height:22px;accent-color:var(--pri);flex:none}
.tm{display:flex;align-items:center;gap:6px}.tm input{width:72px;text-align:center}
.tag{display:inline-block;padding:2px 10px;border-radius:99px;background:var(--soft);color:var(--pri);font-size:13px;font-weight:600}
.ans{width:100%;text-align:left;min-height:48px;padding:10px 14px;border-radius:10px;border:1.5px solid var(--line);background:var(--card);color:var(--ink);font:16px inherit;font-family:inherit;cursor:pointer;margin-bottom:8px}
.ans.ok{border-color:var(--ok);background:var(--soft)}.ans.no{border-color:var(--bad)}
.bar{height:8px;border-radius:8px;background:var(--line);overflow:hidden}.bar i{display:block;height:100%;background:var(--pri)}
.big{font-size:40px;font-weight:800}
</style>
</head>
<body>
<div id="app"></div>
<script>
var S={user:null,tests:[],cur:null,view:'auth',R:null,T:null,mode:'reg'};
try{var d=JSON.parse(localStorage.getItem('tm')||'null');if(d){S.user=d.user;S.tests=d.tests||[];S.view=S.user?'home':'auth';}}catch(e){}
function save(){try{localStorage.setItem('tm',JSON.stringify({user:S.user,tests:S.tests}))}catch(e){}
if(S.user&&S.user.role==='lead'){try{fetch('/api/tests',{method:'POST',headers:{'Content-Type':'application/json','X-Code':S.user.code||''},body:JSON.stringify(S.tests)}).catch(function(){})}catch(e){}}}
function sync(){try{fetch('/api/tests').then(function(r){return r.json()}).then(function(t){if(Array.isArray(t)&&(t.length||!S.tests.length)){S.tests=t;if(S.view!=='edit'&&S.view!=='quiz')render()}}).catch(function(){})}catch(e){}}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function uid(){return Math.random().toString(36).slice(2,9)}
function newQ(){return {q:'',o:['','','',''],c:0,sec:30,pts:1}}
function go(v){clearInterval(S.T);S.view=v;render();window.scrollTo(0,0)}
var TPL=[
{title:'Анатомия: основы',qs:[['Сколько костей у взрослого человека?',['206','208','196','212'],0,30],['Какой орган качает кровь?',['Печень','Сердце','Почки','Лёгкие'],1,20],['Самая крупная кость скелета?',['Бедренная','Плечевая','Большеберцовая','Ребро'],0,25]]},
{title:'Первая помощь',qs:[['С чего начать при остановке дыхания?',['Позвать на помощь и проверить сознание','Дать воды','Поднять ноги','Ждать'],0,30],['Как остановить сильное артериальное кровотечение?',['Давящая повязка или жгут выше раны','Промыть водой','Приложить лёд','Ничего не делать'],0,40]]},
{title:'Фармакология: общее',qs:[['Что такое доза препарата?',['Количество вещества на один приём','Срок годности','Цена','Название'],0,25],['Путь введения «per os» означает:',['Через рот','В вену','В мышцу','Под кожу'],0,20]]}];
function role(){return S.user&&S.user.role==='lead'?'Руководитель':'Студент'}
function fmtDate(t){if(!t.date)return 'не назначен';var s=t.date.split('-').reverse().join('.');return s+(t.time?' в '+t.time:'')}
function days(t){if(!t.date)return null;var a=new Date(t.date+'T00:00:00'),b=new Date();b.setHours(0,0,0,0);return Math.round((a-b)/864e5)}
function total(t){return t.qs.reduce(function(a,q){return a+(+q.sec||0)},0)}
function pts(q){return q.pts==null?1:q.pts}
function maxP(t){return t.qs.reduce(function(a,q){return a+pts(q)},0)}
function mmss(s){return Math.floor(s/60)+':'+('0'+(s%60)).slice(-2)}

function nav(){var h='<div class="nav"><div class="logo">test<b>medical</b>.kg</div>';
if(S.user){(S.user.role==='lead'?[['home','Главная'],['tests','Мои тесты'],['archive','Архив'],['plan','Планировщик']]:[['home','Главная'],['tests','Тесты']]).forEach(function(x){h+='<button class="tab'+(S.view===x[0]?' on':'')+'" onclick="go(\''+x[0]+'\')">'+x[1]+'</button>'});
h+='<span class="tag">'+esc(S.user.name)+' · '+role()+'</span><button class="btn s" onclick="logout()">Выйти</button>'}
return h+'</div>'}
function logout(){S.user=null;save();S.view='auth';render()}

function vAuth(){var reg=S.mode==='reg';
return '<div class="wrap" style="max-width:460px"><div class="card" style="padding:28px"><h1>'+(reg?'Регистрация':'Вход')+'</h1><p>Платформа медицинских тестов</p>'+
(reg?'<label>Имя и фамилия<input class="in" id="nm" autocomplete="name"></label>':'')+
'<label>Email<input class="in" id="em" type="email" autocomplete="email"></label>'+
'<label>Пароль<input class="in" id="pw" type="password" autocomplete="current-password"></label>'+
(reg?'<fieldset style="border:0;padding:0;margin:0"><legend style="font-size:14px;font-weight:600;margin-bottom:6px">Я регистрируюсь как</legend><div class="row"><label style="flex-direction:row;align-items:center;gap:8px"><input type="radio" name="rl" value="student" checked onchange="$(\'cl\').style.display=\'none\'" style="width:20px;height:20px;accent-color:var(--pri)">Студент</label><label style="flex-direction:row;align-items:center;gap:8px"><input type="radio" name="rl" value="lead" onchange="$(\'cl\').style.display=\'flex\'" style="width:20px;height:20px;accent-color:var(--pri)">Руководитель</label></div></fieldset>':'')+
(reg?'<label id="cl" style="display:none">Код руководителя<input class="in" id="cd" type="password" inputmode="numeric" autocomplete="off"></label>':'')+'<div id="err" style="color:var(--bad);font-size:14px"></div><button class="btn p" onclick="doAuth()">'+(reg?'Создать аккаунт':'Войти')+'</button>'+
'<button class="tab" onclick="S.mode=\''+(reg?'in':'reg')+'\';render()">'+(reg?'Уже есть аккаунт? Войти':'Нет аккаунта? Регистрация')+'</button></div></div>'}
function doAuth(){var em=$v('em').trim(),pw=$v('pw'),reg=S.mode==='reg',e=$('err');
if(!em||pw.length<6){e.textContent='Введите email и пароль от 6 символов';return}
if(reg){var nm=$v('nm').trim();if(!nm){e.textContent='Введите имя';return}
var r=document.querySelector('input[name=rl]:checked').value;
if(r==='lead'){var cd=$v('cd').trim();fetch('/api/check?code='+encodeURIComponent(cd)).then(function(x){return x.json()}).then(function(j){if(j.ok){S.user={name:nm,email:em,role:'lead',code:cd};save();go('home')}else e.textContent='Неверный код руководителя'}).catch(function(){e.textContent='Нет связи с сервером'});return}
S.user={name:nm,email:em,role:r}}
else{if(!S.user||S.user.email!==em){e.textContent='Аккаунт не найден на этом устройстве. Зарегистрируйтесь.';return}}
save();go('home')}
function $(i){return document.getElementById(i)}function $v(i){return $(i).value}

function isOpen(t){if(S.user.role==='lead'||!t.date)return true;return new Date()>=new Date(t.date+'T'+(t.time||'00:00')+':00')}
function vHomeS(){var up=S.tests.filter(function(t){return !t.arch&&t.date&&days(t)>=0}).length;return '<div class="wrap"><h1>Здравствуйте, '+esc(S.user.name)+'!</h1><p>Здесь вы проходите тесты, которые назначил руководитель.</p><div class="grid"><div class="card"><h3>Тесты</h3><p>Назначено на даты: '+up+'</p><button class="btn p" onclick="go(\'tests\')">Открыть</button></div><div class="card"><h3>Tutor</h3><p>Пройти доступный тест с таймером.</p><button class="btn" onclick="go(\'tutor\')">Начать</button></div></div></div>'}
function vSL(){var L=S.tests.filter(function(t){return !t.arch}).sort(function(a,b){return (a.date||'')<(b.date||'')?-1:1});var h='<div class="wrap"><h1>Тесты</h1><p>Тест открывается в назначенные дату и время. Создавать и менять тесты может только руководитель.</p>';if(!L.length)h+='<div class="card" style="margin-top:16px"><p>Пока нет назначенных тестов.</p></div>';L.forEach(function(t){var o=isOpen(t);h+='<div class="card" style="margin-top:14px"><div class="row sp"><div><h3>'+esc(t.title)+'</h3><p>'+t.qs.length+' вопр. · '+mmss(total(t))+' · '+fmtDate(t)+'</p></div>'+(o?'<button class="btn p" onclick="run(\''+t.id+'\')">Пройти</button>':'<span class="tag">Откроется '+fmtDate(t)+'</span>')+'</div></div>'});return h+'</div>'}
function vHome(){if(S.user.role!=='lead')return vHomeS();var last=S.tests.filter(function(t){return !t.arch}).length;
return '<div class="wrap"><h1>Здравствуйте, '+esc(S.user.name)+'!</h1><p>Создавайте тесты, меняйте вопросы и время на каждый вопрос.</p><div class="grid">'+
'<div class="card"><h3>Создать тест</h3><p>Новый тест с нуля.</p><button class="btn p" onclick="mk()">Создать</button></div>'+
'<div class="card"><h3>Вернуться к старому тесту</h3><p>Активных тестов: '+last+'</p><button class="btn" onclick="go(\'tests\')">Открыть</button></div>'+
'<div class="card"><h3>Шаблоны</h3><p>Готовые заготовки по темам.</p><button class="btn" onclick="go(\'tpl\')">Смотреть</button></div>'+
'<div class="card"><h3>Tutor</h3><p>Пройти тест с таймером и разбором ответов.</p><button class="btn" onclick="go(\'tutor\')">Начать</button></div></div></div>'}
function mk(qs,title){var t={id:uid(),title:title||'Новый тест',qs:qs||[newQ()],arch:false,date:'',time:''};S.tests.unshift(t);save();open(t.id)}
function open(id){S.cur=S.tests.filter(function(t){return t.id===id})[0];go('edit')}
function find(id){return S.tests.filter(function(t){return t.id===id})[0]}

function vList(arch){if(S.user.role!=='lead')return vSL();var L=S.tests.filter(function(t){return !!t.arch===arch});
var h='<div class="wrap"><div class="row sp"><h1>'+(arch?'Архив':'Мои тесты')+'</h1>'+(arch?'':'<button class="btn p" onclick="mk()">+ Создать тест</button>')+'</div>';
if(!L.length)h+='<div class="card"><p>'+(arch?'Архив пуст. Здесь появятся тесты, которые вы отправите в архив.':'Тестов пока нет. Создайте новый или возьмите шаблон.')+'</p></div>';
L.forEach(function(t){h+='<div class="card"><div class="row sp"><div><h3>'+esc(t.title)+'</h3><p>'+t.qs.length+' вопр. · '+mmss(total(t))+' всего · '+maxP(t)+' б. · '+fmtDate(t)+'</p></div><div class="row"><button class="btn s p" onclick="open(\''+t.id+'\')">Редактировать</button>'+
(arch?'<button class="btn s" onclick="arch(\''+t.id+'\',false)">Восстановить</button>':'<button class="btn s" onclick="arch(\''+t.id+'\',true)">В архив</button>')+'<button class="btn s d" onclick="del(\''+t.id+'\')">Удалить</button></div></div></div>'});
return h+'</div>'}
function arch(id,v){find(id).arch=v;save();render()}
function del(id){if(!confirm('Удалить тест насовсем?'))return;S.tests=S.tests.filter(function(t){return t.id!==id});save();render()}

function vTpl(){var h='<div class="wrap"><h1>Шаблоны</h1><p>Выберите заготовку: она скопируется в ваши тесты, и вы сможете всё изменить.</p><div class="grid">';
TPL.forEach(function(t,i){var s=t.qs.reduce(function(a,q){return a+q[3]},0);h+='<div class="card"><h3>'+t.title+'</h3><p>'+t.qs.length+' вопр. · '+mmss(s)+'</p><button class="btn p" onclick="useT('+i+')">Использовать</button></div>'});
return h+'</div></div>'}
function useT(i){var t=TPL[i];mk(t.qs.map(function(q){return {q:q[0],o:q[1].slice(),c:q[2],sec:q[3],pts:1}}),t.title)}

function vEdit(){var t=S.cur,h='<div class="wrap"><div class="row sp"><h1>Редактор теста</h1><span class="tag">Всего времени: <span id="tot">'+mmss(total(t))+'</span> · Баллов: <span id="tp">'+maxP(t)+'</span></span></div>'+
'<div class="card"><label>Название теста<input class="in" value="'+esc(t.title)+'" oninput="S.cur.title=this.value"></label>'+
'<div class="row"><label>Дата проведения<input class="in" type="date" value="'+esc(t.date)+'" oninput="S.cur.date=this.value"></label><label>Время<input class="in" type="time" value="'+esc(t.time)+'" oninput="S.cur.time=this.value"></label></div><p>Студенты смогут начать тест только с этой даты и времени. Тест попадёт в Планировщик.</p></div>';
t.qs.forEach(function(q,i){h+='<div class="card"><div class="row sp"><h3>Вопрос '+(i+1)+'</h3><div class="row"><div class="tm"><span style="font-size:14px;color:var(--mut)">Баллы</span><input class="in" type="number" min="0" max="100" value="'+pts(q)+'" aria-label="Баллы за вопрос '+(i+1)+'" oninput="setPts('+i+',this.value)"></div><div class="tm"><span style="font-size:14px;color:var(--mut)">Время, сек</span><button class="btn s" aria-label="Меньше" onclick="bump('+i+',-5)">−</button><input class="in" type="number" min="5" max="600" value="'+q.sec+'" aria-label="Секунды на вопрос '+(i+1)+'" oninput="setSec('+i+',this.value)"><button class="btn s" aria-label="Больше" onclick="bump('+i+',5)">+</button></div></div></div>'+
'<label>Текст вопроса<input class="in" value="'+esc(q.q)+'" oninput="S.cur.qs['+i+'].q=this.value"></label><p style="font-size:14px">Отметьте верный ответ:</p>';
q.o.forEach(function(o,j){h+='<div class="opt"><input type="radio" name="c'+i+'" aria-label="Верный: вариант '+(j+1)+'"'+(q.c===j?' checked':'')+' onchange="S.cur.qs['+i+'].c='+j+'"><input class="in" placeholder="Вариант '+(j+1)+'" value="'+esc(o)+'" oninput="S.cur.qs['+i+'].o['+j+']=this.value"></div>'});
h+='<div><button class="btn s d" onclick="dq('+i+')">Удалить вопрос</button></div></div>'});
return h+'<div class="row"><button class="btn" onclick="aq()">+ Добавить вопрос</button><button class="btn p" onclick="saveT()">Сохранить</button><button class="btn" onclick="arch(S.cur.id,true);go(\'archive\')">В архив</button></div></div>'}
function setSec(i,v){S.cur.qs[i].sec=Math.max(5,Math.min(600,+v||5));$('tot').textContent=mmss(total(S.cur))}
function bump(i,n){S.cur.qs[i].sec=Math.max(5,Math.min(600,S.cur.qs[i].sec+n));render()}
function setPts(i,v){S.cur.qs[i].pts=Math.max(0,Math.min(100,Math.round(+v)||0));$('tp').textContent=maxP(S.cur)}
function aq(){S.cur.qs.push(newQ());render()}
function dq(i){if(S.cur.qs.length<2){alert('В тесте должен остаться хотя бы один вопрос');return}S.cur.qs.splice(i,1);render()}
function saveT(){if(!S.cur.date&&!confirm('Дата не задана: тест будет доступен студентам сразу. Продолжить?'))return;save();go('tests')}

function vPlan(){var L=S.tests.filter(function(t){return !t.arch}),dated=L.filter(function(t){return t.date}).sort(function(a,b){return (a.date+a.time)<(b.date+b.time)?-1:1}),none=L.filter(function(t){return !t.date});
var h='<div class="wrap"><h1>Планировщик тестов</h1><p>Назначьте дату и время проведения каждого теста.</p>';
if(!L.length)h+='<div class="card"><p>Нет активных тестов.</p></div>';
function r(t){var n=days(t),st=n==null?'':n<0?'прошёл':n===0?'сегодня':'через '+n+' дн.';
return '<div class="card"><div class="row sp"><div><h3>'+esc(t.title)+'</h3><p>'+t.qs.length+' вопр. · '+mmss(total(t))+(st?' · <b>'+st+'</b>':'')+'</p></div><div class="row"><input class="in" style="width:auto" type="date" aria-label="Дата" value="'+esc(t.date)+'" onchange="find(\''+t.id+'\').date=this.value;save();render()"><input class="in" style="width:auto" type="time" aria-label="Время" value="'+esc(t.time)+'" onchange="find(\''+t.id+'\').time=this.value;save();render()"></div></div></div>'}
if(dated.length){h+='<h2 style="margin-top:20px">По расписанию</h2>';dated.forEach(function(t){h+=r(t)})}
if(none.length){h+='<h2 style="margin-top:20px">Без даты</h2>';none.forEach(function(t){h+=r(t)})}
return h+'</div>'}

function vTutor(){var L=S.tests.filter(function(t){return !t.arch&&isOpen(t)&&t.qs.some(function(q){return q.q&&q.o[q.c]})});
var h='<div class="wrap"><h1>Tutor</h1><p>Проходите тест на время: на каждый вопрос действует свой таймер. В конце Tutor покажет, что повторить.</p>';
if(!L.length)h+='<div class="card" style="margin-top:20px"><p>Нет готовых тестов. Создайте тест или возьмите шаблон.</p></div>';
L.forEach(function(t){h+='<div class="card" style="margin-top:14px"><div class="row sp"><div><h3>'+esc(t.title)+'</h3><p>'+t.qs.length+' вопр. · '+mmss(total(t))+'</p></div><button class="btn p" onclick="run(\''+t.id+'\')">Пройти</button></div></div>'});
return h+'</div>'}
function run(id){var t=find(id);S.R={t:t,i:0,ok:0,p:0,miss:[],ans:null,left:t.qs[0].sec};go('quiz');tick()}
function tick(){clearInterval(S.T);S.T=setInterval(function(){var R=S.R;if(!R||R.ans!==null)return;R.left--;var e=$('tl');if(e)e.textContent=mmss(R.left);var b=$('tb');if(b)b.style.width=Math.max(0,R.left/R.t.qs[R.i].sec*100)+'%';if(R.left<=0)pick(-1)},1000)}
function vQuiz(){var R=S.R,t=R.t;if(R.i>=t.qs.length){var m=R.miss.length;return '<div class="wrap" style="max-width:640px"><div class="card"><h1>Результат</h1><div class="big">'+R.p+' / '+maxP(t)+' баллов</div><p>Верных ответов: '+R.ok+' из '+t.qs.length+' · '+(maxP(t)?Math.round(R.p/maxP(t)*100):0)+'%</p>'+(m?'<h3>Tutor советует повторить:</h3>'+R.miss.map(function(x){return '<p>• '+esc(x.q)+'<br><b style="color:var(--ok)">Верно: '+esc(x.a)+'</b></p>'}).join(''):'<p>Отлично, ошибок нет!</p>')+'<div class="row"><button class="btn p" onclick="go(\'tutor\')">К списку</button></div></div></div>'}
var q=t.qs[R.i],h='<div class="wrap" style="max-width:640px"><div class="row sp"><p>Вопрос '+(R.i+1)+' из '+t.qs.length+' · '+pts(q)+' б.</p><span class="tag" id="tl">'+mmss(R.left)+'</span></div><div class="bar"><i id="tb" style="width:'+Math.max(0,R.left/q.sec*100)+'%"></i></div><div class="card" style="margin-top:16px"><h2>'+esc(q.q)+'</h2>';
q.o.forEach(function(o,j){if(!o)return;var c='ans';if(R.ans!==null){if(j===q.c)c+=' ok';else if(j===R.ans)c+=' no'}h+='<button class="'+c+'"'+(R.ans!==null?' disabled':'')+' onclick="pick('+j+')">'+esc(o)+'</button>'});
if(R.ans!==null){h+='<p style="color:var(--ink)">'+(R.ans===q.c?'Верно!':R.ans===-1?'Время вышло. Верный ответ: '+esc(q.o[q.c]):'Неверно. Верный ответ: '+esc(q.o[q.c]))+'</p><button class="btn p" onclick="nxt()">Дальше</button>'}
return h+'</div></div>'}
function pick(j){var R=S.R,q=R.t.qs[R.i];if(R.ans!==null)return;R.ans=j;if(j===q.c){R.ok++;R.p+=pts(q)}else R.miss.push({q:q.q,a:q.o[q.c]});render()}
function nxt(){var R=S.R;R.i++;R.ans=null;if(R.i<R.t.qs.length)R.left=R.t.qs[R.i].sec;render()}

function render(){var v=S.view;if(!S.user&&v!=='auth')v='auth';if(S.user&&S.user.role!=='lead'&&['archive','tpl','edit','plan'].indexOf(v)>-1)v='home';
var m={auth:vAuth,home:vHome,tests:function(){return vList(false)},archive:function(){return vList(true)},tpl:vTpl,edit:vEdit,plan:vPlan,tutor:vTutor,quiz:vQuiz};
$('app').innerHTML=nav()+m[v]()}
render();
sync();setInterval(function(){if(S.user&&S.user.role!=='lead')sync()},15000);
</script>
</body>
</html>
'''


def load():
    try:
        with open(DATA, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path == "/api/check":
            good = ok_code(parse_qs(u.query).get("code", [""])[0])
            if not good:
                time.sleep(1)
            body = json.dumps({"ok": good}).encode()
            self._send(200, body, "application/json")
        elif path == "/api/tests":
            with LOCK:
                body = json.dumps(load(), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        elif path in ("/", "/index.html"):
            self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self):
        if self.path.split("?")[0] != "/api/tests":
            return self._send(404, b"Not found", "text/plain")
        if not ok_code(self.headers.get("X-Code", "")):
            time.sleep(1)
            return self._send(403, b"Forbidden", "text/plain")
        try:
            size = int(self.headers.get("Content-Length", 0))
            if size > 5_000_000:
                raise ValueError("too big")
            tests = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(tests, list):
                raise ValueError("not a list")
        except (ValueError, UnicodeDecodeError):
            return self._send(400, b"Bad request", "text/plain")
        with LOCK:
            tmp = DATA + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(tests, f, ensure_ascii=False, indent=1)
            os.replace(tmp, DATA)
        self._send(200, b"ok", "text/plain")

    def log_message(self, *a):
        pass


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
    print("testmedical.kg запущен")
    print("  На этом компьютере: http://localhost:%d" % port)
    print("  Для студентов (та же Wi-Fi сеть): http://%s:%d" % (lan_ip(), port))
    print("Остановить: Ctrl+C")
    try:
        ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено")
