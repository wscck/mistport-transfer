const $=id=>document.getElementById(id);
let chosen=[], expiryHours=1, uploadMode="files";
const fmt=n=>{if(n<1024)return n+" B";if(n<1048576)return(n/1024).toFixed(1)+" KB";if(n<1073741824)return(n/1048576).toFixed(1)+" MB";return(n/1073741824).toFixed(2)+" GB"};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function openModal(id){$(id).classList.add("show")}
function closeModal(id){$(id).classList.remove("show")}
$("sendOpen").onclick=()=>openModal("sendModal");
$("receiveOpen").onclick=()=>openModal("receiveModal");
document.querySelectorAll("[data-dismiss]").forEach(x=>x.onclick=()=>closeModal(x.dataset.dismiss));
$("noticeDone").onclick=()=>closeModal("codeNoticeModal");
document.addEventListener("keydown",e=>{if(e.key==="Escape")document.querySelectorAll(".modal.show").forEach(m=>m.classList.remove("show"))});

$("expiryCurrent").onclick=()=>{
  const opened=$("expiryOptions").classList.toggle("open");
  $("expiryCurrent").setAttribute("aria-expanded",String(opened));
};
$("expiryControl").addEventListener("mouseenter",()=>{$("expiryOptions").classList.add("open");$("expiryCurrent").setAttribute("aria-expanded","true")});
$("expiryControl").addEventListener("mouseleave",()=>{$("expiryOptions").classList.remove("open");$("expiryCurrent").setAttribute("aria-expanded","false")});
document.querySelectorAll("[data-hours]").forEach(btn=>btn.onclick=()=>{
  expiryHours=Number(btn.dataset.hours);
  const labels={1:"1 小时（默认）",3:"3 小时",6:"6 小时",12:"12 小时",24:"24 小时"};
  $("expiryText").textContent=labels[expiryHours];
  document.querySelectorAll("[data-hours]").forEach(x=>x.classList.toggle("chosen",x===btn));
  $("expiryOptions").classList.remove("open");
  $("expiryCurrent").setAttribute("aria-expanded","false");
});

function setMode(mode){
  uploadMode=mode; chosen=[]; $("fileInput").value=""; $("folderInput").value=""; renderChosen();
  document.querySelectorAll(".send-tab").forEach(b=>b.classList.toggle("active",b.dataset.mode===mode));
  $("drop").style.display=mode==="text"?"none":"flex";
  $("textCompose").classList.toggle("show",mode==="text");
  $("dropTitle").textContent=mode==="folder"?"选择整个文件夹":"拖放文件到这里";
  $("dropHint").textContent=mode==="folder"?"文件夹结构会保留，并打包为 ZIP":"或点击选择文件";
  $("choose").textContent=mode==="folder"?"浏览文件夹":"浏览文件";
  $("uploadBtn").disabled=mode==="text"?!$("textContent").value.trim():!chosen.length;
}
document.querySelectorAll(".send-tab").forEach(b=>b.onclick=()=>setMode(b.dataset.mode));
$("choose").onclick=e=>{e.stopPropagation();(uploadMode==="folder"?$("folderInput"):$("fileInput")).click()};
$("drop").onclick=e=>{if(e.target.tagName!=="BUTTON")(uploadMode==="folder"?$("folderInput"):$("fileInput")).click()};
$("fileInput").onchange=e=>{chosen=[...e.target.files];renderChosen()};
$("folderInput").onchange=e=>{chosen=[...e.target.files];renderChosen()};
$("textContent").oninput=()=>{$("uploadBtn").disabled=!$("textContent").value.trim()};
function renderChosen(){
  const label=uploadMode==="folder"?`${chosen.length} 个文件 · ${fmt(chosen.reduce((n,f)=>n+f.size,0))}`:chosen.map(f=>`${f.name}（${fmt(f.size)}）`).join(" · ");
  $("selected").textContent=chosen.length?label:"";
  $("uploadBtn").disabled=uploadMode==="text"?!$("textContent").value.trim():!chosen.length;
}
["dragover","dragenter"].forEach(ev=>$("drop").addEventListener(ev,e=>{e.preventDefault();$("drop").classList.add("drag")}));
["dragleave","drop"].forEach(ev=>$("drop").addEventListener(ev,e=>{
  $("drop").classList.remove("drag");
  if(ev==="drop"){e.preventDefault();chosen=[...e.dataTransfer.files];renderChosen()}
}));

$("uploadBtn").onclick=async()=>{
  if(uploadMode==="text"&&!$("textContent").value.trim())return;
  if(uploadMode!=="text"&&!chosen.length)return;
  const fd=new FormData();
  if(uploadMode==="text"){
    const base=($("textTitle").value.trim()||"文字消息").replace(/[\\/:*?"<>|]/g,"_");
    const blob=new Blob([$("textContent").value],{type:"text/plain;charset=utf-8"});
    fd.append("files",blob,base.endsWith(".txt")?base:base+".txt");
    fd.append("upload_kind","files");
  }else{
    chosen.forEach(f=>fd.append("files",f,uploadMode==="folder"?(f.webkitRelativePath||f.name):f.name));
    fd.append("upload_kind",uploadMode);
  }
  fd.append("expiry_hours",String(expiryHours));
  $("uploadBtn").disabled=true;
  $("uploadStatus").textContent="正在上传文件…";
  try{
    const r=await fetch("/api/upload",{method:"POST",body:fd});
    const j=await r.json();
    if(!r.ok)throw Error(j.detail||"上传失败");
    closeModal("sendModal");
    $("uploadStatus").textContent="";
    $("codeResults").innerHTML=j.files.map(f=>`
      <div class="result-code">
        <small>YOUR TEMPORARY RECEIVE CODE</small>
        <strong>${esc(f.code)}</strong>
        <span>${esc(f.name)} · ${fmt(f.size)}</span>
        <span class="code-expiry">有效期 ${f.expiry_hours} 小时 · ${new Date(f.expires_at).toLocaleString()} 自动删除</span>
        <button class="copy-code" data-code="${esc(f.code)}">复制接收码</button>
      </div>`).join("");
    document.querySelectorAll("[data-code]").forEach(b=>b.onclick=async()=>{
      try{await navigator.clipboard.writeText(b.dataset.code);b.textContent="已复制"}catch{b.textContent="请手动复制上方接收码"}
    });
    chosen=[];$("fileInput").value="";$("folderInput").value="";$("textContent").value="";$("textTitle").value="文字消息";setMode("files");
    openModal("codeNoticeModal");
    loadRecent();
  }catch(e){
    $("uploadStatus").textContent=e.message;
  }finally{
    $("uploadBtn").disabled=!chosen.length;
  }
};

$("receiveCode").addEventListener("input",e=>{e.target.value=e.target.value.replace(/\D/g,"").slice(0,6)});
$("receiveBtn").onclick=async()=>{
  const code=$("receiveCode").value.trim();
  if(code.length!==6){$("receiveStatus").textContent="请输入完整的 6 位接收码";return}
  $("receiveBtn").disabled=true;
  $("receiveStatus").textContent="正在验证接收码…";
  try{
    const r=await fetch("/api/receive",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({code})});
    if(!r.ok){const j=await r.json();throw Error(j.detail||"接收失败")}
    const blob=await r.blob();
    const cd=r.headers.get("content-disposition")||"";
    let name="received-file";
    const m=cd.match(/filename\*=UTF-8''([^;]+)/i)||cd.match(/filename="?([^";]+)"?/i);
    if(m)try{name=decodeURIComponent(m[1])}catch{name=m[1]}
    const a=document.createElement("a"),url=URL.createObjectURL(blob);
    a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
    $("receiveStatus").textContent="验证成功，下载已开始。";
    loadRecent();
  }catch(e){$("receiveStatus").textContent=e.message}
  finally{$("receiveBtn").disabled=false}
};

async function loadRecent(){
  try{
    const j=await(await fetch("/api/recent")).json();
    $("recentItems").innerHTML=j.items.length?j.items.map(f=>`
      <div class="recent-card">
        <div class="recent-icon">▤</div>
        <div class="recent-info">
          <div class="recent-name">${esc(f.name)}</div>
          <div class="recent-meta">${new Date(f.created_at).toLocaleString()} · ${fmt(f.size)}</div>
        </div>
        <div class="recent-count">↓ ${f.downloads} 次</div>
      </div>`).join(""):'<div class="recent-card"><div class="recent-info"><div class="recent-name">暂无传输记录</div><div class="recent-meta">上传文件后会显示在这里</div></div></div>';
  }catch{}
}
loadRecent();
setInterval(loadRecent,15000);
