/* Local controls for TL-IPC4ADW. Uses Home Assistant's authenticated WebSocket. */
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const techIcon = name => {
  const paths = {
    camera:'<rect x="3" y="6" width="13" height="12" rx="3"/><path d="m16 10 5-3v10l-5-3"/><circle cx="9.5" cy="12" r="2"/>',
    refresh:'<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9"/>',
    record:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>',
    person:'<circle cx="12" cy="7" r="3"/><path d="M6 21v-3a6 6 0 0 1 12 0v3M4 3H2v4m18-4h2v4"/>',
    ai:'<rect x="6" y="6" width="12" height="12" rx="3"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4M10 15v-5h4v5m-4-2h4"/>',
    signal:'<path d="M4 18v2m5-7v7m5-12v12m5-17v17"/>',
    sliders:'<path d="M4 7h3m4 0h9M4 17h9m4 0h3"/><circle cx="9" cy="7" r="2"/><circle cx="15" cy="17" r="2"/>',
    shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    bell:'<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/>',
    mic:'<rect x="9" y="2" width="6" height="13" rx="3"/><path d="M5 10v2a7 7 0 0 0 14 0v-2M12 19v3m-3 0h6"/>',
    image:'<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1"/><path d="m3 17 6-6 4 4 3-3 5 5"/>',
    moon:'<path d="M20 14A8 8 0 0 1 10 4a8.5 8.5 0 1 0 10 10Z"/>',
    disk:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    link:'<path d="m10 13 4-4m-6 8-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0m4 0 1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0" transform="translate(1 1) scale(.92)"/>',
    code:'<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18"/>',
    move:'<path d="M12 2v20M2 12h20M9 5l3-3 3 3M9 19l3 3 3-3M5 9l-3 3 3 3M19 9l3 3-3 3"/>',
    crop:'<path d="M5 2v16a1 1 0 0 0 1 1h16M2 5h16a1 1 0 0 1 1 1v16"/>',
    lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
    settings:'<path d="m9 3 1 3h4l1-3 3 2-1 3 2 3h3v3h-3l-2 3 1 3-3 2-1-3h-4l-1 3-3-2 1-3-2-3H2v-3h3l2-3-1-3z"/><circle cx="12" cy="12.5" r="3"/>',
    search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    home:'<path d="m3 11 9-8 9 8M5 9v12h5v-7h4v7h5V9"/>',
    timeline:'<path d="M6 3v18M10 6h10M10 12h7M10 18h10"/><circle cx="6" cy="6" r="2"/><circle cx="6" cy="12" r="2"/><circle cx="6" cy="18" r="2"/>',
    chart:'<path d="M3 3v18h18M7 15l4-5 4 2 5-7"/>',
  };
  return `<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${paths[name]||paths.sliders}</svg>`;
};

class TplinkIpcControls extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode:'open'}); this.group='常用'; this.filter=''; this.data=null; this.message='';
    this.shadowRoot.addEventListener('click', e=>this.click(e));
    this.shadowRoot.addEventListener('change', e=>this.change(e));
    this.shadowRoot.addEventListener('input',e=>{if(e.target.id==='control-search'){this.filter=e.target.value;this.renderFields();}});
    this.shadowRoot.addEventListener('pointerdown', e=>this.drawPoint(e));
    this.onHide=()=>{if(document.hidden)this.stopTalk();};
  }
  setConfig(config) {
    if(!config.entry_id||!/^camera\.[a-z0-9_]+$/.test(config.entity||''))throw new Error('Configure entry_id and an ONVIF camera entity');
    if(this.config && (this.config.entry_id!==config.entry_id||this.config.entity!==config.entity))throw new Error('Reload the card after changing its camera');
    this.config=config;
  }
  set hass(hass) { this._hass=hass; if(this.liveElement)this.liveElement.hass=hass; this.updateSummary(); if(!this.started && this.isConnected)this.start(); }
  getCardSize(){return 14;}
  connectedCallback(){if(this._hass)this.start();document.addEventListener('visibilitychange',this.onHide);}
  disconnectedCallback(){clearInterval(this.timer);this.started=false;this.stopTalk();document.removeEventListener('visibilitychange',this.onHide);}
  start(){if(this.started)return;this.started=true;this.refresh();this.timer=setInterval(()=>{if(!this.shadowRoot.activeElement&&!this.talking)this.refresh();},15000);}
  async request(operation,data={}) { return this._hass.callWS({type:'tplink_ipc_local/control',entry_id:this.config.entry_id,operation,data}); }
  async refresh(){try{const data=await this.request('state');if(!this.isConnected)return;const changed=JSON.stringify(data)!==JSON.stringify(this.data);this.data=data;if(changed||!this.shadowRoot.children.length)this.render();}catch(e){this.message=e.message||'无法读取摄像头';this.render();}}
  async run(operation,data={}) {
    if(this.busy)return;if(this.data?.writable===false && operation!=='state'){this.updateStatus('固件未验证，当前仅可查看');return;}this.busy=true;this.updateStatus('正在保存…');
    try{const result=await this.request(operation,data);if(operation==='firmware_check'){this.firmware=result;this.message=result.message;this.data=await this.request('state');}else if(result.rebooting){this.message='摄像头正在重启，稍后将自动恢复连接';}else{this.data=result;this.message=result.execution_status==='submitted'?'请求已接受，请核实设备实际效果':'已保存并回读确认';}}
    catch(e){this.message=e.message||'操作失败，设备状态未确认';}
    finally{this.busy=false;this.render();}
  }
  field(d) {
    const key=escapeHtml(d.key),v=d.value;
    let input;
    if(d.kind==='switch')input=`<input aria-label="${escapeHtml(d.name)}" data-key="${key}" type="checkbox" ${v===true?'checked':''} ${v===null?'disabled':''}>`;
    else if(d.kind==='select')input=`<select aria-label="${escapeHtml(d.name)}" data-key="${key}">${v===null?'<option disabled selected>状态未识别</option>':''}${Object.keys(d.options).map(o=>`<option ${o===v?'selected':''}>${escapeHtml(o)}</option>`).join('')}</select>`;
    else input=`<input aria-label="${escapeHtml(d.name)}" data-key="${key}" type="${d.kind==='number'?'number':'text'}" value="${escapeHtml(v)}" ${d.kind==='number'?`min="${d.min}" max="${d.max}" step="1"`:`maxlength="${d.max_length}"`}>${d.unit?`<span class="unit">${escapeHtml(d.unit)}</span>`:''}`;
    return `<label class="field"><span>${escapeHtml(d.name)}</span><span class="input">${input}</span></label>`;
  }
  ensureShell() {
    if(this.shadowRoot.querySelector('.live-holder'))return;
    this.shadowRoot.innerHTML=`<style>:host{
  display:block;color-scheme:dark;font:14px -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;
  --camera-accent:#61e4ef;--primary-color:#61e4ef;--primary-text-color:#e4eefb;
  --secondary-text-color:#8395af;--secondary-background-color:#111d2e;--divider-color:#203047;
  --card-background-color:#0c1523;--ha-card-background:#0c1523;--text-primary-color:#07131b;
  --tech-border:rgba(128,174,212,.15);--tech-muted:#8193ad;
  background:#080e18;min-height:calc(100vh - 64px);padding:22px;
  background-image:radial-gradient(ellipse at 18% 0%,rgba(40,158,179,.10),transparent 44%),radial-gradient(ellipse at 98% 30%,rgba(70,79,171,.07),transparent 45%);
}
*{box-sizing:border-box}button,input,select,textarea{font:inherit}button{cursor:pointer}button:disabled,input:disabled,select:disabled{opacity:.45;cursor:not-allowed}
ha-card{display:block;max-width:1440px;margin:auto;background:transparent;border:0;box-shadow:none;padding:0;color:var(--primary-text-color);overflow:visible}
.head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}.brand{display:flex;align-items:center;gap:14px}.brand-mark{display:grid;place-items:center;width:48px;height:48px;background:linear-gradient(145deg,#133541,#101b2c);border:1px solid #30606b;border-radius:15px;color:#78edf0;box-shadow:inset 0 0 24px #5be3ee08,0 5px 28px #0003}.brand-mark svg{width:26px;height:26px}
.eyebrow{font-size:10px;letter-spacing:2.6px;font-weight:650;color:#718da5;margin-bottom:6px}.head h2{margin:0;font-size:25px;font-weight:620;letter-spacing:.8px}.head-actions{display:flex;align-items:center;gap:12px}.badge{display:inline-flex;align-items:center;gap:7px;font-size:12px;letter-spacing:.2px;color:#75dfbc;background:#1030276b;border:1px solid #2a71514d;padding:8px 12px;border-radius:7px;white-space:nowrap}.badge.offline{color:#f896a7;background:#351723;border-color:#713044}
button{display:inline-flex;justify-content:center;align-items:center;gap:8px;color:#b6c6dc;background:#122034;border:1px solid #26374d;border-radius:9px;padding:10px 14px;min-height:40px;transition:background .16s,border-color .16s,color .16s,box-shadow .16s}
button:hover{background:#1a2b43;border-color:#476479;color:#effaff}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #61e4ef;outline-offset:3px}
button svg,.field svg{width:17px;height:17px;flex:none}button.primary{color:#07191f;background:#69e4ec;border-color:#69e4ec;font-weight:650;box-shadow:0 3px 18px #59dce616}button.primary:hover{background:#9af0f4;box-shadow:0 0 20px #59dce62b}button.danger{color:#ffc3ca;border-color:#854453;background:#442534}button.danger:hover{background:#62313e}.refresh-btn{width:38px;min-height:36px;padding:8px;background:transparent;border-color:#25364a}.refresh-btn svg{width:16px;height:16px}
.overview{display:grid;grid-template-columns:minmax(0,2.35fr) minmax(250px,1fr);gap:20px;align-items:start}
.feed-frame{position:relative;overflow:hidden;border:1px solid #294052;border-radius:15px;background:#050a12;box-shadow:0 12px 38px #0003}.feed-top,.feed-bottom{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 16px;background:linear-gradient(90deg,#111f2e,#101925);font-size:12px;color:#8ca0b9}.feed-top strong{display:flex;align-items:center;gap:9px;font-weight:550;color:#d5e5f4}.feed-top strong svg{width:16px;height:16px;color:#64d5e0}.feed-code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px;letter-spacing:1.7px;color:#70849e}.feed-bottom{padding:9px 16px;font-size:11px;border-top:1px solid #1e3041}.feed-bottom .signal{color:#65c9b2;display:flex;gap:6px;align-items:center}.signal svg{height:12px;width:14px}.feed-meta{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.3px}.feed-frame:after{content:"";position:absolute;top:0;left:24px;right:24px;height:1px;background:linear-gradient(90deg,transparent,#5eeaf081,transparent);pointer-events:none}
.live-holder{min-height:200px;position:relative;overflow:hidden;background:#03070d}.live-holder>*{display:block}.live-error{color:#6f829e;text-align:center;padding:80px 20px}.feed-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#64e2b4;box-shadow:0 0 9px #64e2b465;margin-right:6px}.feed-dot.offline{background:#a65e75;box-shadow:none}
.summary{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:auto auto auto minmax(135px,1fr);gap:10px;align-content:stretch;align-self:stretch}.stat{min-width:0;position:relative;min-height:92px;padding:14px 15px;border:1px solid var(--tech-border);border-radius:12px;background:linear-gradient(145deg,#142033,#0d1726);overflow:hidden}.stat:after{position:absolute;content:"";bottom:0;left:15px;width:26px;height:2px;background:var(--stat-color,#5cd2de);opacity:.5}.stat-head{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:11px}.stat-head small{font-size:11px;color:#7d93af}.stat-head svg{width:16px;height:16px;color:var(--stat-color,#5cd2de);opacity:.9}.stat strong{font-size:20px;line-height:1.25;font-weight:600;letter-spacing:.3px;display:block;color:#dfedfc}.stat .number{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:24px;color:#8becf4}.stat .number em{font:11px -apple-system,BlinkMacSystemFont,sans-serif;font-style:normal;color:#8298b4;margin-left:4px}.stat small.sub-label{display:block;color:#56728e;font-size:10px;margin-top:6px}
.system-info{grid-column:1/-1;border:1px solid var(--tech-border);background:#0c1624;border-radius:12px;padding:13px 15px}.info-title{font-size:10px;letter-spacing:1.8px;color:#536f8b;margin-bottom:10px}.info-row{display:flex;justify-content:space-between;align-items:center;gap:10px;color:#8ba1bb;font-size:11px;line-height:1.8}.info-row+ .info-row{margin-top:4px}.info-row b{font-weight:450;color:#a4b8d0}.info-row .muted-value{color:#788b9f}.info-row .amber{color:#c7a46a}
.quick-actions{display:flex;justify-content:space-between;align-items:center;gap:14px;margin:14px 0 25px;padding:12px 14px;border:1px solid var(--tech-border);border-radius:11px;background:linear-gradient(90deg,#101e2c,#101827)}.action-label{font-size:10px;letter-spacing:1.6px;color:#56748f;white-space:nowrap}.action-group{display:flex;gap:7px;flex-wrap:wrap}.quick-actions button{min-height:35px;padding:8px 11px;font-size:12px;border-color:transparent;background:#19283a}.quick-actions button svg{width:15px;height:15px}.quick-actions button.voice{background:#14383d;border-color:#2c6268;color:#9aebeb}.quick-actions button.link{background:transparent;color:#7f96b1}.quick-actions button.link:hover{background:#172538;color:#dbeafa}.quick-actions .action-divider{height:22px;width:1px;align-self:center;background:#294054;margin:0 3px}
.workspace{display:grid;grid-template-columns:155px minmax(0,1fr);gap:18px;align-items:start}.tabs{display:flex;flex-direction:column;gap:4px;border:1px solid var(--tech-border);border-radius:13px;padding:8px;background:#0d1725}.tabs button{position:relative;justify-content:flex-start;text-align:left;gap:9px;border:0;background:transparent;color:#728aa6;padding:11px 10px;font-size:12px;min-height:41px}.tabs button .tab-icon{display:inline-flex;color:#587590}.tabs button .tab-icon svg{width:16px;height:16px}.tabs button .tab-count{margin-left:auto;color:#4b6580;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10px}.tabs button:hover{background:#16273a;color:#c8dae9}.tabs button.active{background:linear-gradient(90deg,#153b45,#142934);color:#98f3f4;font-weight:580}.tabs button.active:before{content:"";height:15px;width:2px;border-radius:2px;background:#7aebef;position:absolute;left:-8px;box-shadow:0 0 10px #5de4ef66}.tabs button.active .tab-icon{color:#81e2eb}.tabs button.active .tab-count{color:#76aeb5}
.settings{border:1px solid var(--tech-border);border-radius:14px;padding:21px 24px;background:linear-gradient(135deg,#111d2c,#0c1623);min-width:0;min-height:300px}.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:18px;margin-bottom:7px}.section-title{display:flex;align-items:baseline;gap:9px}.panel-heading h3{font-size:17px;font-weight:580;margin:0;color:#deebf8}.settings-number{font:10px ui-monospace,SFMono-Regular,monospace;letter-spacing:1px;color:#496780}.search-wrap{display:flex;align-items:center;gap:8px;background:#091321;border:1px solid #21374a;border-radius:8px;padding:0 11px;width:260px}.search-wrap>svg{width:14px;height:14px;color:#526e8b;flex:none}.search-wrap:focus-within{border-color:#477d88;box-shadow:0 0 0 2px #5cd3df0b}.search{border:0!important;outline:0!important;padding:10px 0!important;background:transparent!important;width:100%;font-size:12px!important;min-width:0}.search::-webkit-search-cancel-button{filter:grayscale(1)}input::placeholder{color:#405b78}.hint{font-size:11px;line-height:1.6;color:#7891ad;margin:0 0 19px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px 13px}.field{display:flex;align-items:center;justify-content:space-between;gap:14px;min-height:68px;border:1px solid #203348;border-radius:10px;padding:15px 16px;background:#0b1624;transition:border-color .15s,background .15s}.field:hover{border-color:#315166;background:#0e1c2c}.field>span:first-child{color:#a8bdd4;font-size:13px;line-height:1.5}.input{display:flex;align-items:center;gap:7px;flex:none;min-width:0}.unit{font-size:10px;color:#5d7996}
input:not([type=checkbox]),select,textarea{background:#102237;color:#c7e4f4;border:1px solid #29455c;border-radius:7px;padding:8px;max-width:100%;font-size:12px}select{cursor:pointer;color-scheme:dark}.field select{max-width:170px}.field input[type=number]{width:73px;font-family:ui-monospace,SFMono-Regular,monospace;color:#90e9ef}.field input[type=text]{width:150px}input[type=checkbox]{appearance:none;-webkit-appearance:none;width:40px;height:22px;border:1px solid #38516b;border-radius:15px;background:#172638;position:relative;cursor:pointer;margin:0;transition:all .2s;flex:none}input[type=checkbox]:after{content:"";position:absolute;width:14px;height:14px;left:3px;top:3px;border-radius:50%;background:#657d96;transition:transform .2s,background .2s}input[type=checkbox]:checked{background:#1e7780;border-color:#409aa4;box-shadow:0 0 12px #66e4ea10}input[type=checkbox]:checked:after{transform:translateX(18px);background:#b8fcfb;box-shadow:0 0 5px #8cfff445}
.wide{grid-column:1/-1;min-width:0}p{line-height:1.75}.muted,.tip{color:#718ba6}.tip{font-size:12px;line-height:1.75}.extra{display:flex;gap:9px;flex-wrap:wrap;margin-top:17px}.status{font-size:12px;line-height:1.6;color:#71c4bd;margin-top:15px;min-height:20px}.status:empty{margin-top:6px;min-height:0}.dpad{display:grid;grid-template-columns:repeat(3,59px);gap:6px;width:max-content;margin:18px auto;padding:14px;border:1px solid #2d4a62;border-radius:23px;background:radial-gradient(circle,#193249,#0c1929);box-shadow:inset 0 0 25px #132b3f}.dpad button{padding:0;width:59px;height:48px;min-height:48px;background:#132a3c;border-color:#2b4a62;color:#9cebf0;font-size:18px;border-radius:11px}.dpad button[data-op=stop]{font-size:11px;background:#1e4652;border-color:#3f7b83}.presets{display:flex;flex-wrap:wrap;gap:8px;justify-content:center}.presets button{border-color:#325c6a;color:#8bdce2}.editor{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin-top:20px}.editor label{display:flex;flex-direction:column;gap:8px;font-size:12px;color:#7894b0}.draw{position:relative;max-width:760px;margin-top:17px;touch-action:none;cursor:crosshair;border:1px solid #32556a;border-radius:10px;overflow:hidden}.draw img{display:block;width:100%}.draw svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}.schedule{display:grid;grid-template-columns:65px 1fr;gap:9px;align-items:center;margin-top:15px}.schedule label{font-size:12px;color:#839db9}.schedule input{font-family:ui-monospace,SFMono-Regular,monospace;font-size:12px}.firmware-box{padding:18px 20px;border:1px solid #28445a;border-radius:11px;background:linear-gradient(125deg,#13273a,#0d1c2c);margin:8px 0 17px;line-height:2;font-size:13px}.firmware-box strong{color:#abedf1;font-weight:580}a{color:#72cbdc;text-underline-offset:4px;font-size:12px}.head svg,.feed-frame svg,.tabs svg{fill:none;stroke:currentColor;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round}
@media(min-width:1250px){.stat{min-height:104px}.stat strong{font-size:20px}.stat .number{font-size:28px}.summary{gap:12px}.system-info{padding:15px 17px}}
@media(max-width:1050px){:host{padding:18px}.overview{grid-template-columns:minmax(0,1.85fr) minmax(225px,1fr);gap:15px}.grid{grid-template-columns:1fr}.quick-actions{align-items:flex-start}.action-label{padding-top:10px}.settings{padding:18px}.workspace{grid-template-columns:140px minmax(0,1fr);gap:14px}.stat{padding:12px;min-height:85px}.stat strong{font-size:16px}.stat .number{font-size:23px}.search-wrap{width:210px}.quick-actions .action-divider{display:none}}
@media(max-width:760px){:host{padding:14px 12px}.head{margin-bottom:18px;gap:8px}.brand{gap:10px}.brand-mark{width:39px;height:39px;border-radius:11px}.brand-mark svg{width:22px;height:22px}.eyebrow{font-size:8px;letter-spacing:1.8px}.head h2{font-size:21px}.head-actions{gap:7px}.badge{font-size:10px;padding:7px 9px}.refresh-btn{min-height:31px;width:31px;padding:6px}.overview{grid-template-columns:1fr;gap:12px}.feed-top{padding:10px 13px}.feed-code{font-size:9px}.live-holder{min-height:160px}.summary{grid-template-columns:repeat(4,minmax(0,1fr));grid-template-rows:auto;gap:7px}.stat{padding:11px 9px;min-height:80px;border-radius:9px}.stat-head{margin-bottom:9px}.stat-head small{font-size:10px}.stat-head svg{display:none}.stat strong{font-size:12px}.stat .number{font-size:20px}.stat:after{left:10px;width:20px}.system-info{display:flex;flex-wrap:wrap;gap:6px 18px;padding:10px 12px}.info-title{display:none}.info-row{font-size:10px;flex:1 0 130px}.info-row+.info-row{margin:0}.quick-actions{display:block;padding:10px;margin:12px 0 17px}.action-label{display:none}.action-group{gap:6px}.quick-actions button{font-size:11px;min-height:34px;padding:7px 9px;flex:1}.quick-actions button svg{width:14px;height:14px}.quick-actions button.link{flex:1}.workspace{display:block}.tabs{flex-direction:row;flex-wrap:nowrap;overflow:auto;gap:3px;padding:5px;margin-bottom:13px;border-radius:10px;scrollbar-width:none}.tabs::-webkit-scrollbar{display:none}.tabs button{flex:none;white-space:nowrap;min-height:37px;font-size:11px;padding:8px 10px;border-radius:6px}.tabs button .tab-count{display:none}.tabs button .tab-icon svg{width:14px;height:14px}.tabs button.active:before{display:none}.settings{padding:16px 13px;border-radius:12px}.panel-heading{flex-wrap:wrap;gap:12px}.search-wrap{width:100%;order:2}.panel-heading h3{font-size:16px}.hint{font-size:10px;margin:10px 0 14px}.field{min-height:62px;padding:12px}.field>span:first-child{font-size:12px}.field select{max-width:155px}.grid{gap:9px}.firmware-box{padding:12px;font-size:12px}.extra button{font-size:12px}.schedule{grid-template-columns:45px 1fr}}
@media(max-width:390px){.head h2{font-size:19px}.badge{font-size:9px}.summary{grid-template-columns:1fr 1fr}.stat-head svg{display:block}.stat{min-height:80px}.stat strong{font-size:16px}.field select{max-width:130px}.field input[type=text]{width:125px}.settings{padding:13px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{transition:none!important;animation:none!important}}
.hero-ptz{grid-column:1/-1;padding:12px 16px;border:1px solid var(--tech-border);border-radius:12px;background:radial-gradient(ellipse at 50% 80%,#17324588,#0c1725 70%);display:flex;flex-direction:column;justify-content:center}.ptz-heading{display:flex;justify-content:space-between;align-items:center;color:#839fba;font-size:11px}.ptz-heading>span{display:flex;align-items:center;gap:7px}.ptz-heading svg{width:15px;height:15px;color:#629da9}.ptz-heading small{font-size:10px;color:#4f6d87}.hero-ptz .dpad{grid-template-columns:repeat(3,42px);gap:4px;margin:8px auto 0;padding:0;border:0;background:none;box-shadow:none}.hero-ptz .dpad button{width:42px;height:31px;min-height:31px;font-size:16px;border-radius:7px;background:#11283a;border-color:#2a4c60}.hero-ptz .dpad button[data-op=stop]{font-size:10px;background:#20505a;color:#9ff0ef;border-color:#3e7c84}@media(max-width:1050px){.summary{grid-template-rows:auto auto auto minmax(118px,1fr)}.hero-ptz{padding:10px 12px}.hero-ptz .dpad button{height:27px;min-height:27px}}@media(max-width:760px){.summary{grid-template-rows:auto}.hero-ptz{display:none}}</style><ha-card><div class="head"><div class="brand"><div class="brand-mark">${techIcon('camera')}</div><div><div class="eyebrow">LOCAL CAMERA CONTROL</div><h2>${escapeHtml(this.config.title||'TP-Link 摄像头')}</h2></div></div><div class="head-actions"><span class="badge">连接中</span><button class="refresh-btn" data-op="refresh" title="刷新状态" aria-label="刷新状态">${techIcon('refresh')}</button></div></div><div class="overview"><div class="feed-frame"><div class="feed-top"><strong>${techIcon('camera')}实时画面</strong><span class="feed-code">LOCAL</span></div><div class="live-holder"><div class="live-error">正在连接实时画面…</div></div><div class="feed-bottom"><span class="signal">本地视频源</span><span class="feed-meta"></span></div></div><div class="summary"></div></div><div class="quick-actions"></div><div class="workspace"><nav class="tabs" aria-label="摄像头设置分类"></nav><section class="settings"><div class="panel-heading"><div class="section-title"><h3 class="group-title">常用</h3><span class="settings-number"></span></div><label class="search-wrap">${techIcon('search')}<input id="control-search" class="search" type="search" placeholder="搜索设置，如：音量、夜视" aria-label="搜索摄像头设置"></label></div><p class="hint">设置自动保存并核验 · 区域与计划需点击保存</p><div class="grid"></div><div class="context-actions"></div><div class="status" role="status"></div></section></div></ha-card>`;
    this.mountLive();
  }
  async mountLive(){
    if(this.liveElement||this.mounting)return;this.mounting=true;
    try{
      const helpers=await window.loadCardHelpers();
      const config=structuredClone(this.config?.live_config||{type:'picture-entity',entity:this.config.entity,camera_view:'live',show_name:false,show_state:false});
      if(config.type==='custom:advanced-camera-card'&&config.live?.controls?.ptz)config.live.controls.ptz.mode='off';
      const element=helpers.createCardElement(config);element.hass=this._hass;
      if(!this.isConnected)return;this.liveElement=element;this.shadowRoot.querySelector('.live-holder').replaceChildren(element);
    }catch{const holder=this.shadowRoot.querySelector('.live-holder');if(holder)holder.innerHTML='<div class="live-error">实时画面暂未加载，请刷新页面。</div>';}
    finally{this.mounting=false;}
  }
  updateSummary(){
    const root=this.shadowRoot;if(!root.querySelector('.summary'))return;
    const d=this.data,states=this._hass?.states||{};
    const privacy=d?.controls?.find(x=>x.key==='privacy')?.value;
    const online=Boolean(d?.online);
    const badge=root.querySelector('.badge');badge.textContent=online?'● 本地在线':'● 连接待恢复';badge.classList.toggle('offline',!online);
    const meta=root.querySelector('.feed-meta');
    const resolution=d?.controls?.find(x=>x.key==='main_resolution')?.value;
    const codec=d?.controls?.find(x=>x.key==='main_encode_type')?.value;
    if(meta)meta.textContent=[codec,resolution?.replace('*',' × ')].filter(Boolean).join(' / ')||'正在读取视频源';
    const signal=root.querySelector('.signal');if(signal)signal.innerHTML=`<span class="feed-dot ${online?'':'offline'}"></span>${online?'本地视频源':'视频源离线'}`;
    const count=root.querySelector('.settings-number');if(count)count.textContent=d?.controls?.length?d.controls.length+' CONTROLS':'';
    const disk=d?.sd?.[0]?Object.values(d.sd[0])[0]:null;
    const html=`<div class="stat"><small>设备连接</small><strong>${online?'在线':'离线'}</strong></div><div class="stat"><small>隐私遮蔽</small><strong>${privacy===true?'已开启':privacy===false?'已关闭':'未知'}</strong></div><div class="stat"><small>控制模式</small><strong>${d?.writable?'已验证固件':'仅查看'}</strong></div><div class="stat"><small>SD 卡</small><strong>${escapeHtml(disk?.status||'未知')}</strong></div>`;
    if(this._summaryHTML!==html){this._summaryHTML=html;root.querySelector('.summary').innerHTML=html;}
    const actions=`<span class="action-label">QUICK ACCESS</span><div class="action-group">${(d?.presets||[]).map(p=>`<button data-preset="${escapeHtml(p.id)}">${techIcon('home')}${escapeHtml(p.name)}</button>`).join('')}<button class="voice" data-group="声音">${techIcon('mic')}声音设置</button></div>`;
    if(this._actionsHTML!==actions){this._actionsHTML=actions;root.querySelector('.quick-actions').innerHTML=actions;}
  }

  updateStatus(text){const element=this.shadowRoot.querySelector('.status');if(element)element.textContent=text||this.message;}
  render(){
    this.ensureShell();this.updateSummary();
    const groups=this.data?(this.config?.compact?['常用','声音','云台位置']:[...new Set(this.data.controls.map(x=>x.group)),'云台位置','区域与计划','隐私区域','设备维护']):[];
    this.shadowRoot.querySelector('.tabs').innerHTML=groups.map(g=>`<button class="${g===this.group?'active':''}" data-group="${g}" aria-pressed="${g===this.group}"><span class="tab-icon">${techIcon(({常用:'sliders',侦测:'shield',报警:'bell',声音:'mic',画面:'image',夜视:'moon',存储:'disk',事件联动:'link',编码:'code',云台位置:'move',区域与计划:'crop',隐私区域:'lock',设备维护:'settings'})[g])}</span><span class="tab-label">${g}</span><span class="tab-count">${this.data.controls.filter(d=>d.group===g).length||''}</span></button>`).join('');
    this.shadowRoot.querySelector('.group-title').textContent=this.filter?'搜索结果':this.group;
    const search=this.shadowRoot.querySelector('#control-search');if(search.value!==this.filter)search.value=this.filter;
    this.renderFields();this.updateStatus();
  }
  renderFields(){
    const d=this.data;if(!d)return;
    const fields=d.controls.filter(x=>this.filter?(x.name+x.key+x.group).toLowerCase().includes(this.filter.toLowerCase()):x.group===this.group);
    let content=fields.map(x=>this.field(x)).join('');
    if(!this.filter&&this.group==='云台位置')content=`<div class="wide"><p class="muted">小幅转动镜头，或保存当前画面为常用位置。最多 8 个位置。</p><div class="dpad"><span></span><button data-op="move" data-direction="up" aria-label="镜头向上">↑</button><span></span><button data-op="move" data-direction="left" aria-label="镜头向左">←</button><button data-op="stop">停止</button><button data-op="move" data-direction="right" aria-label="镜头向右">→</button><span></span><button data-op="move" data-direction="down" aria-label="镜头向下">↓</button></div><div class="presets">${d.presets.map(p=>`<button data-preset="${escapeHtml(p.id)}">${escapeHtml(p.name)} · ${escapeHtml(p.id)}</button>`).join('')}</div><div class="editor"><label>位置编号<select id="preset-id">${Array.from({length:8},(_,i)=>`<option value="${i+1}">${i+1}${d.presets.some(p=>p.id===String(i+1))?' · 已保存':' · 空闲'}</option>`).join('')}</select></label><label>位置名称<input id="preset-name" maxlength="24" placeholder="例如：门口、沙发"></label><button class="primary" data-op="save-preset">保存当前位置</button><button data-op="delete-preset">删除位置</button></div></div>`;
    if(!this.filter&&this.group==='区域与计划')content=this.regionEditor();
    if(!this.filter&&this.group==='隐私区域')content=this.coverEditor();
    if(!this.filter&&this.group==='设备维护'){
      const f=this.firmware||d.firmware;
      content=`<div class="wide"><div class="firmware-box"><strong>${escapeHtml(d.device?.device_model)} · 硬件 V${escapeHtml(d.device?.hw_version)}</strong><br>当前固件 ${escapeHtml(d.device?.sw_version)}<br><span class="muted">${escapeHtml(f?.message||'点击检查官方更新')}${f?.checked_at?'<br>检查时间 '+escapeHtml(new Date(f.checked_at).toLocaleString()):''}</span></div><div class="extra"><button class="primary" data-op="firmware-check">检查官方更新</button><button data-op="system_time">同步时间</button><button data-op="reboot-confirm">重启摄像头</button></div><p class="tip">检查更新不会下载或安装固件。不同硬件版本的固件不能混刷；安装升级、重新配网和账号管理继续使用 TP-Link 物联 App。</p><p class="tip">这款设备不支持光学变焦、自动对焦、雨刷及原厂巡航。</p><a href="https://www.tp-link.com.cn/product_4204.html?v=download" target="_blank" rel="noopener">官方手册与下载</a></div>`;
    }
    this.shadowRoot.querySelector('.grid').innerHTML=content||'<p class="muted">没有匹配的设置。</p>';
    let extra='';
    if(!this.filter&&this.group==='声音')extra=`<p class="tip">半双工对讲：讲话时不同时收听。离开页面或 90 秒后自动结束。</p><div class="extra"><button class="${this.talking?'danger':'primary'}" data-op="talk">${this.talking?'结束对讲':'开始对讲'}</button></div>`;
    if(!this.filter&&this.group==='报警')extra='<div class="extra"><button class="danger" data-op="alarm-start">手动报警 15 秒</button><button data-op="alarm_stop">立即停止报警</button></div>';
    if(!this.filter&&this.group==='编码')extra='<p class="tip">调整编码或分辨率时画面会短暂重连。H.264 对浏览器兼容更好。</p>';
    this.shadowRoot.querySelector('.context-actions').innerHTML=extra;
    this.shadowRoot.querySelector('.group-title').textContent=this.filter?'搜索结果 · '+fields.length:this.group;
    if(!this.filter&&this.group==='区域与计划')this.paint();
    if(!this.filter&&this.group==='隐私区域')this.paintCover();
  }

  regionEditor() {
    const names={people_detection:'人形侦测区域',linecrossing_detection:'越线边界',intrusion_detection:'入侵区域',regionexiting_detection:'离开区域'};
    this.regionModule ||= 'people_detection';this.regionId ||= '1';
    const rows=this.data.regions[this.regionModule]||[];
    const region=rows.map(x=>Object.values(x)[0]).find(x=>x.id===this.regionId);
    if(!this.points || this.loadedRegion!==this.regionModule+this.regionId){this.points=region?Array.from({length:this.regionModule==='linecrossing_detection'?2:4},(_,i)=>[+region[`pt${i+1}_x`],+region[`pt${i+1}_y`]]):[];this.loadedRegion=this.regionModule+this.regionId;this.drawing=false;}
    const image=this._hass.states[this.config.entity]?.attributes?.entity_picture||'';
    const scheduleModule=this.scheduleModule||this.regionModule;
    const schedule=scheduleModule==='record_plan'?this.data.record_schedule:this.data.schedules[scheduleModule]||{};
    const days=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'];
    return `<div class="wide"><div class="editor"><label>编辑区域<select id="region-module">${Object.entries(names).map(([k,v])=>`<option value="${k}" ${k===this.regionModule?'selected':''}>${v}</option>`).join('')}</select></label><label>区域编号<select id="region-id">${rows.map(x=>Object.values(x)[0]).map(x=>`<option value="${x.id}" ${x.id===this.regionId?'selected':''}>${x.id}</option>`).join('')}</select></label><button data-op="redraw">重新绘制</button><button data-op="region-save">保存区域</button></div><p class="tip">${this.regionModule==='linecrossing_detection'?'点击画面上的两个点画线。':'按顺序点击画面上的四个角画区域。'}保存区域不会自动开启侦测。</p><div class="draw">${image?`<img src="${escapeHtml(image)}" alt="摄像头当前画面"><svg viewBox="0 0 10000 10000" preserveAspectRatio="none"></svg>`:'画面暂不可用'}</div><h3>布防与 SD 卡录像时间</h3><select id="schedule-module">${Object.entries({...names,record_plan:'SD 卡录像计划'}).map(([k,v])=>`<option value="${k}" ${k===scheduleModule?'selected':''}>${v}</option>`).join('')}</select><p class="tip">${scheduleModule==='record_plan'?'时段写法：0000-2400:2（全天事件录像）；:1 为连续录像。':'时段写法：0800-1200, 1400-2200；留空表示当天不布防。'}</p><div class="schedule">${days.map((day,i)=>{let slots=[];try{slots=JSON.parse(decodeURIComponent(schedule[day]||'[]'));}catch{}return `<label for="day-${day}">${['周一','周二','周三','周四','周五','周六','周日'][i]}</label><input id="day-${day}" value="${escapeHtml(slots.join(', '))}">`;}).join('')}</div><div class="extra"><button data-op="schedule-save">保存一周计划</button></div></div>`;
  }
  paint(){const svg=this.shadowRoot.querySelector('svg');if(!svg)return;svg.innerHTML=`<polyline points="${this.points.concat(this.points.length===4?[this.points[0]]:[]).map(p=>p.join(',')).join(' ')}" fill="${this.points.length===4?'#39d9ae33':'none'}" stroke="#39d9ae" stroke-width="45"/>${this.points.map((p,i)=>`<circle cx="${p[0]}" cy="${p[1]}" r="85" fill="#ffde67"/><text x="${p[0]+100}" y="${p[1]+100}" fill="#fff" font-size="300">${i+1}</text>`).join('')}`;}
  drawPoint(e){if(this.group==='隐私区域'){this.drawCover(e);return;}const draw=e.target.closest('.draw');if(!draw||!this.drawing)return;const r=draw.getBoundingClientRect();this.points.push([Math.max(0,Math.min(10000,Math.round((e.clientX-r.left)/r.width*10000))),Math.max(0,Math.min(10000,Math.round((e.clientY-r.top)/r.height*10000)))]);if(this.points.length===(this.regionModule==='linecrossing_detection'?2:4))this.drawing=false;this.paint();}
  change(e){const t=e.target;if(t.dataset.key){const d=this.data.controls.find(x=>x.key===t.dataset.key);this.run('set',{key:d.key,value:d.kind==='switch'?t.checked:d.kind==='number'?Number(t.value):t.value});}else if(t.id==='region-module'){this.regionModule=t.value;this.regionId='1';this.render();}else if(t.id==='region-id'){this.regionId=t.value;this.render();}else if(t.id==='schedule-module'){this.scheduleModule=t.value;this.render();}}
  click(e){const b=e.target.closest('button');if(!b)return;if(b.dataset.nav){history.pushState(null,'',b.dataset.nav);window.dispatchEvent(new Event('location-changed'));return;}if(b.dataset.group){this.group=b.dataset.group;this.filter='';this.message='';this.render();return;}if(b.dataset.preset){this.run('preset_goto',{id:b.dataset.preset});return;}const op=b.dataset.op;if(!op)return;
    const value=id=>this.shadowRoot.getElementById(id)?.value;
    if(op==='refresh'){this.message='';this.refresh();}
    else if(op==='firmware-check')this.run('firmware_check',{refresh:true});
    else if(op==='move')this.run(op,{direction:b.dataset.direction});
    else if(op==='save-preset'){const id=value('preset-id');if(this.data.presets.some(p=>p.id===id)&&!confirm('覆盖这个预置位的位置和名称？'))return;this.run('preset_save',{id,name:value('preset-name')});}
    else if(op==='delete-preset'){if(confirm('删除这个预置位？'))this.run('preset_delete',{id:value('preset-id')});}
    else if(op==='alarm-start'){if(confirm('摄像头将发出报警声音或闪光，15 秒后自动停止。现在开始？'))this.run('alarm_start');}
    else if(op==='talk'){this.talking?this.stopTalk():this.startTalk();}
    else if(op==='reboot-confirm'){if(confirm('重启摄像头会短暂中断画面和录像，是否继续？'))this.run('system_reboot');}
    else if(op==='cover-new'){this.coverPoints=[];this.coverDrawing=true;this.message='请在画面上点击矩形的两个对角';this.paintCover();}
    else if(op==='cover-delete'){this.coverBoxes.splice(Number(b.dataset.index),1);this.render();}
    else if(op==='cover-save'){this.run('cover_save',{regions:this.coverBoxes,expected:this.coverExpected});}
    else if(op==='redraw'){this.points=[];this.drawing=true;this.paint();}
    else if(op==='region-save'){this.run('region_save',{module:this.regionModule,id:this.regionId,points:this.points});}
    else if(op==='schedule-save'){const days={};for(const day of ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'])days[day]=value('day-'+day).split(',').map(x=>x.trim()).filter(Boolean);this.run('schedule_save',{module:this.scheduleModule||this.regionModule,days});}
    else this.run(op);
  }
  coverEditor(){
    const raw=this.data.regions.cover||[];
    const expected=raw.map(row=>{const v=Object.values(row)[0];return Object.fromEntries(['x_coor','y_coor','width','height'].map(k=>[k,String(v[k])]))});
    if(!this.coverBoxes||JSON.stringify(this.coverExpected)!==JSON.stringify(expected)){this.coverExpected=expected;this.coverBoxes=expected.map(r=>Object.fromEntries(Object.entries(r).map(([k,v])=>[k,Number(v)])));}
    const image=this._hass.states[this.config.entity]?.attributes?.entity_picture||'';
    return `<div class="wide"><p>最多保存 4 个遮挡矩形。保存后，在“常用”中开启“画面局部遮挡”生效。</p><div class="extra"><button data-op="cover-new" ${this.coverBoxes.length>=4?'disabled':''}>添加矩形</button><button data-op="cover-save">保存遮挡区域</button></div><div class="draw">${image?`<img src="${escapeHtml(image)}" alt="摄像头当前画面"><svg viewBox="0 0 10000 10000" preserveAspectRatio="none"></svg>`:'画面暂不可用'}</div><div class="extra">${this.coverBoxes.map((r,i)=>`<button data-op="cover-delete" data-index="${i}">删除区域 ${i+1}</button>`).join('')}</div></div>`;
  }
  paintCover(){const svg=this.shadowRoot.querySelector('svg');if(svg)svg.innerHTML=(this.coverBoxes||[]).map((r,i)=>`<rect x="${r.x_coor}" y="${r.y_coor}" width="${r.width}" height="${r.height}" fill="#0008" stroke="#ffdc67" stroke-width="35"/><text x="${r.x_coor+70}" y="${r.y_coor+300}" fill="#fff" font-size="260">${i+1}</text>`).join('');}
  drawCover(e){const el=e.target.closest('.draw');if(!el||!this.coverDrawing||this.coverBoxes.length>=4)return;const r=el.getBoundingClientRect();this.coverPoints.push([Math.max(0,Math.min(10000,Math.round((e.clientX-r.left)/r.width*10000))),Math.max(0,Math.min(10000,Math.round((e.clientY-r.top)/r.height*10000)))]);if(this.coverPoints.length===2){const [a,b]=this.coverPoints;this.coverDrawing=false;const box={x_coor:Math.min(a[0],b[0]),y_coor:Math.min(a[1],b[1]),width:Math.abs(a[0]-b[0]),height:Math.abs(a[1]-b[1])};if(box.width&&box.height)this.coverBoxes.push(box);this.render();}}
  async startTalk(){
    if(!this.data?.talk_enabled||!this.data?.writable){this.updateStatus('请先在集成选项中启用实验性对讲');return;}
    if(this.startingTalk)return;this.startingTalk=true;
    try{
      this.media=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,channelCount:1}});
      if(!this.isConnected){this.media.getTracks().forEach(t=>t.stop());return;}
      await this._hass.callWS({type:'tplink_ipc_local/talk',entry_id:this.config.entry_id,operation:'start'});
      if(!this.isConnected||document.hidden){await this.stopTalk();return;}
      this.audioContext=new AudioContext();await this.audioContext.resume();
      const worklet=`class CameraAudio extends AudioWorkletProcessor{constructor(){super();this.buffer=[];this.phase=0;}alaw(x){let n=Math.max(-32768,Math.min(32767,Math.round(x*32767)));let mask=n>=0?213:85;if(n<0)n=-n-1;let seg=0;for(let v=n>>8;v;v>>=1)seg++;if(seg>7)seg=7;let a=seg<<4;a|=seg<2?(n>>4)&15:(n>>(seg+3))&15;return a^mask;}process(inputs){const input=inputs[0]?.[0];if(!input)return true;for(let i=0;i<input.length;i++){this.phase+=8000;if(this.phase>=sampleRate){this.phase-=sampleRate;this.buffer.push(this.alaw(input[i]));if(this.buffer.length===1600){this.port.postMessage(new Uint8Array(this.buffer));this.buffer=[];}}}return true;}}registerProcessor('camera-audio',CameraAudio);`;
      const url=URL.createObjectURL(new Blob([worklet],{type:'application/javascript'}));try{await this.audioContext.audioWorklet.addModule(url);}finally{URL.revokeObjectURL(url);}
      this.audioNode=new AudioWorkletNode(this.audioContext,'camera-audio');this.audioSource=this.audioContext.createMediaStreamSource(this.media);this.audioSource.connect(this.audioNode);const gain=this.audioContext.createGain();gain.gain.value=0;this.audioNode.connect(gain).connect(this.audioContext.destination);
      this.pendingAudio=0;this.talking=true;
      this.audioNode.port.onmessage=async e=>{if(!this.talking)return;if(this.pendingAudio>=2){this.message='网络延迟过高，对讲已停止';await this.stopTalk();return;}this.pendingAudio++;try{await this._hass.callWS({type:'tplink_ipc_local/talk',entry_id:this.config.entry_id,operation:'audio',audio:btoa(String.fromCharCode(...e.data))});}catch{this.message='对讲连接中断';await this.stopTalk();}finally{this.pendingAudio--;}};
      this.talkTimer=setTimeout(()=>this.stopTalk(),90000);this.message='对讲已开始，声音将发送到所选摄像头';this.render();
    }catch(e){this.message=e.message||'无法启动对讲，请检查麦克风权限';await this.stopTalk();}
    finally{this.startingTalk=false;}
  }
  async stopTalk(){
    const active=this.talking||this.media;this.talking=false;clearTimeout(this.talkTimer);
    this.media?.getTracks().forEach(t=>t.stop());this.media=null;this.audioSource?.disconnect();this.audioNode?.disconnect();
    if(this.audioContext){await this.audioContext.close().catch(()=>{});this.audioContext=null;}
    if(active&&this._hass)try{await this._hass.callWS({type:'tplink_ipc_local/talk',entry_id:this.config.entry_id,operation:'stop'});}catch{}
    if(this.isConnected)this.render();
  }
}
if(!customElements.get('tplink-ipc-controls'))customElements.define('tplink-ipc-controls',TplinkIpcControls);
window.customCards=window.customCards||[];window.customCards.push({type:'tplink-ipc-controls',name:'TP-Link IPC Local Controls',description:'TL-IPC4ADW 的画面、声音、云台、侦测、区域和计划控制。'});
