"""
Interactive features for the drawing set:
  - price overlay toggle (list price on every selected part, plans and schedules)
  - budget mode (+/- N % ranges everywhere) and the budget builder sheet (AV-702)
  - 3D model sheet (V-801): room render with the Chicagoland Home Theater logo on
    the screen, slow turntable spin, video / still export via the downloads capability.

Everything here renders from design.json, so prices, positions and products match
the drawings and schedules. Only list price (MSRP) is used; dealer cost never
enters the page.
"""
import html
import json

BRAND = "Chicagoland Home Theater"


def e(s):
    return html.escape(str(s), quote=True)


def price_span(v, cls="price"):
    """A price placeholder the page script fills in (exact or budget range); hidden until 'Show prices'."""
    if v is None:
        return '<span class="na">-</span>'
    return f'<span class="{cls}" data-v="{float(v):.2f}"></span>'


def svg_price(x, y, v, anchor="middle"):
    if v is None:
        return ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="price pricechip" text-anchor="{anchor}" '
            f'data-v="{float(v):.2f}"></text>')


def model_prices(D):
    out = {}
    for b in D["bom"]:
        if b.get("msrp") is not None:
            out[b["model"]] = b["msrp"]
    return out


# Budget categories: group every package BOM line into client-facing categories
def category_of(b):
    role, sku = b["role"], (b.get("sku") or "")
    if role in ("Loudspeakers", "Brackets", "Subwoofers", "Processing", "Amplification"):
        return "audio"
    if role == "Video":
        return "video"
    if role == "Sources / control / power":
        if sku.startswith("K0") or sku.startswith("KPROMO"):
            return "video"
        if sku.startswith(("PKG-", "ITP-", "REM-", "SHR-", "SVR-", "SSC-")):
            return "control"
        return "power"
    return None


CATEGORIES = [
    ("audio", "Audio", "Loudspeakers, subwoofers, brackets, processor, amplification"),
    ("video", "Video", "Projector, movie server / player, plus screen allowance"),
    ("control", "Control", "Savant host, remote, touch screen"),
    ("power", "Power", "Surge protection and power conditioning"),
    ("seating", "Seating", "Theater recliners (allowance per seat)"),
    ("acoustics", "Acoustic treatment", "Panels, cloud, bass traps, diffusion (allowance)"),
    ("infra", "Infrastructure", "Speaker wire, rack, ventilation, conduit (allowance)"),
    ("labor", "Labor & calibration", "Pre-wire, trim-out, programming, calibration (allowance)"),
]

ALLOWANCES = [  # (key, category, label, unit multiplier source)
    ("screen", "video", "AT screen, 120in 16:9 fixed frame", 1),
    ("seat", "seating", "Recliner, per seat", "seats"),
    ("acoustics", "acoustics", "Acoustic treatment package", 1),
    ("infra", "infra", "Wire, rack and infrastructure", 1),
    ("labor", "labor", "Labor, programming and calibration", 1),
]


def toolbar():
    return ('<div class="pricebar" role="group" aria-label="Pricing display">'
            '<button type="button" id="btn-prices" aria-pressed="false">Show prices</button>'
            '<button type="button" id="btn-budget" aria-pressed="false">Budget ranges</button>'
            '<label class="pct" for="budget-pct">&plusmn;</label>'
            '<input id="budget-pct" type="number" min="0" max="50" step="1" value="10" inputmode="numeric" aria-label="Budget range percent">'
            '<span class="pctlab">%</span>'
            '<span class="pricestate" id="pricestate" aria-live="polite">Prices hidden</span></div>')


def sheet_budget(D, html_sheet):
    opt = D["options"]
    data = {"tiers": [{"id": t, "label": s["label"], "lines": [
        {"cat": category_of(b), "desc": b["desc"], "qty": b["qty"], "ext": b.get("ext_msrp")}
        for b in s["bom"] if b.get("sku") and category_of(b)]} for t, s in opt.items()],
        "drawn": D["tier"], "seats": len(D["seating"]["seats"]),
        "categories": [{"key": k, "label": l, "desc": d} for k, l, d in CATEGORIES],
        "allowances": [{"key": k, "cat": c, "label": l, "per": p} for k, c, l, p in ALLOWANCES]}
    tier_opts = "".join(f'<option value="{e(t)}"{" selected" if t == D["tier"] else ""}>{e(s["label"])}</option>'
                        for t, s in opt.items())
    allow = "".join(
        f'<div class="allow"><label for="al-{k}">{e(l)}{" (x " + str(len(D["seating"]["seats"])) + " seats)" if p == "seats" else ""}</label>'
        f'<div class="ain"><span>$</span><input id="al-{k}" data-key="{k}" type="number" min="0" step="100" inputmode="decimal" placeholder="enter allowance"></div></div>'
        for k, c, l, p in ALLOWANCES)
    body = (f'<div class="budget">'
            f'<div class="bcontrols"><label for="bud-tier">Package</label><select id="bud-tier">{tier_opts}</select>'
            f'<label for="bud-pct">Range &plusmn;</label><input id="bud-pct" type="number" min="0" max="50" step="1" value="10" inputmode="numeric">'
            f'<span class="pctlab">%</span></div>'
            f'<div class="g2"><div class="cell wide"><div class="tw"><table class="budt" id="budtable"><thead><tr>'
            f'<th>Category</th><th>Includes</th><th class="r">Estimate</th><th class="r">Low</th><th class="r">High</th><th>Share</th>'
            f'</tr></thead><tbody></tbody><tfoot></tfoot></table></div>'
            f'<p class="fine">Equipment estimates are list prices (MSRP) from the {e(D.get("price_source") or "Savant price list")} '
            f'for the selected package. Seating, screen, treatment, infrastructure and labor are not on the Savant list: enter your '
            f'allowances below and they are added to their category. Low / High apply the range to every category. '
            f'Allowances are remembered in this browser only.</p></div>'
            f'<div class="cell wide"><h3>Allowances (not on the Savant list)</h3><div class="allows">{allow}</div></div></div>'
            f'<script type="application/json" id="budgetdata">{json.dumps(data)}</script></div>')
    return html_sheet("AV-702", "Budget builder", body)


def sheet_3d(D, html_sheet):
    S = D["seating"]
    sc = D["screen"]
    sm = D["subs"]
    chosen = next(o for o in sm["options"] if o["id"] == sm["chosen_id"])
    mp = model_prices(D)
    cat = D["catalog"]
    chans = [{"ch": c["ch"], "model": c["model"], "pos": c["pos"], "mount": c["mount"],
              "wh": cat[c["model"]].get("grille_wh", [0.25, 0.4]), "price": mp.get(c["model"])} for c in D["channels"]]
    data = {"W": D["room"]["W"], "L": D["room"]["L"], "H": D["room"]["H"], "brand": BRAND,
            "screen": {"x0": sc["x0"], "x1": sc["x1"], "zb": sc["zb"], "zt": sc["zt"], "y": sc["y"]},
            "seats": [{"id": s["id"], "x": s["x"], "y": s["y"], "floor": s["floor"]} for s in S["seats"]],
            "riser": {"front": S["riser_front"], "back": S["riser_back"], "x1": S["riser_x1"], "h": S["riser"]},
            "chans": chans,
            "subs": [{"pos": p, "wall": w, "wh": sm["grille_wh"], "model": sm["model"], "price": mp.get(sm["model"])}
                     for p, w in zip(chosen["units"], chosen["walls"])],
            "projector": {"lens": D["projector"]["lens"], "model": D["projector"]["model"], "price": mp.get(D["projector"]["model"])},
            "zones": D["treatment_zones"], "door": [D["inputs"]["door"]["x0"], D["inputs"]["door"]["width"]],
            "title": f"{D['package']['label']} package: Dolby Atmos {D['layout']}"}
    body = (f'<div class="v3d">'
            f'<div class="v3controls">'
            f'<button type="button" id="v3-spin" aria-pressed="false">Spin</button>'
            f'<label for="v3-dur">Export length</label><select id="v3-dur"><option value="20">20 s</option>'
            f'<option value="30" selected>30 s (slow)</option><option value="45">45 s (very slow)</option></select>'
            f'<button type="button" id="v3-rec" class="dl">Export spin video</button>'
            f'<button type="button" id="v3-png" class="dl">Save still image</button>'
            f'<label class="file" for="v3-logo">Use our logo file</label><input type="file" id="v3-logo" accept="image/png,image/jpeg,image/svg+xml,image/webp">'
            f'<button type="button" id="v3-logo-reset">Default logo</button>'
            f'<span class="v3status" id="v3-status" aria-live="polite"></span></div>'
            f'<div class="v3stage" id="v3-stage"><canvas id="v3-canvas" width="1920" height="1080" aria-label="3D model of the theater"></canvas>'
            f'<div class="v3labels" id="v3-labels" aria-hidden="true"></div>'
            f'<div class="v3fallback" id="v3-fallback" hidden>The 3D view needs WebGL, which this browser has turned off.</div></div>'
            f'<p class="fine">Drag to orbit, scroll or pinch to zoom. The screen always shows the {BRAND} logo; load your own logo file '
            f'(PNG or SVG) to replace the wordmark. It is kept in this browser only. With Show prices on, each part is labelled with its '
            f'model and list price. Exports save after you confirm. Labels are not part of the exported video.</p>'
            f'<script type="application/json" id="v3data">{json.dumps(data, default=list)}</script></div>')
    return html_sheet("V-801", "3D model and client spin", body)


CSS3 = r"""
.topbar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--paper2);padding-block:8px}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:10;background:var(--paper2)}
.pricebar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.pricebar button,.v3controls button,.v3controls select,.bcontrols select,.bcontrols input,.pricebar input,.allow input,.v3controls .file{
  font:inherit;font-size:13.5px;color:var(--ink);background:var(--paper);border:1px solid var(--ink3);padding:6px 10px;border-radius:2px;cursor:pointer}
.pricebar input,.bcontrols input{width:4.2em;cursor:text}
.pricebar button[aria-pressed="true"],.v3controls button[aria-pressed="true"]{background:var(--accent);color:#14263b;border-color:var(--accent)}
.pricebar button:focus-visible,.v3controls button:focus-visible,.v3controls select:focus-visible,.bcontrols select:focus-visible,
.bcontrols input:focus-visible,.pricebar input:focus-visible,.allow input:focus-visible,.v3controls input:focus-visible+.file{outline:2px solid var(--accent);outline-offset:2px}
.pricebar .pct,.pricebar .pctlab,.bcontrols .pctlab{font-family:var(--f-mono);font-size:13px;color:var(--ink2)}
.pricestate{font-family:var(--f-mono);font-size:11.5px;color:var(--ink2);letter-spacing:.06em}
body:not(.show-prices) .price,body:not(.show-prices) .pcol{display:none}
body:not(.show-prices) svg .price{display:none}
body.show-prices .noprice{display:none}
.noprice{color:var(--ink3);font-style:italic}
.price{color:var(--accent);font-variant-numeric:tabular-nums;white-space:nowrap}
svg text.pricechip{fill:var(--accent);font-size:11px;font-weight:600}
.budget{display:flex;flex-direction:column;gap:14px}
.bcontrols{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.bcontrols label{font-family:var(--f-mono);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2)}
table.budt td{white-space:normal} table.budt .r{text-align:right;font-family:var(--f-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
table.budt td.inc{color:var(--ink2);font-size:12px} table.budt tfoot td{font-weight:600;border-top:1px solid var(--ink)}
.bar{height:8px;background:var(--accent);border-radius:1px;min-width:1px}
.barcell{min-width:120px}
.todo{color:var(--no);font-size:11.5px;font-family:var(--f-mono)}
.allows{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:10px 18px}
.allow{display:flex;flex-direction:column;gap:4px;min-width:0}
.allow label{font-size:13px;color:var(--ink2)}
.ain{display:flex;align-items:center;gap:6px}.ain span{font-family:var(--f-mono);color:var(--ink2)}
.allow input{width:100%;cursor:text}
.v3d{display:flex;flex-direction:column;gap:12px}
.v3controls{display:flex;flex-wrap:wrap;gap:8px 10px;align-items:center}
.v3controls label:not(.file){font-family:var(--f-mono);font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2)}
.v3controls input[type=file]{position:absolute;width:1px;height:1px;opacity:0}
.v3status{font-family:var(--f-mono);font-size:12px;color:var(--ink2)}
.v3stage{position:relative;width:100%;aspect-ratio:16/9;max-width:100%;background:#05101c;border:1px solid var(--ink3);overflow:hidden}
#v3-canvas{width:100%;height:100%;display:block;touch-action:none}
.v3labels{position:absolute;inset:0;pointer-events:none}
.v3lab{position:absolute;transform:translate(-50%,-120%);background:rgba(8,22,38,.86);border:1px solid var(--accent);color:var(--ink);
  font-family:var(--f-mono);font-size:11px;padding:2px 6px;border-radius:2px;white-space:nowrap}
.v3lab b{color:var(--accent);font-weight:600}
.v3fallback[hidden]{display:none}
.v3fallback{position:absolute;inset:0;display:grid;place-items:center;color:var(--ink2);padding:16px;text-align:center}
@media print{.pricebar,.v3controls,.bcontrols{display:none}}
"""


FEATURES_JS = r"""
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.147.0/examples/js/controls/OrbitControls.js"></script>
<script>
(function(){
  // ---------------- price overlay + budget mode ----------------
  var store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  var st={show:store.get('cht.showPrices')==='1', budget:store.get('cht.budget')==='1', pct:+(store.get('cht.pct')||10)};
  var bP=document.getElementById('btn-prices'), bB=document.getElementById('btn-budget'), pIn=document.getElementById('budget-pct'), stEl=document.getElementById('pricestate');
  function money(v){return '$'+Math.round(v).toLocaleString('en-US')}
  function fmt(v){ if(!st.budget) return money(v); var k=st.pct/100; return money(v*(1-k))+'–'+money(v*(1+k)); }
  window.CHTprice={fmt:fmt,state:st,money:money};
  function apply(){
    document.body.classList.toggle('show-prices',st.show);
    bP.setAttribute('aria-pressed',st.show?'true':'false'); bP.textContent=st.show?'Hide prices':'Show prices';
    bB.setAttribute('aria-pressed',st.budget?'true':'false');
    pIn.value=st.pct;
    document.querySelectorAll('.price').forEach(function(n){ n.textContent=fmt(+n.dataset.v); });
    stEl.textContent=!st.show?'Prices hidden':(st.budget?'Budget ranges ±'+st.pct+'% (list price)':'List price (MSRP)');
    document.dispatchEvent(new CustomEvent('cht-prices'));
  }
  bP.addEventListener('click',function(){st.show=!st.show; store.set('cht.showPrices',st.show?'1':'0'); apply();});
  bB.addEventListener('click',function(){st.budget=!st.budget; if(st.budget)st.show=true; store.set('cht.budget',st.budget?'1':'0'); store.set('cht.showPrices',st.show?'1':'0'); apply();});
  pIn.addEventListener('input',function(){var v=Math.max(0,Math.min(50,+pIn.value||0)); st.pct=v; store.set('cht.pct',String(v)); apply(); syncBudgetPct();});
  apply();

  // ---------------- budget builder ----------------
  var bd=document.getElementById('budgetdata');
  function syncBudgetPct(){var b=document.getElementById('bud-pct'); if(b&&+b.value!==st.pct){b.value=st.pct; renderBudget();}}
  function renderBudget(){}
  if(bd){
    var B=JSON.parse(bd.textContent), selT=document.getElementById('bud-tier'), pct=document.getElementById('bud-pct');
    var tbody=document.querySelector('#budtable tbody'), tfoot=document.querySelector('#budtable tfoot');
    pct.value=st.pct;
    var allowIn=Array.prototype.slice.call(document.querySelectorAll('.allow input'));
    allowIn.forEach(function(i){var v=store.get('cht.allow.'+i.dataset.key); if(v)i.value=v;
      i.addEventListener('input',function(){store.set('cht.allow.'+i.dataset.key,i.value); renderBudget();});});
    renderBudget=function(){
      var tier=B.tiers.filter(function(t){return t.id===selT.value})[0], k=(+pct.value||0)/100, tot={}, missing={};
      B.categories.forEach(function(c){tot[c.key]=0;});
      tier.lines.forEach(function(l){ if(l.ext!=null) tot[l.cat]+=l.ext; });
      B.allowances.forEach(function(a){ var i=document.getElementById('al-'+a.key), v=parseFloat(i.value);
        if(isFinite(v)&&v>0){ tot[a.cat]+=v*(a.per==='seats'?B.seats:1); } else { missing[a.cat]=true; } });
      var grand=0; B.categories.forEach(function(c){grand+=tot[c.key];});
      tbody.innerHTML='';
      B.categories.forEach(function(c){var v=tot[c.key], tr=document.createElement('tr');
        var share=grand>0?v/grand:0;
        tr.innerHTML='<td><b></b></td><td class="inc"></td><td class="r"></td><td class="r"></td><td class="r"></td><td class="barcell"><div class="bar"></div></td>';
        tr.children[0].firstChild.textContent=c.label; tr.children[1].textContent=c.desc;
        if(missing[c.key]&&v===0){ tr.children[2].innerHTML='<span class="todo">enter allowance</span>'; }
        else { tr.children[2].textContent=money(v); tr.children[3].textContent=money(v*(1-k)); tr.children[4].textContent=money(v*(1+k));
          if(missing[c.key]) tr.children[1].insertAdjacentHTML('beforeend',' <span class="todo">(allowance not entered)</span>'); }
        tr.children[5].firstChild.style.width=(share*100).toFixed(1)+'%';
        tbody.appendChild(tr);});
      tfoot.innerHTML='<tr><td>Total</td><td class="inc"></td><td class="r"></td><td class="r"></td><td class="r"></td><td></td></tr>';
      var f=tfoot.firstChild.children; f[1].textContent=tier.label+' package, ±'+(+pct.value||0)+'%';
      f[2].textContent=money(grand); f[3].textContent=money(grand*(1-k)); f[4].textContent=money(grand*(1+k));
    };
    selT.addEventListener('change',renderBudget);
    pct.addEventListener('input',function(){var v=Math.max(0,Math.min(50,+pct.value||0)); st.pct=v; store.set('cht.pct',String(v)); apply(); renderBudget();});
    renderBudget();
  }

  // ---------------- 3D model ----------------
  var v3=document.getElementById('v3data'); if(!v3) return;
  var M=JSON.parse(v3.textContent), cv=document.getElementById('v3-canvas'), stage=document.getElementById('v3-stage');
  var status=document.getElementById('v3-status'), labelsEl=document.getElementById('v3-labels');
  if(typeof THREE==='undefined'){ document.getElementById('v3-fallback').hidden=false; document.getElementById('v3-fallback').textContent='The 3D library did not load. Check your connection and reload.'; return; }
  var renderer;
  try{ renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true,preserveDrawingBuffer:true}); }
  catch(err){ document.getElementById('v3-fallback').hidden=false; return; }
  renderer.setPixelRatio(1); renderer.setSize(1920,1080,false);
  renderer.outputEncoding=THREE.sRGBEncoding;
  var W=M.W,L=M.L,H=M.H, scene=new THREE.Scene(); scene.background=new THREE.Color(0x07121f);
  function P(x,y,z){return new THREE.Vector3(x,z,y);} // room (x,y,z) -> three (x, up, depth)
  var cam=new THREE.PerspectiveCamera(38,16/9,0.1,200), target=P(W/2,L/2,0.6);
  var ctr=new THREE.OrbitControls(cam,cv); ctr.target.copy(target); ctr.enableDamping=true; ctr.maxPolarAngle=Math.PI*0.49; ctr.minDistance=4; ctr.maxDistance=30;
  var R0=Math.hypot(W,L)*1.05, EL=0.62, ang0=0.55;
  function camAt(a){ var r=R0; cam.position.set(target.x+r*Math.sin(a)*Math.cos(EL), target.y+r*Math.sin(EL), target.z+r*Math.cos(a)*Math.cos(EL)); cam.lookAt(target); }
  camAt(ang0); ctr.update();
  scene.add(new THREE.HemisphereLight(0xbcd2ff,0x140c0c,0.32));
  var key=new THREE.DirectionalLight(0xfff2e0,0.5); key.position.set(W*0.2,H*4,L*1.2); scene.add(key);
  var fill=new THREE.PointLight(0xffc98a,0.9,14); fill.position.copy(P(W/2,L*0.6,H-0.3)); scene.add(fill);
  function mat(c,o){return new THREE.MeshStandardMaterial(Object.assign({color:c,roughness:0.85,metalness:0.0},o||{}));}
  function wp(wall,u,zc,w,h,m,inset){ // one-sided panel facing into the room: hidden whenever its wall is cut away
    var g=new THREE.Mesh(new THREE.PlaneGeometry(w,h),m), i=inset||0.01;
    if(wall==='front'){g.position.set(u,zc,i);}
    else if(wall==='back'){g.rotation.y=Math.PI; g.position.set(u,zc,L-i);}
    else if(wall==='left'){g.rotation.y=Math.PI/2; g.position.set(i,zc,u);}
    else {g.rotation.y=-Math.PI/2; g.position.set(W-i,zc,u);}
    scene.add(g); return g; }
  function box(w,h,d,m,x,y,z){var g=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),m); g.position.set(x,y,z); scene.add(g); return g;}
  // room shell: back-faces only -> automatic cutaway of the walls nearest the camera
  var wallM=mat(0x141a28,{side:THREE.BackSide});
  var shell=new THREE.Mesh(new THREE.BoxGeometry(W,H,L), [wallM,wallM,mat(0x151a26,{side:THREE.BackSide}),mat(0x1d1a20,{side:THREE.BackSide}),wallM,mat(0x0e1016,{side:THREE.BackSide})]);
  shell.position.set(W/2,H/2,L/2); scene.add(shell);
  // carpet floor (always visible)
  var floor=new THREE.Mesh(new THREE.PlaneGeometry(W,L),mat(0x1d1a20,{roughness:0.95})); floor.rotation.x=-Math.PI/2; floor.position.set(W/2,0.002,L/2); scene.add(floor);
  // riser + step lights
  var r=M.riser; box(r.x1,r.h,r.back-r.front,mat(0x231c22,{roughness:0.95}),r.x1/2,r.h/2,(r.front+r.back)/2);
  var stepL=new THREE.Mesh(new THREE.BoxGeometry(r.x1,0.02,0.02),new THREE.MeshBasicMaterial({color:0xffc46b})); stepL.position.set(r.x1/2,0.05,r.front+0.012); scene.add(stepL);
  // AT front wall fabric (slightly see-through so the LCR read)
  var fab=new THREE.Mesh(new THREE.PlaneGeometry(W,H),mat(0x0d0f14,{transparent:true,opacity:0.78})); fab.position.set(W/2,H/2,M.screen.y-0.02); scene.add(fab);
  // logo texture on the screen
  var lc=document.createElement('canvas'); lc.width=2048; lc.height=1152; var lx=lc.getContext('2d');
  var logoImg=null;
  function drawLogo(){
    var g=lx.createLinearGradient(0,0,0,1152); g.addColorStop(0,'#0b1c30'); g.addColorStop(1,'#050b14'); lx.fillStyle=g; lx.fillRect(0,0,2048,1152);
    if(logoImg){ var s=Math.min(1600/logoImg.width,800/logoImg.height); var w=logoImg.width*s,h=logoImg.height*s; lx.drawImage(logoImg,(2048-w)/2,(1152-h)/2,w,h); }
    else {
      var disp='"Barlow Condensed","Arial Narrow",Arial,sans-serif';
      lx.fillStyle='#ffd166'; lx.textAlign='center'; lx.textBaseline='alphabetic';
      lx.font='700 360px '+disp; lx.fillText('CHT',1024,560);
      lx.fillStyle='#e9f2fb'; lx.font='600 96px '+disp;
      var t='CHICAGOLAND HOME THEATER', sp=14, wsum=0, i; for(i=0;i<t.length;i++)wsum+=lx.measureText(t[i]).width+sp; wsum-=sp;
      var x=1024-wsum/2; lx.textAlign='left'; for(i=0;i<t.length;i++){lx.fillText(t[i],x,760); x+=lx.measureText(t[i]).width+sp;}
      lx.fillStyle='#ffd166'; lx.fillRect(1024-260,820,520,6);
    }
    tex.needsUpdate=true; if(typeof dirty!=='undefined') dirty=true;
  }
  var tex=new THREE.CanvasTexture(lc); tex.encoding=THREE.sRGBEncoding; tex.anisotropy=8;
  var s=M.screen, sw=s.x1-s.x0, sh=s.zt-s.zb;
  var scr=new THREE.Mesh(new THREE.PlaneGeometry(sw,sh),new THREE.MeshBasicMaterial({map:tex,toneMapped:false}));
  scr.position.set((s.x0+s.x1)/2,(s.zb+s.zt)/2,s.y); scene.add(scr);
  var fr=new THREE.Mesh(new THREE.PlaneGeometry(sw+0.16,sh+0.16),mat(0x050608)); fr.position.set((s.x0+s.x1)/2,(s.zb+s.zt)/2,s.y-0.01); scene.add(fr);
  var screenLight=new THREE.PointLight(0x9fc4ff,0.8,9); screenLight.position.set((s.x0+s.x1)/2,(s.zb+s.zt)/2,s.y+1.2); scene.add(screenLight);
  // seats
  var leather=mat(0x121317,{roughness:0.45}), armM=mat(0x18191e,{roughness:0.45});
  M.seats.forEach(function(st){ var y0=st.floor, x=st.x, z=st.y;
    box(0.80,0.42,0.80,leather,x,y0+0.21,z-0.30);
    box(0.80,0.62,0.16,leather,x,y0+0.62,z+0.12).rotation.x=-0.18;
    box(0.11,0.62,0.86,armM,x-0.345,y0+0.31,z-0.28); box(0.11,0.62,0.86,armM,x+0.345,y0+0.31,z-0.28);
  });
  // speakers / subs / projector
  var grille=mat(0x2b2f36,{roughness:0.5}), accent=mat(0xc9ced6,{roughness:0.5});
  var labels=[];
  function addLabel(pos,txt,price){ var d=document.createElement('div'); d.className='v3lab'; labelsEl.appendChild(d); labels.push({p:pos,el:d,txt:txt,price:price}); }
  M.chans.forEach(function(c){ var p=c.pos, w=c.wh[0], h=c.wh[1], m, pos;
    if(c.mount.indexOf('Front')===0){ m=wp('front',p[0],p[2],w,h,grille,0.03); pos=P(p[0],0.02,p[2]+h/2); }
    else if(c.mount==='Left wall'){ m=wp('left',p[1],p[2],w,h,grille,0.03); pos=P(0.02,p[1],p[2]+h/2); }
    else if(c.mount==='Right wall'){ m=wp('right',p[1],p[2],w,h,grille,0.03); pos=P(W-0.02,p[1],p[2]+h/2); }
    else if(c.mount==='Back wall'){ m=wp('back',p[0],p[2],w,h,grille,0.03); pos=P(p[0],L-0.02,p[2]+h/2); }
    else { m=box(w,0.03,h,accent,p[0],H-0.02,p[1]); pos=P(p[0],p[1],H); }
    addLabel(pos,c.ch+' · '+c.model,c.price); });
  M.subs.forEach(function(sb,i){ var p=sb.pos, w=sb.wh[0], h=sb.wh[1], zc=0.15+h/2, pos;
    var sm=mat(0x1f2228,{roughness:0.55});
    var u=(sb.wall==='left'||sb.wall==='right')?p[1]:p[0]; wp(sb.wall,u,zc,w,h,sm,0.035);
    pos=sb.wall==='left'?P(0.02,p[1],zc+h/2):sb.wall==='right'?P(W-0.02,p[1],zc+h/2):sb.wall==='front'?P(p[0],0.02,zc+h/2):P(p[0],L-0.02,zc+h/2);
    addLabel(pos,'SW'+(i+1)+' · '+sb.model,sb.price); });
  var lens=M.projector.lens; box(0.50,0.22,0.50,mat(0x101114,{roughness:0.4}),lens[0],lens[2],lens[1]+0.25);
  box(0.04,H-lens[2]-0.11,0.04,mat(0x6b7280),lens[0],(H+lens[2]+0.11)/2,lens[1]+0.25);
  addLabel(P(lens[0],lens[1]+0.25,lens[2]+0.2),'Projector · '+M.projector.model,M.projector.price);
  // projected beam (faint)
  var bg=new THREE.BufferGeometry(), A=[lens[0],lens[2],lens[1]], corners=[[s.x0,s.zb],[s.x1,s.zb],[s.x1,s.zt],[s.x0,s.zt]], vts=[];
  for(var i=0;i<4;i++){var a=corners[i],b=corners[(i+1)%4]; vts.push(A[0],A[1],A[2], a[0],a[1],s.y+0.01, b[0],b[1],s.y+0.01);}
  bg.setAttribute('position',new THREE.Float32BufferAttribute(vts,3)); bg.computeVertexNormals();
  scene.add(new THREE.Mesh(bg,new THREE.MeshBasicMaterial({color:0x9fd0ff,transparent:true,opacity:0.05,side:THREE.DoubleSide,depthWrite:false})));
  // acoustic treatment zones
  var panel=mat(0x232a3d,{roughness:0.95}), Z=M.zones;
  wp('left',(Z.left.y0+Z.left.y1)/2,(Z.left.z0+Z.left.z1)/2,Z.left.y1-Z.left.y0,Z.left.z1-Z.left.z0,panel,0.02);
  wp('right',(Z.right.y0+Z.right.y1)/2,(Z.right.z0+Z.right.z1)/2,Z.right.y1-Z.right.y0,Z.right.z1-Z.right.z0,panel,0.02);
  wp('back',W/4,H/2,W/2,H*0.8,mat(0x1d2433,{roughness:0.9}),0.02);
  wp('back',M.door[0]+M.door[1]/2,1.05,M.door[1],2.1,mat(0x3a2c26),0.025);
  drawLogo();
  if(document.fonts&&document.fonts.ready) document.fonts.ready.then(function(){ if(!logoImg) drawLogo(); });
  try{ var saved=store.get('cht.logo'); if(saved){ var im=new Image(); im.onload=function(){logoImg=im; drawLogo();}; im.src=saved; } }catch(e){}
  document.getElementById('v3-logo').addEventListener('change',function(ev){ var f=ev.target.files&&ev.target.files[0]; if(!f)return;
    var rd=new FileReader(); rd.onload=function(){ var im=new Image(); im.onload=function(){ logoImg=im; drawLogo(); store.set('cht.logo',rd.result); status.textContent='Logo loaded.'; }; im.onerror=function(){status.textContent='That file could not be read as an image.';}; im.src=rd.result; }; rd.readAsDataURL(f); });
  document.getElementById('v3-logo-reset').addEventListener('click',function(){ logoImg=null; try{localStorage.removeItem('cht.logo')}catch(e){} drawLogo(); status.textContent='Default wordmark restored.'; });
  // labels
  function updateLabels(){ var show=document.body.classList.contains('show-prices'), rect=stage.getBoundingClientRect();
    labels.forEach(function(l){ if(!show){l.el.style.display='none';return;} var v=l.p.clone().project(cam);
      if(v.z>1||v.x<-1.1||v.x>1.1||v.y<-1.1||v.y>1.1){l.el.style.display='none';return;}
      l.el.style.display='block'; l.el.style.left=((v.x+1)/2*rect.width)+'px'; l.el.style.top=((1-v.y)/2*rect.height)+'px';
      l.el.innerHTML=''; l.el.appendChild(document.createTextNode(l.txt+' ')); var b=document.createElement('b'); b.textContent=l.price!=null?window.CHTprice.fmt(l.price):'-'; l.el.appendChild(b); }); }
  document.addEventListener('cht-prices',updateLabels);
  // spin + render loop
  var spinning=false, period=40, last=performance.now(), recording=false, spinBtn=document.getElementById('v3-spin');
  function setAngle(a){ var dx=cam.position.x-target.x, dz=cam.position.z-target.z, r=Math.hypot(dx,dz), y=cam.position.y; cam.position.set(target.x+r*Math.sin(a), y, target.z+r*Math.cos(a)); cam.lookAt(target); }
  function curAngle(){ return Math.atan2(cam.position.x-target.x, cam.position.z-target.z); }
  spinBtn.addEventListener('click',function(){ spinning=!spinning; spinBtn.setAttribute('aria-pressed',spinning?'true':'false'); spinBtn.textContent=spinning?'Stop spin':'Spin'; });
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var dirty=true, visible=true;
  if('IntersectionObserver' in window){ new IntersectionObserver(function(es){ visible=es[0].isIntersecting; if(visible)dirty=true; }).observe(stage); }
  ctr.addEventListener('change',function(){dirty=true;});
  document.addEventListener('cht-prices',function(){dirty=true;});
  window.addEventListener('resize',function(){dirty=true;});
  function loop(now){ var dt=Math.min((now-last)/1000,0.1); last=now;
    if(visible&&!recording){
      if(spinning&&!reduce){ setAngle(curAngle()+dt*2*Math.PI/period); dirty=true; }
      if(ctr.update()) dirty=true;
      if(dirty){ renderer.render(scene,cam); updateLabels(); dirty=false; } }
    requestAnimationFrame(loop); }
  requestAnimationFrame(loop);
  // deterministic hook for offline rendering
  window.CHT3D={frame:function(a){ camAt(a); renderer.render(scene,cam); return cv.toDataURL('image/png'); }, start:ang0, ready:function(){return true;}};
  // exports via the downloads capability
  var dl=null;
  if(window.claude&&window.claude.use){ window.claude.use('downloads').then(function(d){ dl=d; if(!d) hideDl(); }).catch(hideDl); } else hideDl();
  function hideDl(){ document.querySelectorAll('.v3controls .dl').forEach(function(b){b.hidden=true;}); status.textContent='Export is available when the page is opened on claude.ai.'; }
  function save(name,blob){ if(!dl)return; dl.save({filename:name,data:blob}).then(function(){status.textContent='Saved '+name+'.';}).catch(function(err){
      var c=err&&err.code; status.textContent=c==='declined'?'Export cancelled.':c==='rate_limited'?'Another save is open; try again in a moment.':'This view cannot save files.'; }); }
  document.getElementById('v3-png').addEventListener('click',function(){ renderer.render(scene,cam); cv.toBlob(function(b){ if(b) save('cht-theater-view.png',b); },'image/png'); });
  document.getElementById('v3-rec').addEventListener('click',function(){
    if(recording||typeof MediaRecorder==='undefined'||!cv.captureStream){ status.textContent='This browser cannot record video; use Save still image.'; return; }
    var secs=+document.getElementById('v3-dur').value, stream=cv.captureStream(30), types=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'], type=types.filter(function(t){return MediaRecorder.isTypeSupported(t)})[0];
    var rec=new MediaRecorder(stream,type?{mimeType:type,videoBitsPerSecond:12e6}:undefined), chunks=[], a0=curAngle(), t0=performance.now();
    recording=true; status.textContent='Recording '+secs+' s spin…';
    rec.ondataavailable=function(e){ if(e.data&&e.data.size)chunks.push(e.data); };
    rec.onstop=function(){ recording=false; save('cht-theater-spin.webm',new Blob(chunks,{type:'video/webm'})); };
    rec.start(500);
    (function step(){ var t=(performance.now()-t0)/1000; if(t>=secs){ setAngle(a0); renderer.render(scene,cam); rec.stop(); return; }
      setAngle(a0+2*Math.PI*t/secs); renderer.render(scene,cam); status.textContent='Recording… '+Math.ceil(secs-t)+' s'; requestAnimationFrame(step); })();
  });
})();
</script>
"""
