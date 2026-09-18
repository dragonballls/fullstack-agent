"""Protected Build #2 frontend assets: GPU-oriented 3D Neural JARVIS world."""

NEURAL_MESH_BUILTIN = {
    "id": "neural-mesh",
    "name": "Neural JARVIS",
    "version": "0.1.0",
    "description": "Blue fully 3D JARVIS neural environment with liquid-cell visuals, zoom, search, typed chat, and adaptive rendering foundations.",
    "protected": True,
    "css": r"""
#jarvis-text-shell,
#jarvis-workspace-shell { display:none !important; }
#jarvis-ui-build-layer.neural-mesh-root {
  position:fixed; inset:0; z-index:2147481000; pointer-events:none;
  color:#dff6ff; font-family:Inter,Segoe UI,system-ui,sans-serif;
}
#jarvis-neural-canvas { position:absolute; inset:0; width:100%; height:100%; display:block; pointer-events:auto; cursor:grab; }
#jarvis-neural-canvas.dragging { cursor:grabbing; }
#jn-hud { position:absolute; left:24px; top:20px; pointer-events:none; text-shadow:0 0 18px rgba(56,174,255,.35); }
#jn-title { font-size:15px; letter-spacing:.34em; color:#a8deff; }
#jn-status { margin-top:4px; font-size:9px; letter-spacing:.16em; color:#4c9fcf; text-transform:uppercase; }
#jn-search { position:absolute; top:20px; right:24px; width:min(320px,34vw); pointer-events:auto; box-sizing:border-box; border:1px solid rgba(91,190,255,.28); border-radius:12px; padding:11px 13px; outline:none; color:#dff6ff; background:rgba(2,12,24,.70); box-shadow:0 0 28px rgba(20,130,220,.10); backdrop-filter:blur(10px); }
#jn-actions { position:absolute; top:63px; right:24px; display:flex; gap:7px; pointer-events:auto; }
.jn-btn { border:1px solid rgba(91,190,255,.20); border-radius:9px; padding:7px 9px; color:#88cfff; background:rgba(2,12,24,.52); cursor:pointer; font:9px/1.2 Inter,Segoe UI,sans-serif; letter-spacing:.12em; text-transform:uppercase; }
.jn-btn:hover { border-color:rgba(124,210,255,.58); }
#jn-inspector { position:absolute; left:24px; bottom:94px; width:min(350px,calc(100vw - 48px)); padding:12px; border:1px solid rgba(91,190,255,.16); border-radius:12px; background:rgba(1,9,18,.68); backdrop-filter:blur(10px); pointer-events:none; opacity:0; transition:opacity .18s ease; }
#jn-inspector.visible { opacity:1; }
.jn-mini { font-size:8px; color:#4d91b8; letter-spacing:.11em; text-transform:uppercase; }
.jn-name { margin-top:3px; font-size:14px; color:#c9eeff; }
.jn-meta { margin-top:6px; font-size:9px; line-height:1.5; color:#6fa8c5; }
#jn-chat { position:absolute; left:50%; bottom:22px; transform:translateX(-50%); width:min(780px,calc(100vw - 48px)); display:flex; gap:9px; padding:9px; box-sizing:border-box; pointer-events:auto; border:1px solid rgba(91,190,255,.26); border-radius:16px; background:rgba(1,9,18,.74); box-shadow:0 0 36px rgba(20,128,255,.10); backdrop-filter:blur(14px); }
#jn-chat input { min-width:0; flex:1; border:0; outline:none; color:#e6f8ff; background:transparent; padding:10px 11px; font:13px/1.2 Inter,Segoe UI,sans-serif; }
#jn-chat input::placeholder { color:rgba(137,190,217,.66); }
#jn-help { position:absolute; left:50%; bottom:80px; transform:translateX(-50%); color:rgba(120,178,208,.58); font-size:8px; letter-spacing:.15em; pointer-events:none; white-space:nowrap; }
#jn-perf { position:absolute; bottom:22px; right:24px; font-size:8px; color:#438eb9; letter-spacing:.12em; pointer-events:none; }
""",
    "markup": r"""
<div class="neural-mesh-root">
  <canvas id="jarvis-neural-canvas"></canvas>
  <div id="jn-hud"><div id="jn-title">JARVIS</div><div id="jn-status">NEURAL MESH · 3D WORLD · ONLINE</div></div>
  <input id="jn-search" autocomplete="off" spellcheck="false" placeholder="Search the neural world…" />
  <div id="jn-actions"><button class="jn-btn" id="jn-home">CORE</button><button class="jn-btn" id="jn-perf-btn">PERFORMANCE</button><button class="jn-btn" id="jn-freeze">FREEZE</button></div>
  <div id="jn-inspector"><div class="jn-mini">SELECTED NEURON</div><div class="jn-name" id="jn-name"></div><div class="jn-meta" id="jn-meta"></div></div>
  <div id="jn-help">DRAG · ORBIT &nbsp;&nbsp; WHEEL · ZOOM &nbsp;&nbsp; CLICK · SELECT &nbsp;&nbsp; TYPE · TALK TO JARVIS</div>
  <div id="jn-chat"><input id="jn-chat-input" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis…" /><button class="jn-btn" id="jn-chat-send">↵</button></div>
  <div id="jn-perf">AUTO QUALITY</div>
</div>
""",
    "script": r"""
const root = arguments[0];
root.classList.add("neural-mesh-root");
(() => {
  "use strict";
  const canvas = root.querySelector("#jarvis-neural-canvas");
  const gl = canvas.getContext("webgl2", { antialias:false, alpha:true, powerPreference:"high-performance" });
  if (!gl) { root.querySelector("#jn-status").textContent="WEBGL2 UNAVAILABLE"; return; }

  const state={nodes:[],links:[],selected:null,frozen:false,mode:"foreground",quality:"maximum",yaw:.2,pitch:-.12,distance:20,lastX:0,lastY:0,dragging:false,lastPoll:0,pollMs:900,frameMs:16,lastFrame:performance.now(),searchTimer:0};

  function compile(type,source){
    const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||"shader error");return s;
  }
  function makeProgram(vs,fs){
    const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,vs));gl.attachShader(p,compile(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);
    if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||"link error");return p;
  }

  const droplet=makeProgram(
    'attribute vec3 aPos;attribute float aSize;attribute float aEnergy;uniform mat4 uMvp;uniform float uTime;varying float vEnergy;void main(){vec3 p=aPos;p.x+=sin(uTime*.00017+aPos.z)*.12;p.y+=cos(uTime*.00021+aPos.x)*.10;p.z+=sin(uTime*.00014+aPos.y)*.13;gl_Position=uMvp*vec4(p,1.0);gl_PointSize=min(54.0,max(5.0,aSize*42.0));vEnergy=aEnergy;}',
    'precision highp float;varying float vEnergy;void main(){vec2 u=gl_PointCoord*2.0-1.0;u.x*=1.10;float d=length(u);float edge=smoothstep(1.0,.68,d);if(edge<=0.0)discard;float core=exp(-5.0*dot(u,u));float ring=.5+.5*cos(10.0*atan(u.y,u.x));float filament=smoothstep(.2,.78,abs(ring))*.18;vec3 blue=vec3(.20,.72,1.0),white=vec3(.75,.95,1.0);vec3 c=mix(blue,white,core)+filament*vec3(.3,.55,.8);gl_FragColor=vec4(c,edge*(.25+.58*core+.18*vEnergy));}'
  );
  const lines=makeProgram(
    'attribute vec3 aPos;attribute float aStrength;uniform mat4 uMvp;varying float vStrength;void main(){gl_Position=uMvp*vec4(aPos,1.0);vStrength=aStrength;}',
    'precision highp float;varying float vStrength;void main(){gl_FragColor=vec4(.10,.54,.98,.08+.34*vStrength);}'
  );

  const posBuf=gl.createBuffer(),sizeBuf=gl.createBuffer(),energyBuf=gl.createBuffer(),lineBuf=gl.createBuffer(),strengthBuf=gl.createBuffer();

  function matrix(){
    const aspect=canvas.width/Math.max(1,canvas.height),f=1/Math.tan(Math.PI/6);
    const proj=new Float32Array(16),view=new Float32Array(16),out=new Float32Array(16);
    proj[0]=f/aspect;proj[5]=f;proj[10]=-1;proj[11]=-1;proj[14]=-.2;
    const cp=Math.cos(state.pitch),sp=Math.sin(state.pitch),sy=Math.sin(state.yaw),cy=Math.cos(state.yaw);
    const ex=sy*cp*state.distance,ey=sp*state.distance,ez=cy*cp*state.distance;
    const zx=ex/Math.max(.001,state.distance),zy=ey/Math.max(.001,state.distance),zz=ez/Math.max(.001,state.distance);
    let xx=-zz,xz=zx,xl=Math.hypot(xx,xz)||1;xx/=xl;xz/=xl;const yx=zy*xz,yy=zz*xx-zx*xz,yz=zx*xx;
    view[0]=xx;view[4]=yx;view[8]=zx;view[12]=-(xx*ex+yx*ey+zx*ez);
    view[1]=0;view[5]=yy;view[9]=zy;view[13]=-(0*ex+yy*ey+zy*ez);
    view[2]=xz;view[6]=yz;view[10]=zz;view[14]=-(xz*ex+yz*ey+zz*ez);view[15]=1;
    for(let c=0;c<4;c++)for(let r=0;r<4;r++)out[c*4+r]=proj[r]*view[c*4]+proj[4+r]*view[c*4+1]+proj[8+r]*view[c*4+2]+proj[12+r]*view[c*4+3];
    return out;
  }

  function upload(buffer,data){gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.DYNAMIC_DRAW);}
  function bind(program,name,size,buffer){const loc=gl.getAttribLocation(program,name);if(loc<0)return;gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,0,0);}

  function updateBuffers(time){
    const max=state.quality==="maximum"?1400:Math.min(700,state.nodes.length),nodes=state.nodes.slice(0,max);
    const pos=new Float32Array(nodes.length*3),size=new Float32Array(nodes.length),energy=new Float32Array(nodes.length);
    nodes.forEach((n,i)=>{pos.set(n.position,i*3);size[i]=(n.scale||1)*(n.kind==="core"?2.2:n.kind==="subsystem"?1.5:.9);energy[i]=n.energy||.2;});
    upload(posBuf,pos);upload(sizeBuf,size);upload(energyBuf,energy);
    const map=new Map(nodes.map(n=>[n.id,n])),lp=new Float32Array(state.links.length*6),ls=new Float32Array(state.links.length*2);
    let count=0;
    for(const r of state.links){const a=map.get(r.source),b=map.get(r.target);if(!a||!b)continue;lp.set(a.position,count*6);lp.set(b.position,count*6+3);ls[count*2]=r.strength||.4;ls[count*2+1]=r.strength||.4;count++;}
    upload(lineBuf,lp);upload(strengthBuf,ls);return {nodes:nodes.length,links:count};
  }

  function resize(){
    const dpr=Math.min(window.devicePixelRatio||1,state.quality==="maximum"?1.5:1),w=Math.max(1,Math.floor(canvas.clientWidth*dpr)),h=Math.max(1,Math.floor(canvas.clientHeight*dpr));
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
  }

  function draw(now){
    requestAnimationFrame(draw);
    if(document.hidden)return;
    resize();const mvp=matrix(),counts=updateBuffers(now);
    gl.clearColor(0,.004,.012,1);gl.clear(gl.COLOR_BUFFER_BIT);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.disable(gl.DEPTH_TEST);
    gl.useProgram(lines);gl.uniformMatrix4fv(gl.getUniformLocation(lines,"uMvp"),false,mvp);bind(lines,"aPos",3,lineBuf);bind(lines,"aStrength",1,strengthBuf);gl.drawArrays(gl.LINES,0,counts.links*2);
    gl.useProgram(droplet);gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uMvp"),false,mvp);gl.uniform1f(gl.getUniformLocation(droplet,"uTime"),now);bind(droplet,"aPos",3,posBuf);bind(droplet,"aSize",1,sizeBuf);bind(droplet,"aEnergy",1,energyBuf);gl.drawArrays(gl.POINTS,0,counts.nodes);
    const dt=now-state.lastFrame;state.lastFrame=now;state.frameMs=state.frameMs*.92+dt*.08;
    root.querySelector("#jn-perf").textContent="AUTO QUALITY · "+state.quality.toUpperCase()+" · "+Math.round(1000/Math.max(1,state.frameMs))+" FPS";
  }

  function api(){return window.pywebview&&window.pywebview.api;}
  async function poll(){
    if(!api()||!api().neural_world_snapshot)return;
    try{
      const data=await api().neural_world_snapshot(state.quality==="maximum"?1400:700);
      state.nodes=Array.isArray(data.entities)?data.entities:[];state.links=Array.isArray(data.relations)?data.relations:[];
      state.quality=data.performance&&data.performance.quality||state.quality;state.mode=data.performance&&data.performance.mode||state.mode;
      root.querySelector("#jn-status").textContent="NEURAL MESH · "+state.nodes.length+" NEURONS · "+state.links.length+" LINKS · "+((data.windows&&data.windows.length)||0)+" WINDOWS";
      state.lastPoll=performance.now();
    }catch(_){root.querySelector("#jn-status").textContent="NEURAL MESH · BACKEND DEGRADED";}
  }

  function select(x,y){
    let best=null,bestD=Infinity,cx=canvas.clientWidth/2,cy=canvas.clientHeight/2;
    for(const n of state.nodes){
      const depth=Math.max(3,state.distance*.18+Math.abs(n.position[2]));
      const sx=cx+n.position[0]*canvas.clientWidth/(depth*2.6),sy=cy-n.position[1]*canvas.clientHeight/(depth*2.0),d=Math.hypot(sx-x,sy-y);
      if(d<bestD){bestD=d;best=n;}
    }
    if(best&&bestD<90){state.selected=best.id;root.querySelector("#jn-name").textContent=best.label;root.querySelector("#jn-meta").textContent=best.kind+" · "+best.status+" · "+best.source+" · "+best.lifecycle;root.querySelector("#jn-inspector").classList.add("visible");}
  }

  async function search(value){
    if(!value.trim()||!api()||!api().neural_search)return;
    try{const results=await api().neural_search(value.trim(),null,null,null,12);if(results.length){const n=results[0];state.selected=n.id;state.target=n.position;root.querySelector("#jn-name").textContent=n.label;root.querySelector("#jn-meta").textContent=n.kind+" · "+n.status+" · "+n.source;root.querySelector("#jn-inspector").classList.add("visible");}}catch(_){}
  }

  async function chat(){
    const input=root.querySelector("#jn-chat-input"),text=input.value.trim();if(!text||!api()||!api().submit_text)return;
    input.disabled=true;root.querySelector("#jn-status").textContent="JARVIS · PROCESSING";
    try{let r=await api().submit_text(text,false);if(r&&r.needs_confirmation&&window.confirm(r.text||"Confirmation required."))r=await api().submit_text(text,true);input.value="";await poll();}catch(_){root.querySelector("#jn-status").textContent="JARVIS · REQUEST FAILED";}finally{input.disabled=false;input.focus();}
  }

  canvas.addEventListener("pointerdown",e=>{state.dragging=true;state.lastX=e.clientX;state.lastY=e.clientY;canvas.classList.add("dragging");canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener("pointermove",e=>{if(!state.dragging)return;state.yaw+=(e.clientX-state.lastX)*.008;state.pitch=Math.max(-1.35,Math.min(1.35,state.pitch+(e.clientY-state.lastY)*.006));state.lastX=e.clientX;state.lastY=e.clientY;});
  canvas.addEventListener("pointerup",()=>{state.dragging=false;canvas.classList.remove("dragging");});
  canvas.addEventListener("pointercancel",()=>{state.dragging=false;canvas.classList.remove("dragging");});
  canvas.addEventListener("wheel",e=>{e.preventDefault();state.distance=Math.max(4,Math.min(160,state.distance*Math.exp(e.deltaY*.001)));},{passive:false});
  canvas.addEventListener("click",e=>select(e.clientX,e.clientY));
  root.querySelector("#jn-search").addEventListener("input",e=>{clearTimeout(state.searchTimer);state.searchTimer=setTimeout(()=>search(e.target.value),250);});
  root.querySelector("#jn-home").addEventListener("click",()=>{state.distance=20;state.yaw=.2;state.pitch=-.12;});
  root.querySelector("#jn-perf-btn").addEventListener("click",async()=>{const next=state.mode==="foreground"?"background":"foreground";if(api()&&api().neural_set_performance_mode){const r=await api().neural_set_performance_mode(next);state.mode=r.mode||next;state.quality=r.quality||state.quality;}});
  root.querySelector("#jn-freeze").addEventListener("click",()=>{state.frozen=!state.frozen;root.querySelector("#jn-freeze").textContent=state.frozen?"UNFREEZE":"FREEZE";});
  root.querySelector("#jn-chat-send").addEventListener("click",chat);
  root.querySelector("#jn-chat-input").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();chat();}});
  document.addEventListener("visibilitychange",()=>{canvas.style.visibility=document.hidden?"hidden":"visible";});
  window.addEventListener("resize",resize);
  poll();setInterval(()=>{if(!state.frozen&&performance.now()-state.lastPoll>state.pollMs)poll();},400);draw(performance.now());
})();
"""
}
