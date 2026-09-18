"""Protected Build #2 frontend assets for the Neural JARVIS world.

The asset is deliberately dependency-light: WebGL2, CSS, and the existing pywebview
bridge. It is rendered as an additive UI build and does not replace Jarvis core.
"""

NEURAL_MESH_BUILTIN = {
    "id": "neural-mesh",
    "name": "Neural JARVIS",
    "version": "0.4.0",
    "description": "Blue fully 3D JARVIS world with instanced liquid-cell neurons, lifecycle pulses, fluid grab/return, spatial windows, search, zoom, performance culling, and a camera-facing persistent neural command surface.",
    "protected": True,
    "css": r"""
#jarvis-text-shell,#jarvis-workspace-shell{display:none!important}
#jarvis-ui-build-layer.neural-mesh-root{position:fixed;inset:0;z-index:2147481000;pointer-events:none;color:#dff6ff;font-family:Inter,Segoe UI,system-ui,sans-serif;overflow:hidden;background:#000}
#jarvis-neural-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;pointer-events:auto;cursor:grab;background:radial-gradient(circle at 50% 46%,rgba(29,150,255,.075),transparent 43%),linear-gradient(180deg,#010813,#000207)}
#jarvis-neural-canvas.dragging{cursor:grabbing}
#jn-hud{position:absolute;left:24px;top:20px;pointer-events:none;text-shadow:0 0 18px rgba(56,174,255,.45)}
#jn-title{font-size:16px;letter-spacing:.34em;color:#b8e9ff}
#jn-status{margin-top:5px;font-size:9px;letter-spacing:.15em;color:#58a8d7;text-transform:uppercase}
#jn-focus{position:absolute;left:24px;top:86px;max-width:420px;font-size:10px;color:#78b9dc;pointer-events:none}
#jn-search{position:absolute;right:24px;top:20px;width:min(340px,36vw);box-sizing:border-box;pointer-events:auto;border:1px solid rgba(91,190,255,.28);border-radius:12px;padding:11px 13px;outline:none;color:#dff6ff;background:rgba(2,12,24,.72);box-shadow:0 0 28px rgba(20,130,220,.1);backdrop-filter:blur(10px)}
#jn-kind,#jn-life{position:absolute;top:63px;width:145px;box-sizing:border-box;padding:7px 8px;border:1px solid rgba(91,190,255,.18);border-radius:9px;color:#88cfff;background:rgba(2,12,24,.68);font:8px Inter,Segoe UI,sans-serif;letter-spacing:.1em;pointer-events:auto;text-transform:uppercase}
#jn-kind{right:322px}#jn-life{right:165px}
#jn-kind,#jn-life,#jn-connected,#jn-source,#jn-age{position:absolute;right:24px;box-sizing:border-box;border:1px solid rgba(91,190,255,.18);border-radius:9px;padding:8px 10px;outline:none;color:#9bd9f5;background:rgba(2,12,24,.72);font:8px Inter,Segoe UI,sans-serif;letter-spacing:.08em;backdrop-filter:blur(10px)}
#jn-kind{top:112px;width:150px}#jn-life{top:112px;right:182px;width:140px}#jn-connected{top:150px;width:min(298px,32vw)}#jn-source{top:188px;width:180px}#jn-age{top:188px;right:212px;width:130px}
#jn-actions{position:absolute;right:24px;top:63px;display:flex;gap:7px;pointer-events:auto;flex-wrap:wrap;justify-content:flex-end;max-width:450px}
.jn-btn{border:1px solid rgba(91,190,255,.2);border-radius:9px;padding:7px 9px;color:#88cfff;background:rgba(2,12,24,.52);cursor:pointer;font:9px/1.2 Inter,Segoe UI,sans-serif;letter-spacing:.12em;text-transform:uppercase}
.jn-btn:hover{border-color:rgba(124,210,255,.6);box-shadow:0 0 18px rgba(39,151,239,.1)}
#jn-inspector{position:absolute;left:24px;bottom:95px;width:min(360px,calc(100vw - 48px));padding:12px;border:1px solid rgba(91,190,255,.16);border-radius:12px;background:rgba(1,9,18,.66);box-shadow:0 0 28px rgba(20,128,255,.06);backdrop-filter:blur(10px);pointer-events:none;opacity:0;transition:opacity .18s ease}
#jn-inspector.visible{opacity:1}
.jn-mini{font-size:8px;color:#4d91b8;letter-spacing:.11em;text-transform:uppercase}
.jn-name{margin-top:3px;font-size:14px;color:#c9eeff}
.jn-meta{margin-top:6px;font-size:9px;line-height:1.5;color:#6fa8c5}
#jn-response{position:absolute;left:50%;bottom:81px;transform:translateX(-50%);width:min(760px,calc(100vw - 80px));max-height:100px;overflow:auto;padding:8px 12px;box-sizing:border-box;border:1px solid rgba(91,190,255,.12);border-radius:11px;background:rgba(1,9,18,.45);color:rgba(181,226,248,.86);font-size:9px;line-height:1.45;pointer-events:none;opacity:0}
#jn-response.visible{opacity:1}
#jn-observe{position:absolute;right:24px;bottom:92px;width:min(390px,calc(100vw - 48px));max-height:180px;overflow:auto;padding:10px;border:1px solid rgba(91,190,255,.12);border-radius:11px;background:rgba(1,9,18,.54);color:#88bddc;font-size:8px;line-height:1.45;pointer-events:none;opacity:0;backdrop-filter:blur(10px)}
#jn-observe.visible{opacity:1}
#jn-minimap{position:absolute;right:24px;bottom:64px;width:180px;height:110px;border:1px solid rgba(91,190,255,.12);border-radius:10px;background:rgba(1,9,18,.35);opacity:.72;pointer-events:none;display:none}
#jn-minimap.visible{display:block}
#jn-neural-console{position:absolute;left:0;top:0;width:min(560px,calc(100vw - 32px));min-height:96px;box-sizing:border-box;pointer-events:auto;transform:translate3d(-9999px,-9999px,0) scale(.94);transform-origin:50% 50%;transform-style:preserve-3d;will-change:transform;z-index:40}
#jn-neural-console.jn-console-collapsed{width:min(310px,calc(100vw - 32px));min-height:0}
#jn-neural-console::before{content:"";position:absolute;inset:-1px;border:1px solid rgba(77,184,255,.24);border-radius:18px;background:linear-gradient(145deg,rgba(4,20,39,.92),rgba(1,8,18,.82));box-shadow:0 24px 80px rgba(0,0,0,.42),0 0 42px rgba(24,140,255,.18),inset 0 0 30px rgba(42,168,255,.04);backdrop-filter:blur(16px);transform:translateZ(-8px);pointer-events:none}
#jn-neural-console::after{content:"";position:absolute;left:13px;right:13px;top:42px;height:1px;background:linear-gradient(90deg,rgba(72,186,255,.4),transparent 82%);opacity:.72;pointer-events:none}
#jn-console-header{position:relative;display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px 9px}
.jn-console-identity{display:flex;align-items:center;gap:8px;min-width:0}
.jn-console-orb{width:9px;height:9px;border-radius:50%;background:#55caff;box-shadow:0 0 18px rgba(70,194,255,.95),0 0 36px rgba(70,194,255,.32);flex:0 0 auto}
.jn-console-title{font-size:9px;letter-spacing:.19em;color:#bfeaff;text-transform:uppercase;white-space:nowrap}
.jn-console-subtitle{margin-top:2px;font-size:7px;letter-spacing:.10em;color:#4e91bb;text-transform:uppercase;white-space:nowrap}
.jn-console-controls{display:flex;gap:5px;pointer-events:auto}
.jn-console-btn{border:1px solid rgba(91,190,255,.18);border-radius:8px;min-width:28px;height:27px;padding:0 8px;color:#7fc5ea;background:rgba(3,18,32,.48);cursor:pointer;font:8px Inter,Segoe UI,sans-serif;letter-spacing:.09em;text-transform:uppercase}
.jn-console-btn:hover{border-color:rgba(127,219,255,.62);box-shadow:0 0 18px rgba(45,159,246,.14);color:#dff6ff}
#jn-console-body{position:relative;padding:0 12px 11px}
#jn-console-log{display:flex;flex-direction:column;gap:5px;max-height:74px;overflow:auto;margin:0 0 8px;padding:5px 1px 0;scrollbar-width:thin}
.jn-console-message{max-width:92%;padding:6px 8px;border:1px solid rgba(91,190,255,.09);border-radius:8px;background:rgba(255,255,255,.018);font-size:8px;line-height:1.35;color:#83afd0;word-break:break-word}
.jn-console-message.user{margin-left:auto;border-color:rgba(68,184,255,.17);color:#b9e5ff;background:rgba(39,140,208,.06)}
.jn-console-message.system{color:#6e9abb}
#jn-console-quick{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:7px}
.jn-console-chip{border:1px solid rgba(91,190,255,.12);border-radius:8px;padding:5px 7px;color:#6faecf;background:rgba(2,15,27,.42);cursor:pointer;font:7px Inter,Segoe UI,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.jn-console-chip:hover{color:#cdeeff;border-color:rgba(108,210,255,.34)}
#jn-console-composer{display:flex;gap:7px;align-items:flex-end;padding:6px;border:1px solid rgba(91,190,255,.21);border-radius:12px;background:rgba(1,10,20,.54);box-shadow:inset 0 0 20px rgba(30,142,229,.035)}
#jn-chat-input{min-width:0;flex:1;resize:none;border:0;outline:none;overflow:hidden;color:#e6f8ff;background:transparent;padding:5px 6px;font:11px/1.35 Inter,Segoe UI,sans-serif;max-height:92px}
#jn-chat-input::placeholder{color:rgba(137,190,217,.66)}
#jn-chat-send{width:38px;height:34px;flex:0 0 auto}
#jn-console-footer{display:flex;justify-content:space-between;gap:8px;padding:6px 2px 0;color:#477da0;font-size:7px;letter-spacing:.10em;text-transform:uppercase}
#jn-console-footer strong{color:#62bff0;font-weight:500}
#jn-neural-console.jn-console-collapsed #jn-console-body,#jn-neural-console.jn-console-collapsed #jn-console-footer{display:none}
#jn-neural-console.jn-console-collapsed::after{top:43px}
#jn-neural-console.jn-console-collapsed .jn-console-subtitle{color:#5da4cc}
#jn-console-tether{position:absolute;left:0;top:0;width:0;height:1px;transform-origin:0 50%;background:linear-gradient(90deg,rgba(61,186,255,.64),rgba(61,186,255,.12),transparent);box-shadow:0 0 10px rgba(42,160,255,.25);pointer-events:none;z-index:35}
#jn-console-tether::after{content:"";position:absolute;right:-3px;top:-3px;width:7px;height:7px;border:1px solid rgba(120,220,255,.72);border-radius:50%;background:rgba(32,138,214,.24);box-shadow:0 0 14px rgba(63,191,255,.55)}
#jn-help{position:absolute;left:50%;bottom:128px;transform:translateX(-50%);color:rgba(120,178,208,.56);font-size:8px;letter-spacing:.13em;pointer-events:none;white-space:nowrap}
#jn-perf{position:absolute;bottom:22px;right:24px;font-size:8px;color:#438eb9;letter-spacing:.12em;pointer-events:none}
#jn-ecology{position:absolute;left:24px;bottom:22px;font-size:8px;color:#438eb9;letter-spacing:.12em;pointer-events:none;text-transform:uppercase}
#jn-surfaces{position:absolute;inset:0;pointer-events:none;perspective:1600px;transform-style:preserve-3d;overflow:hidden;transition:perspective .25s ease}
#jn-surfaces.flat-2d{perspective:none;transform-style:flat}
.jn-spatial-window{position:absolute;left:0;top:0;width:360px;height:250px;transform-style:preserve-3d;pointer-events:auto;border:1px solid rgba(92,200,255,.25);border-radius:14px;background:rgba(4,16,30,.62);box-shadow:0 18px 70px rgba(0,0,0,.42),0 0 32px rgba(31,151,238,.09),inset 0 0 24px rgba(37,155,232,.05);overflow:hidden;backdrop-filter:blur(7px)}
.jn-spatial-window.giant{width:740px;height:470px}
.jn-spatial-window.shape-circle{border-radius:50%}.jn-spatial-window.shape-oval{border-radius:48%}.jn-spatial-window.shape-pill{border-radius:999px}.jn-spatial-window.shape-hex{clip-path:polygon(25% 4%,75% 4%,98% 50%,75% 96%,25% 96%,2% 50%)}.jn-spatial-window.shape-diamond{clip-path:polygon(50% 0%,100% 50%,50% 100%,0% 50%)}.jn-spatial-window.shape-triangle{clip-path:polygon(50% 0%,100% 100%,0% 100%)}.jn-spatial-window.shape-star{clip-path:polygon(50% 0%,61% 36%,98% 36%,68% 58%,79% 100%,50% 74%,21% 100%,32% 58%,2% 36%,39% 36%)}
.jn-window-head{height:28px;display:flex;align-items:center;justify-content:space-between;padding:0 9px;border-bottom:1px solid rgba(92,200,255,.12);background:rgba(3,12,24,.57);font-size:8px;letter-spacing:.08em;color:#86c4e2;user-select:none;cursor:grab}
.jn-window-head:active{cursor:grabbing}
.jn-window-resize{position:absolute;right:2px;bottom:2px;width:18px;height:18px;cursor:nwse-resize;opacity:.5}
.jn-window-resize::after{content:"";position:absolute;right:2px;bottom:2px;width:10px;height:10px;border-right:2px solid rgba(140,220,255,.7);border-bottom:2px solid rgba(140,220,255,.7)}
.jn-window-preview{display:block;width:100%;height:calc(100% - 28px);object-fit:contain;background:rgba(1,5,12,.70)}
.jn-window-empty{height:222px;display:flex;align-items:center;justify-content:center;color:rgba(112,164,194,.55);font-size:8px;letter-spacing:.12em;text-transform:uppercase}
.jn-spatial-window.giant .jn-window-empty{height:442px}
.jn-window-status{font-size:7px;color:#4f9ac1}
""",
    "markup": r"""
<div class="neural-mesh-root">
  <canvas id="jarvis-neural-canvas"></canvas>
  <div id="jn-surfaces"></div>
  <div id="jn-hud"><div id="jn-title">JARVIS</div><div id="jn-status">NEURAL MESH · 3D WORLD · ONLINE</div></div>
  <div id="jn-focus"></div>
  <input id="jn-search" autocomplete="off" spellcheck="false" placeholder="Search the neural world…" />
  <input id="jn-connected" autocomplete="off" spellcheck="false" placeholder="Connected to…" />
  <input id="jn-source" autocomplete="off" spellcheck="false" placeholder="Source…" />
  <select id="jn-age" aria-label="recency"><option value="">ANY TIME</option><option value="900">15 MIN</option><option value="3600">1 HR</option><option value="86400">24 HR</option><option value="604800">7 DAYS</option></select>
  <select id="jn-kind" aria-label="Neural type filter"><option value="">ALL TYPES</option><option value="file">FILES</option><option value="application">APPS</option><option value="window">WINDOWS</option><option value="page">PAGES</option><option value="repository">REPOS</option><option value="agent">AGENTS</option><option value="task">TASKS</option><option value="memory">MEMORY</option><option value="location">LOCATIONS</option><option value="process">PROCESSES</option></select>
  <select id="jn-life" aria-label="Neural lifecycle filter"><option value="">ALL STATES</option><option value="active">ACTIVE</option><option value="waiting">WAITING</option><option value="mature">MATURE</option><option value="dormant">DORMANT</option><option value="failed">FAILED</option><option value="retired">RETIRED</option></select>
  <div id="jn-actions">
    <button class="jn-btn" id="jn-home">CORE</button>
  <button class="jn-btn" id="jn-trace">TRACE</button>
    <button class="jn-btn" id="jn-earth">EARTH</button>
    <button class="jn-btn" id="jn-mode">3D</button>
    <button class="jn-btn" id="jn-follow">FOLLOW</button>
    <button class="jn-btn" id="jn-map">MAP</button>
    <button class="jn-btn" id="jn-windows">WINDOWS</button>
    <button class="jn-btn" id="jn-giant">GIANT</button>
    <button class="jn-btn" id="jn-perf-btn">PERF</button>
    <button class="jn-btn" id="jn-freeze">FREEZE</button>
  </div>
  <div id="jn-inspector"><div class="jn-mini">SELECTED NEURON</div><div class="jn-name" id="jn-name"></div><div class="jn-meta" id="jn-meta"></div></div>
  <div id="jn-response"></div>
  <div id="jn-observe"></div><canvas id="jn-minimap" width="180" height="110"></canvas>
  <div id="jn-help">DRAG · ORBIT · WHEEL · ZOOM · GRAB NEURON · TYPE TALK · SPATIAL WINDOWS</div>
  <div id="jn-console-tether"></div>
  <div id="jn-neural-console" aria-label="Neural command surface">
    <div id="jn-console-header">
      <div class="jn-console-identity"><span class="jn-console-orb"></span><div><div class="jn-console-title">NEURAL COMMAND</div><div class="jn-console-subtitle" id="jn-console-status">3D CORE LINK · ALWAYS IN VIEW</div></div></div>
      <div class="jn-console-controls"><button class="jn-console-btn" id="jn-console-float" title="Detach the neural command surface into a movable desktop window">FLOAT</button><button class="jn-console-btn" id="jn-console-collapse" title="Collapse the command surface">MIN</button><button class="jn-console-btn" id="jn-console-hotkey" title="F13 toggles this surface">F13</button></div>
    </div>
    <div id="jn-console-body">
      <div id="jn-console-log"><div class="jn-console-message system">Neural command surface online. Locked to JARVIS CORE.</div></div>
      <div id="jn-console-quick">
        <button class="jn-console-chip" data-command="Show me what you are doing">SHOW ACTIVITY</button>
        <button class="jn-console-chip" data-command="Open God's Eye">GOD'S EYE</button>
        <button class="jn-console-chip" data-command="Check system status">SYSTEM STATUS</button>
        <button class="jn-console-chip" data-command="Show my workflows">WORKFLOWS</button>
      </div>
      <div id="jn-console-composer"><textarea id="jn-chat-input" rows="1" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis…"></textarea><button class="jn-btn" id="jn-chat-send" aria-label="Send message">↵</button></div>
      <div id="jn-console-footer"><span>ENTER SEND · SHIFT+ENTER NEW LINE</span><strong>F13 TOGGLE · CORE LOCKED · CAMERA FACING</strong></div>
    </div>
  </div>
  <div id="jn-perf">AUTO QUALITY</div><div id="jn-ecology">FLUID ECOLOGY · STANDBY</div>
</div>
""",
    "script": r"""
const ui = arguments[0];
ui.classList.add("neural-mesh-root");
(function(){
"use strict";
const canvas=ui.querySelector("#jarvis-neural-canvas");
const gl=canvas.getContext("webgl2",{antialias:false,alpha:true,powerPreference:"high-performance",desynchronized:true});
if(!gl){ui.querySelector("#jn-status").textContent="NEURAL MESH · WEBGL2 UNAVAILABLE";return;}

const S={
  nodes:[],links:[],windows:[],selected:null,dragNode:null,orbit:false,pointerMoved:false,tracePath:[],traceIndex:0,traceTimer:null,follow:false,minimap:false,connected:"",followTask:null,
  localOffsets:new Map(),velocities:new Map(),births:new Map(),retirements:new Map(),particles:[],eventSequence:0,
  lastSnapshot:0,lastEvents:0,lastWindows:0,lastPoll:0,lastAdvanced:0,lastNativeVisibility:0,nativeVisibilityMs:500,observationSequence:0,lastHandPoll:0,lastLayoutPoll:0,snapshotMs:2600,eventsMs:320,windowsMs:2200,advancedPollMs:720,
  quality:"maximum",mode:"foreground",view:"network",surfaceMode:"3d",frozen:false,giant:false,showWindows:true,
  earthData:{locators:[]},earthLastPoll:0,earthYaw:0,earthPitch:-0.16,earthDistance:4.6,observation:{enabled:false,focus:"auto"},hand:{enabled:false,sample:null},handWindow:null,lastHandPoll:0,handPollMs:90,handPinching:false,handNode:null,handX:0,handY:0,
  yaw:.20,pitch:-.12,distance:20,target:[0,0,0],lastX:0,lastY:0,
  frameMs:16,lastFrame:performance.now(),searchTimer:0,layoutTimers:new Map(),consoleCollapsed:false,lastConsoleLayout:0,consoleLayoutMs:50,
  surfacePositions:new Map(),surfaceScales:new Map(),layouts:new Map(),lastLayoutPoll:0,layoutPollMs:2200,advanced:{physics:{}}
};

function compile(type,src){
  const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);
  if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s)||"shader");
  return s;
}
function program(vs,fs){
  const p=gl.createProgram();gl.attachShader(p,compile(gl.VERTEX_SHADER,vs));gl.attachShader(p,compile(gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);
  if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p)||"link");
  return p;
}
function cross(a,b){return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]}
function sub(a,b){return[a[0]-b[0],a[1]-b[1],a[2]-b[2]]}
function add(a,b){return[a[0]+b[0],a[1]+b[1],a[2]+b[2]]}
function mul3(a,s){return[a[0]*s,a[1]*s,a[2]*s]}
function norm(v){const l=Math.hypot(v[0],v[1],v[2])||1;return[v[0]/l,v[1]/l,v[2]/l]}
function perspective(out,fov,aspect,near,far){const f=1/Math.tan(fov/2);out.fill(0);out[0]=f/aspect;out[5]=f;out[10]=(far+near)/(near-far);out[11]=-1;out[14]=(2*far*near)/(near-far);return out}
function lookAt(out,eye,target){
  const z=norm(sub(eye,target)),x=norm(cross([0,1,0],z)),y=cross(z,x);
  out.fill(0);out[0]=x[0];out[1]=y[0];out[2]=z[0];out[4]=x[1];out[5]=y[1];out[6]=z[1];out[8]=x[2];out[9]=y[2];out[10]=z[2];out[15]=1;
  out[12]=-(x[0]*eye[0]+x[1]*eye[1]+x[2]*eye[2]);
  out[13]=-(y[0]*eye[0]+y[1]*eye[1]+y[2]*eye[2]);
  out[14]=-(z[0]*eye[0]+z[1]*eye[1]+z[2]*eye[2]);
  return out;
}
function multiply(out,a,b){
  const r=new Float32Array(16);
  for(let c=0;c<4;c++)for(let row=0;row<4;row++)r[c*4+row]=a[row]*b[c*4]+a[4+row]*b[c*4+1]+a[8+row]*b[c*4+2]+a[12+row]*b[c*4+3];
  out.set(r);return out;
}
function camera(){
  const cp=Math.cos(S.pitch),sp=Math.sin(S.pitch),sy=Math.sin(S.yaw),cy=Math.cos(S.yaw);
  const eye=[S.target[0]+sy*cp*S.distance,S.target[1]+sp*S.distance,S.target[2]+cy*cp*S.distance];
  const forward=norm(sub(S.target,eye)),right=norm(cross(forward,[0,1,0])),up=norm(cross(right,forward));
  return{eye,forward,right,up};
}
function upload(buf,data,usage){gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data,usage||gl.DYNAMIC_DRAW)}
function attr(p,name,size,buf,div){
  const loc=gl.getAttribLocation(p,name);if(loc<0)return;
  gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,0,0);
  if(div!==undefined)gl.vertexAttribDivisor(loc,div);
}

const droplet=program(
'#version 300 es\nprecision highp float;\nlayout(location=0)in vec3 aPos;layout(location=1)in vec3 aNormal;layout(location=2)in vec3 aCenter;layout(location=3)in float aScale;layout(location=4)in float aEnergy;layout(location=5)in float aPhase;layout(location=6)in float aSelected;layout(location=7)in float aShape;layout(location=8)in float aBirth;\nuniform mat4 uMvp;uniform mat4 uView;uniform float uTime;out vec3 vNormal;out vec3 vView;out vec3 vLocal;out float vEnergy;out float vPhase;out float vSelected;\nvoid main(){float life=clamp((uTime-aBirth)/760.0,0.0,1.0);float grow=life*life*(3.0-2.0*life);float wob=1.0+.028*sin(uTime*.0035+aPhase+aPos.y*4.0);vec3 local=aPos*wob; if(aShape<1.5){local=vec3(local.x,local.y*1.05,local.z);} else if(aShape<2.5){local=normalize(aPos)*(.84+.16*abs(aPos.y));} else if(aShape<3.5){local*=vec3(.88,1.38,.88);} else if(aShape<4.5){local*=vec3(.72,1.45,.72);} else if(aShape<5.5){local.xz*=1.0+.30*sin(8.0*atan(local.z,local.x));} else if(aShape<6.5){local.y*=.34;local.xz*=1.20;} else if(aShape<7.5){local.xz*=1.0+.55*pow(max(0.,sin(5.0*atan(local.z,local.x))),6.0);} else if(aShape<8.5){float ang=atan(local.z,local.x);local.xz*=.82+.22*cos(2.*ang);local.y*=1.18;} else if(aShape<9.5){local*=1.25;local.y*=.8;} else if(aShape<10.5){float h=1.0+0.7*cos(atan(local.z,local.x));local.x*=h;local.z*=h;local.y*=1.08;} else if(aShape<11.5){float ang=atan(local.z,local.x);local.xz*=.78+0.34*(.5+.5*sin(10.*ang));} else if(aShape<12.5){float ang=atan(local.z,local.x);float t=0.5+.5*sin(4.*ang);local.xz*=.68+.46*t;local.y+=.18*sin(ang*4.); } else if(aShape<13.5){local.y=sign(local.y)*pow(abs(local.y),.7);local.xz*=1.0-0.35*abs(local.y);} else if(aShape<14.5){local.y+=.30*sin(7.*atan(local.z,local.x));local.xz*=.94;} else if(aShape<15.5){float ang=atan(local.z,local.x);local.xz*=.78;local.y+=.28*sin(ang*5.);local.x+=.11*sin(local.y*6.); } else if(aShape<16.5){local*=.62;local.x+=.46*sin(local.y*5.);local.z+=.46*cos(local.y*5.);} else {local*=.72;local.x+=.55*sign(local.x);} local.y+=.035*sin(uTime*.0025+aPhase*1.7);vec3 world=aCenter+local*(aScale*mix(.08,1.0,grow));world+=vec3(sin(uTime*.0002+aPhase)*.06,cos(uTime*.00017+aPhase*1.4)*.05,sin(uTime*.00018+aPhase*.8)*.06)*min(1.0,aScale);vec4 vp=uView*vec4(world,1.0);gl_Position=uMvp*vec4(world,1.0);vNormal=normalize(mat3(uView)*aNormal);vView=normalize(-vp.xyz);vLocal=local;vEnergy=aEnergy;vPhase=aPhase;vSelected=aSelected;}',
'#version 300 es\nprecision highp float;in vec3 vNormal;in vec3 vView;in vec3 vLocal;in float vEnergy;in float vPhase;in float vSelected;out vec4 outColor;\nvoid main(){vec3 n=normalize(vNormal),light=normalize(vec3(-.35,.62,.74));float diff=max(0.,dot(n,light));float fres=pow(1.-max(0.,dot(n,normalize(vView))),2.);float ring=.5+.5*sin(14.*atan(vLocal.z,vLocal.x)+vPhase+vLocal.y*5.);float e=clamp(vEnergy,0.,1.);vec3 blue=vec3(.05,.31,.73),cyan=vec3(.24,.78,1.),white=vec3(.82,.97,1.);vec3 c=mix(blue,cyan,diff*.6+fres*.4);c=mix(c,white,e*.26+ring*.08);if(vSelected>.5)c=mix(c,vec3(.70,.96,1.),.50);outColor=vec4(c,clamp(.30+.38*fres+.16*e+.07*ring,0.,.96));}'
);

const earthProg=program(
`#version 300 es
precision highp float;
layout(location=0)in vec3 aPos;layout(location=1)in vec3 aNormal;
uniform mat4 uMvp;uniform mat4 uModel;out vec3 vPos;out vec3 vNormal;
void main(){vPos=aPos;vNormal=mat3(uModel)*aNormal;gl_Position=uMvp*uModel*vec4(aPos,1.);}`,
`#version 300 es
precision highp float;
in vec3 vPos;in vec3 vNormal;out vec4 outColor;
void main(){
  vec3 n=normalize(vNormal),light=normalize(vec3(-.55,.68,.75));
  float lit=.32+.68*max(0.,dot(n,light));
  float lat=asin(clamp(vPos.y,-1.,1.)),lon=atan(vPos.z,vPos.x);
  float noise=sin(lon*4.2+sin(lat*5.0))*sin(lat*7.1)+.34*sin(lon*9.2-lat*2.7);
  float land=smoothstep(.18,.56,noise);
  float polar=smoothstep(.69,.93,abs(vPos.y));
  vec3 c=mix(vec3(.012,.20,.46),vec3(.08,.42,.25),land);
  c=mix(c,vec3(.72,.90,.98),polar*.76);
  float gridLat=pow(1.-abs(sin(lat*18.)),18.);
  float gridLon=pow(1.-abs(sin(lon*36.)),24.);
  c+=vec3(.16,.52,.86)*(gridLat+gridLon)*.038;
  float rim=pow(1.-max(0.,dot(n,vec3(0.,0.,1.))),2.);
  c+=vec3(.10,.43,.94)*rim*.34;
  outColor=vec4(c*lit,1.);
}`
);
const lineProg=program(
'#version 300 es\nprecision highp float;layout(location=0)in vec3 aPos;layout(location=1)in float aStrength;layout(location=2)in float aProgress;uniform mat4 uMvp;uniform float uTime;out float vStrength;out float vProgress;void main(){gl_Position=uMvp*vec4(aPos,1.);vStrength=aStrength;vProgress=aProgress;}',
'#version 300 es\nprecision highp float;in float vStrength;in float vProgress;uniform float uTime;out vec4 outColor;void main(){float pulse=.5+.5*sin(vProgress*18.-uTime*.004);outColor=vec4(.04,.46,.98,(.035+.27*vStrength)*(.72+.28*pulse));}'
);

const partProg=program(
'#version 300 es\nprecision highp float;layout(location=0)in vec3 aPos;layout(location=1)in float aLife;layout(location=2)in float aSize;uniform mat4 uMvp;out float vLife;void main(){gl_Position=uMvp*vec4(aPos,1.);gl_PointSize=max(2.,aSize*(1.-aLife));vLife=aLife;}',
'#version 300 es\nprecision highp float;in float vLife;out vec4 outColor;void main(){vec2 u=gl_PointCoord*2.-1.;if(length(u)>1.)discard;outColor=vec4(.18,.69,1.,(1.-vLife)*.48);}'
);

const meshPos=gl.createBuffer(),meshNormal=gl.createBuffer(),meshIndex=gl.createBuffer(),centerBuf=gl.createBuffer(),scaleBuf=gl.createBuffer(),energyBuf=gl.createBuffer(),phaseBuf=gl.createBuffer(),selectedBuf=gl.createBuffer(),shapeBuf=gl.createBuffer(),birthBuf=gl.createBuffer(),lineBuf=gl.createBuffer(),lineStrengthBuf=gl.createBuffer(),lineProgressBuf=gl.createBuffer(),particleBuf=gl.createBuffer(),particleLifeBuf=gl.createBuffer(),particleSizeBuf=gl.createBuffer();

function buildDroplet(){
  const lat=7,lon=10,pos=[],nor=[],idx=[];
  for(let iy=0;iy<=lat;iy++){
    const p=Math.PI*iy/lat,y=Math.cos(p),r=Math.sin(p),pinch=1-.20*Math.max(0,y)+.045*Math.max(0,-y);
    for(let ix=0;ix<=lon;ix++){
      const t=2*Math.PI*ix/lon,a=1+.04*Math.sin(3*t+2*y),x=r*Math.cos(t)*pinch*a,z=r*Math.sin(t)*pinch,yy=y*1.12+.028*Math.sin(2*t)*(1-Math.abs(y));
      pos.push(x,yy,z);nor.push(...norm([x,yy*.92,z]));
    }
  }
  for(let iy=0;iy<lat;iy++)for(let ix=0;ix<lon;ix++){const a=iy*(lon+1)+ix,b=a+1,c=a+lon+1,d=c+1;idx.push(a,c,b,b,c,d);}
  upload(meshPos,new Float32Array(pos),gl.STATIC_DRAW);upload(meshNormal,new Float32Array(nor),gl.STATIC_DRAW);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,meshIndex);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(idx),gl.STATIC_DRAW);return idx.length;
}
const meshCount=buildDroplet();
const earthPos=gl.createBuffer(),earthNormal=gl.createBuffer(),earthIndex=gl.createBuffer(),earthCenterBuf=gl.createBuffer(),earthScaleBuf=gl.createBuffer(),earthEnergyBuf=gl.createBuffer(),earthPhaseBuf=gl.createBuffer(),earthSelectedBuf=gl.createBuffer(),earthShapeBuf=gl.createBuffer(),earthBirthBuf=gl.createBuffer();
function buildEarthSphere(){
  const lat=20,lon=32,pos=[],nor=[],idx=[];
  for(let iy=0;iy<=lat;iy++){
    const p=Math.PI*iy/lat,y=Math.cos(p),r=Math.sin(p);
    for(let ix=0;ix<=lon;ix++){
      const t=2*Math.PI*ix/lon,x=r*Math.cos(t),z=r*Math.sin(t);
      pos.push(x,y,z);nor.push(x,y,z);
    }
  }
  for(let iy=0;iy<lat;iy++)for(let ix=0;ix<lon;ix++){
    const a=iy*(lon+1)+ix,b=a+1,c=a+lon+1,d=c+1;idx.push(a,c,b,b,c,d);
  }
  upload(earthPos,new Float32Array(pos),gl.STATIC_DRAW);
  upload(earthNormal,new Float32Array(nor),gl.STATIC_DRAW);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,earthIndex);
  gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(idx),gl.STATIC_DRAW);
  return idx.length;
}
const earthIndexCount=buildEarthSphere();

function shapeCode(node){const name=String(node.shape&&node.shape.name||"droplet").toLowerCase();const codes={sphere:2,capsule:3,crystal:4,torus:5,ring:6,star:7,orbital:8,core:9,heart:10,gear:11,spiral:12,pyramid:13,wave:14,dna:15,molecule:16,arrow:17};return codes[name]||((name.length%11)+18);}
function nodePosition(n){const o=S.localOffsets.get(n.id),b=o?[n.position[0]+o[0],n.position[1]+o[1],n.position[2]+o[2]]:n.position,p=S.advanced&&S.advanced.physics||{},wave=Number(p.waves&&p.waves[0]&&p.waves[0].amplitude)||0,ripple=Number(p.ripples&&p.ripples[0]&&p.ripples[0].strength)||0,t=performance.now()*.001+Number(n.id.length||0);return[b[0]+Math.sin(t+b[2])*wave*.32,b[1]+Math.cos(t*.83+b[0])*wave*.22,b[2]+Math.sin(t*.71+b[1])*ripple*.16];}
function activeNodes(cam){
  const max=S.mode==="background"?320:S.quality==="performance"?720:1500;
  const c=cam||camera();
  const visible=S.nodes.filter(function(n){
    const p=worldToScreen(nodePosition(n),c);
    return p!==null&&p[0]>-140&&p[0]<canvas.clientWidth+140&&p[1]>-140&&p[1]<canvas.clientHeight+140;
  });
  return visible.slice().sort(function(a,b){
    if(a.kind==="core")return-1;if(b.kind==="core")return 1;
    const da=Math.hypot(a.position[0]-c.eye[0],a.position[1]-c.eye[1],a.position[2]-c.eye[2]);
    const db=Math.hypot(b.position[0]-c.eye[0],b.position[1]-c.eye[1],b.position[2]-c.eye[2]);
    return(b.energy||0)-(a.energy||0)+(da-db)*.0005;
  }).slice(0,max);
}
function simulateFluid(dt,nodes){
  if(S.mode==="background"||S.quality==="minimal"||S.dragNode)return;
  const step=Math.min(34,Math.max(0,dt))*.0015;
  const maxPairs=12000;
  const cellSize=1.8,grid=new Map(),positions=new Map();
  nodes.forEach(function(n){
    const p=nodePosition(n),key=Math.floor(p[0]/cellSize)+":"+Math.floor(p[1]/cellSize)+":"+Math.floor(p[2]/cellSize);
    if(!grid.has(key))grid.set(key,[]);grid.get(key).push(n);positions.set(n.id,p);
  });
  let pairs=0;
  nodes.forEach(function(n){
    const base=n.position,o=S.localOffsets.get(n.id)||[0,0,0],p=positions.get(n.id),v=S.velocities.get(n.id)||[0,0,0];
    let fx=-o[0]*1.65,fy=-o[1]*1.65,fz=-o[2]*1.65;
    const gx=Math.floor(p[0]/cellSize),gy=Math.floor(p[1]/cellSize),gz=Math.floor(p[2]/cellSize);
    for(let ix=-1;ix<=1;ix++)for(let iy=-1;iy<=1;iy++)for(let iz=-1;iz<=1;iz++){
      const bucket=grid.get((gx+ix)+":"+(gy+iy)+":"+(gz+iz));if(!bucket)continue;
      for(const other of bucket){
        if(other.id===n.id||pairs>=maxPairs)continue;
        const q=positions.get(other.id),dx=p[0]-q[0],dy=p[1]-q[1],dz=p[2]-q[2],d=Math.hypot(dx,dy,dz);
        if(d>0&&d<1.55){
          const push=(1.55-d)*1.9/d;fx+=dx*push;fy+=dy*push;fz+=dz*push;pairs++;
        }else if(d>1.55&&d<4.2&&other.kind===n.kind){
          const pull=(d-1.55)*.035;fx-=dx*pull;fy-=dy*pull;fz-=dz*pull;
        }
      }
    }
    v[0]=(v[0]+fx*step)*.93;v[1]=(v[1]+fy*step)*.93;v[2]=(v[2]+fz*step)*.93;
    const next=[o[0]+v[0]*step*18,o[1]+v[1]*step*18,o[2]+v[2]*step*18];
    const mag=Math.hypot(...next);
    const cap=.95;
    if(mag>cap){next[0]*=cap/mag;next[1]*=cap/mag;next[2]*=cap/mag;}
    S.velocities.set(n.id,v);S.localOffsets.set(n.id,next);
  });
}
function resize(){
  const dpr=Math.min(window.devicePixelRatio||1,S.quality==="maximum"?1.5:1.0),w=Math.max(1,Math.floor(canvas.clientWidth*dpr)),h=Math.max(1,Math.floor(canvas.clientHeight*dpr));
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
}
function render(now){
  requestAnimationFrame(render);
  if(document.hidden)return;
  renderMinimap();
  if(S.view==="earth"){resize();renderEarth(now);return;}
  const dt=now-S.lastFrame;S.lastFrame=now;S.frameMs=S.frameMs*.92+dt*.08;
  if(S.mode==="foreground"&&S.frameMs>28)S.quality="performance";
  if(S.mode==="foreground"&&S.frameMs<18&&S.nodes.length<800)S.quality="maximum";
  resize();
  renderNeuralConsolePlacement(false);
  const c=camera();
  const nodes=activeNodes(c);simulateFluid(dt,nodes);
  const aspect=canvas.width/Math.max(1,canvas.height),proj=new Float32Array(16),view=new Float32Array(16),mvp=new Float32Array(16);
  perspective(proj,Math.PI/3,aspect,.05,2000);lookAt(view,c.eye,S.target);multiply(mvp,proj,view);
  gl.clearColor(0,.004,.012,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
  const nowMs=performance.now();
  const cp=new Float32Array(nodes.length*3),cs=new Float32Array(nodes.length),ce=new Float32Array(nodes.length),ph=new Float32Array(nodes.length),se=new Float32Array(nodes.length),sh=new Float32Array(nodes.length),bi=new Float32Array(nodes.length);
  nodes.forEach(function(n,i){cp.set(nodePosition(n),i*3);cs[i]=(n.scale||1)*(n.kind==="core"?1.75:n.kind==="subsystem"?1.30:.72);ce[i]=n.energy||.2;ph[i]=i*.73+(n.id.length%23);se[i]=n.id===S.selected?1:0;sh[i]=shapeCode(n);bi[i]=S.births.get(n.id)||nowMs-900;});
  upload(centerBuf,cp);upload(scaleBuf,cs);upload(energyBuf,ce);upload(phaseBuf,ph);upload(selectedBuf,se);upload(shapeBuf,sh);upload(birthBuf,bi);
  gl.useProgram(droplet);gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uMvp"),false,mvp);gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uView"),false,view);gl.uniform1f(gl.getUniformLocation(droplet,"uTime"),nowMs);
  attr(droplet,"aPos",3,meshPos);attr(droplet,"aNormal",3,meshNormal);attr(droplet,"aCenter",3,centerBuf,1);attr(droplet,"aScale",1,scaleBuf,1);attr(droplet,"aEnergy",1,energyBuf,1);attr(droplet,"aPhase",1,phaseBuf,1);attr(droplet,"aSelected",1,selectedBuf,1);attr(droplet,"aShape",1,shapeBuf,1);attr(droplet,"aBirth",1,birthBuf,1);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,meshIndex);gl.drawElementsInstanced(gl.TRIANGLES,meshCount,gl.UNSIGNED_SHORT,0,nodes.length);

  const map=new Map(nodes.map(function(n){return[n.id,n]})),lp=[],ls=[],lg=[];
  const visibleRelationCap=S.mode==="background"?600:S.quality==="performance"?1200:4200;let relationCount=0;for(const r of S.links){if(relationCount>=visibleRelationCap)break;if(S.dragNode&&(r.source===S.dragNode||r.target===S.dragNode))continue;const a=map.get(r.source),b=map.get(r.target);if(!a||!b)continue;relationCount++;const ap=nodePosition(a),bp=nodePosition(b),mid=[(ap[0]+bp[0])*.5,(ap[1]+bp[1])*.5,(ap[2]+bp[2])*.5],bend=norm(cross(norm(sub(bp,ap)),[0,1,0])),mag=.16+Math.min(1.1,Math.hypot(...sub(bp,ap))*.055),p1=add(mid,mul3(bend,mag)),p2=add(mid,mul3(bend,-mag)),pts=[ap,p1,p1,p2,p2,bp];pts.forEach(function(p,i){lp.push(...p);ls.push(r.strength||.4);lg.push((i%2)*.5);});}
  upload(lineBuf,new Float32Array(lp));upload(lineStrengthBuf,new Float32Array(ls));upload(lineProgressBuf,new Float32Array(lg));
  gl.useProgram(lineProg);gl.uniformMatrix4fv(gl.getUniformLocation(lineProg,"uMvp"),false,mvp);gl.uniform1f(gl.getUniformLocation(lineProg,"uTime"),nowMs);attr(lineProg,"aPos",3,lineBuf);attr(lineProg,"aStrength",1,lineStrengthBuf);attr(lineProg,"aProgress",1,lineProgressBuf);gl.drawArrays(gl.LINES,0,lp.length/3);

  if(S.quality!=="minimal"&&S.particles.length){
    S.particles=S.particles.filter(function(p){p.life+=dt/650;return p.life<1;});
    const pp=[],pl=[],ps=[];S.particles.forEach(function(p){p.pos[0]+=p.vel[0]*dt*.001;p.pos[1]+=p.vel[1]*dt*.001;p.pos[2]+=p.vel[2]*dt*.001;pp.push(...p.pos);pl.push(p.life);ps.push(p.size);});
    upload(particleBuf,new Float32Array(pp));upload(particleLifeBuf,new Float32Array(pl));upload(particleSizeBuf,new Float32Array(ps));
    gl.useProgram(partProg);gl.uniformMatrix4fv(gl.getUniformLocation(partProg,"uMvp"),false,mvp);attr(partProg,"aPos",3,particleBuf);attr(partProg,"aLife",1,particleLifeBuf);attr(partProg,"aSize",1,particleSizeBuf);gl.drawArrays(gl.POINTS,0,S.particles.length);
  }
  rootStatus("AUTO QUALITY · "+S.quality.toUpperCase()+" · "+Math.round(1000/Math.max(1,S.frameMs))+" FPS · "+nodes.length+" ACTIVE");
}
function pickEarthLocator(x,y){
  const oldYaw=S.yaw,oldPitch=S.pitch,oldDistance=S.distance,oldTarget=S.target.slice();
  S.yaw=S.earthYaw;S.pitch=S.earthPitch;S.distance=S.earthDistance;S.target=[0,0,0];
  let best=null,bestD=Infinity;
  for(const item of (Array.isArray(S.earthData.locators)?S.earthData.locators:[])){
    const lat=(Number(item.latitude)||0)*Math.PI/180,lon=(Number(item.longitude)||0)*Math.PI/180;
    const rr=Math.cos(lat)*1.075,p=[rr*Math.cos(lon),Math.sin(lat)*1.075,rr*Math.sin(lon)],screen=worldToScreen(p);
    if(!screen)continue;
    const d=Math.hypot(screen[0]-x,screen[1]-y);
    if(d<bestD){bestD=d;best=item;}
  }
  S.yaw=oldYaw;S.pitch=oldPitch;S.distance=oldDistance;S.target=oldTarget;
  return bestD<55?best:null;
}
function renderEarthLabels(){
  const box=ui.querySelector("#jn-focus");
  const locators=Array.isArray(S.earthData.locators)?S.earthData.locators:[];
  if(S.view==="earth"&&locators.length)box.textContent="GOD'S EYE · "+locators.map(function(x){return String(x.label||"Locator").slice(0,36)}).slice(0,5).join(" · ");
}
function renderEarth(now){
  const oldYaw=S.yaw,oldPitch=S.pitch,oldDistance=S.distance,oldTarget=S.target.slice();
  S.yaw=S.earthYaw;S.pitch=S.earthPitch;S.distance=S.earthDistance;S.target=[0,0,0];
  const c=camera(),proj=new Float32Array(16),view=new Float32Array(16),mvp=new Float32Array(16);
  perspective(proj,Math.PI/3,canvas.width/Math.max(1,canvas.height),.05,100);
  lookAt(view,c.eye,S.target);multiply(mvp,proj,view);
  gl.clearColor(.001,.004,.012,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
  gl.enable(gl.DEPTH_TEST);gl.depthMask(true);gl.disable(gl.BLEND);
  gl.useProgram(earthProg);
  gl.uniformMatrix4fv(gl.getUniformLocation(earthProg,"uMvp"),false,mvp);
  const model=new Float32Array(16);model[0]=model[5]=model[10]=model[15]=1;
  gl.uniformMatrix4fv(gl.getUniformLocation(earthProg,"uModel"),false,model);
  attr(earthProg,"aPos",3,earthPos);attr(earthProg,"aNormal",3,earthNormal);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,earthIndex);gl.drawElements(gl.TRIANGLES,earthIndexCount,gl.UNSIGNED_SHORT,0);

  const locators=Array.isArray(S.earthData.locators)?S.earthData.locators:[];
  if(locators.length){
    const cp=new Float32Array(locators.length*3),cs=new Float32Array(locators.length),ce=new Float32Array(locators.length),ph=new Float32Array(locators.length),sel=new Float32Array(locators.length),sh=new Float32Array(locators.length),bi=new Float32Array(locators.length);
    locators.forEach(function(item,i){
      const lat=(Number(item.latitude)||0)*Math.PI/180,lon=(Number(item.longitude)||0)*Math.PI/180;
      const r=1.075,rr=Math.cos(lat)*r;
      cp.set([rr*Math.cos(lon),Math.sin(lat)*r,rr*Math.sin(lon)],i*3);
      cs[i]=.10;ce[i]=1;ph[i]=i*.91;sel[i]=0;sh[i]=1;bi[i]=now-1700;
    });
    gl.enable(gl.BLEND);gl.depthMask(false);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
    upload(earthCenterBuf,cp);upload(earthScaleBuf,cs);upload(earthEnergyBuf,ce);upload(earthPhaseBuf,ph);upload(earthSelectedBuf,sel);upload(earthShapeBuf,sh);upload(earthBirthBuf,bi);
    gl.useProgram(droplet);
    gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uMvp"),false,mvp);
    gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uView"),false,view);
    gl.uniform1f(gl.getUniformLocation(droplet,"uTime"),now);
    attr(droplet,"aPos",3,meshPos);attr(droplet,"aNormal",3,meshNormal);attr(droplet,"aCenter",3,earthCenterBuf,1);attr(droplet,"aScale",1,earthScaleBuf,1);attr(droplet,"aEnergy",1,earthEnergyBuf,1);attr(droplet,"aPhase",1,earthPhaseBuf,1);attr(droplet,"aSelected",1,earthSelectedBuf,1);attr(droplet,"aShape",1,earthShapeBuf,1);attr(droplet,"aBirth",1,earthBirthBuf,1);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,meshIndex);gl.drawElementsInstanced(gl.TRIANGLES,meshCount,gl.UNSIGNED_SHORT,0,locators.length);
  }
  S.yaw=oldYaw;S.pitch=oldPitch;S.distance=oldDistance;S.target=oldTarget;
  ui.querySelector("#jn-title").textContent="GOD'S EYE";
  renderEarthLabels();
  ui.querySelector("#jn-status").textContent="3D EARTH · "+locators.length+" LOCATORS · "+(S.earthData.authorized_current?"CURRENT LOCATION AUTHORIZED":"CURRENT LOCATION UNAVAILABLE");
}
async function pollEarth(){
  const a=api();if(!a||!a.gods_eye_globe)return;
  try{S.earthData=await a.gods_eye_globe();}catch(_){}
  S.earthLastPoll=performance.now();
}
async function pollObservation(){
  const a=api();if(!a||!a.neural_observation_state)return;
  try{
    S.observation=await a.neural_observation_state();
    const box=ui.querySelector("#jn-observe");
    if(S.observation&&S.observation.enabled){
      const events=await a.neural_events(S.observationSequence,40);
      let lines=[];
      for(const e of Array.isArray(events)?events:[]){
        S.observationSequence=Math.max(S.observationSequence,Number(e.sequence)||0);
        if(e.kind==="task.progress"&&e.entity_id)S.followTask=e.entity_id;
        if(e.kind&&String(e.kind).startsWith("observation.")){lines.push(String(e.payload&&e.payload.message||e.kind).slice(0,120));}
      }
      if(S.follow&&S.followTask){const taskNode=S.nodes.find(function(n){return n.id===S.followTask});if(taskNode){S.selected=taskNode.id;S.target=[...nodePosition(taskNode)];}}
      box.textContent=(S.observation.focus||"auto").toUpperCase()+" · "+(lines.length?lines.slice(-6).join("  •  "):S.observation.reason||"OBSERVING");
      box.classList.add("visible");
    }else{
      box.classList.remove("visible");box.textContent="";
    }
  }catch(_){}
}
async function moveHandWindow(el,dx,dy){
  const key=String(el&&el.dataset.handle||"");if(!key)return;
  const x=(Number(el.dataset.x)||0)+dx,y=(Number(el.dataset.y)||0)+dy;
  el.dataset.x=String(x);el.dataset.y=String(y);applySurfaceTransform(el);
  const info=S.windows.find(function(item){return String(item.handle)===key}),a=api();
  if(info&&a&&a.spatial_window_move_resize&&info.embedded){
    const rect=el.getBoundingClientRect();try{await a.spatial_window_move_resize(Number(info.handle),Math.round(x),Math.round(y),Math.max(80,Math.round(rect.width)),Math.max(60,Math.round(rect.height)));}catch(_){}
  }
}
async function pollHand(){
  if(S.view==="earth")return;
  try{
    const response=await fetch("http://127.0.0.1:8795/hand/state",{cache:"no-store"});
    if(!response.ok)return;
    const data=await response.json();
    S.hand=data||{enabled:false};
    if(!S.hand.enabled||!S.hand.sample)return;
    const sample=S.hand.sample;
    const x=Math.max(0,Math.min(1,Number(sample.x)||0))*canvas.clientWidth;
    const y=Math.max(0,Math.min(1,Number(sample.y)||0))*canvas.clientHeight;
    if(Boolean(sample.pinch)&&!S.handPinching){
      const target=document.elementFromPoint(x,y);const surface=target&&target.closest?target.closest(".jn-spatial-window"):null;
      if(surface){S.handWindow=surface;S.handX=x;S.handY=y;}else{const node=pick(x,y);if(node){S.handNode=node.id;S.selected=node.id;S.handX=x;S.handY=y;}}
      S.handPinching=true;
    }else if(Boolean(sample.pinch)&&S.handPinching&&S.handWindow){
      const dx=x-S.handX,dy=y-S.handY;await moveHandWindow(S.handWindow,dx,dy);S.handX=x;S.handY=y;
    }else if(Boolean(sample.pinch)&&S.handPinching&&S.handNode){
      const dx=x-S.handX,dy=y-S.handY;
      const node=S.nodes.find(function(item){return item.id===S.handNode});
      if(node){
        const p=worldToScreen(nodePosition(node));
        if(p){
          const delta=screenDelta(dx,dy,p[2]),old=S.localOffsets.get(node.id)||[0,0,0];
          S.localOffsets.set(node.id,add(old,delta));
          spawn(nodePosition(node),Math.max(1,Math.floor(Math.hypot(dx,dy)/16)));
        }
      }
      S.handX=x;S.handY=y;
    }else if(!Boolean(sample.pinch)&&S.handPinching){
      if(S.handWindow){S.handWindow=null;}
      if(S.handNode){
        const id=S.handNode,from=S.localOffsets.get(id)||[0,0,0],start=performance.now();S.handNode=null;
        function settleHand(){const t=Math.min(1,(performance.now()-start)/780),e=t*t*(3-2*t);S.localOffsets.set(id,[from[0]*(1-e),from[1]*(1-e),from[2]*(1-e)]);if(t<1)requestAnimationFrame(settleHand);else S.localOffsets.delete(id);}
        requestAnimationFrame(settleHand);
      }
      S.handPinching=false;
    }
    if(Number(sample.fingers)===2&&Number.isFinite(S.handY)){
      const dy=y-S.handY;
      if(Math.abs(dy)>6)S.distance=Math.max(3.5,Math.min(180,S.distance*Math.exp(dy*.0015)));
    }
    S.handX=x;S.handY=y;
  }catch(_){}
  S.lastHandPoll=performance.now();
}
function renderMinimap(){
  const c=ui.querySelector("#jn-minimap");if(!S.minimap||S.view!=="network"){c.classList.remove("visible");return;}
  c.classList.add("visible");const g=c.getContext("2d");if(!g)return;g.clearRect(0,0,c.width,c.height);
  const nodes=S.nodes.slice(0,420),sx=c.width*.5,sy=c.height*.5;
  nodes.forEach(function(n){const x=sx+n.position[0]*4.2,y=sy+n.position[2]*3.0;g.fillStyle=n.id===S.selected?"#dff6ff":"#3aa8ee";g.globalAlpha=Math.max(.18,Math.min(.9,(n.energy||.2)));g.fillRect(x,y,n.id===S.selected?3:1.5,n.id===S.selected?3:1.5);});
  g.globalAlpha=.5;g.strokeStyle="#3aa8ee";g.strokeRect(sx-2,sy-2,4,4);
}
function rootStatus(text){ui.querySelector("#jn-perf").textContent=text}
function worldToScreen(p){
  const c=camera(),rel=sub(p,c.eye),depth=rel[0]*c.forward[0]+rel[1]*c.forward[1]+rel[2]*c.forward[2];if(depth<=.1)return null;
  const focal=canvas.clientHeight/(2*Math.tan(Math.PI/6));
  return[canvas.clientWidth/2+(rel[0]*c.right[0]+rel[1]*c.right[1]+rel[2]*c.right[2])*focal/depth,canvas.clientHeight/2-(rel[0]*c.up[0]+rel[1]*c.up[1]+rel[2]*c.up[2])*focal/depth,depth];
}
function clampNumber(v,low,high){return Math.max(low,Math.min(high,v));}
function appendConsoleMessage(kind,text){
  const log=ui.querySelector("#jn-console-log");if(!log)return;
  const row=document.createElement("div");row.className="jn-console-message "+(kind==="user"?"user":"system");row.textContent=String(text||"").slice(0,1600);
  log.appendChild(row);
  while(log.children.length>10)log.removeChild(log.firstChild);
  log.scrollTop=log.scrollHeight;
}
function setConsoleStatus(text){
  const status=ui.querySelector("#jn-console-status");if(status)status.textContent=String(text||"").slice(0,90);
}
function setConsoleCollapsed(collapsed){
  S.consoleCollapsed=Boolean(collapsed);
  const el=ui.querySelector("#jn-neural-console");if(!el)return;
  el.classList.toggle("jn-console-collapsed",S.consoleCollapsed);
  const button=ui.querySelector("#jn-console-collapse");if(button)button.textContent=S.consoleCollapsed?"OPEN":"MIN";
  try{localStorage.setItem("jarvis.neuralCommand.collapsed",S.consoleCollapsed?"1":"0");}catch(_){}
  requestAnimationFrame(function(){renderNeuralConsolePlacement(true);});
}
function renderNeuralConsolePlacement(force){
  const now=performance.now();
  if(!force&&now-S.lastConsoleLayout<S.consoleLayoutMs)return;
  S.lastConsoleLayout=now;
  const el=ui.querySelector("#jn-neural-console"),tether=ui.querySelector("#jn-console-tether");if(!el)return;
  const width=canvas.clientWidth,height=canvas.clientHeight;if(width<1||height<1)return;
  let corePos=[0,0,0],coreScreen=null,anchorScreen=null;
  const core=S.nodes.find(function(n){return n.id==="jarvis.core";});
  if(core){
    corePos=nodePosition(core);
    coreScreen=worldToScreen(corePos);
    const c=camera();
    const commandAnchor=S.nodes.find(function(n){return n.id==="jarvis.neural-command";});
    const commandPos=commandAnchor?nodePosition(commandAnchor):add(add(corePos,mul3(c.right,2.7)),mul3(c.up,-2.0));
    const anchor=add(add(commandPos,mul3(c.right,2.1)),mul3(c.up,-1.25));
    anchorScreen=worldToScreen(anchor);
  }
  let x=width*.5,y=height*.5,depth=16;
  if(S.view==="earth"){y=height-132;}
  else if(anchorScreen){x=anchorScreen[0];y=anchorScreen[1];depth=anchorScreen[2]||16;}
  else if(coreScreen){x=coreScreen[0];y=coreScreen[1]+115;depth=coreScreen[2]||16;}
  const w=el.offsetWidth||520,h=el.offsetHeight||(S.consoleCollapsed?46:156);
  const margin=14,top=76,bottom=16;
  x=clampNumber(x-w*.5,margin,Math.max(margin,width-w-margin));
  y=clampNumber(y-h*.5,top,Math.max(top,height-h-bottom));
  const scale=clampNumber(.88+18/(depth+42),.88,1.04);
  el.style.transform="translate3d("+Math.round(x)+"px,"+Math.round(y)+"px,0) scale("+scale.toFixed(3)+")";
  if(tether){
    if(S.view==="earth"||!coreScreen){tether.style.width="0";tether.style.opacity="0";}
    else{
      const ex=x+w*.5,ey=y+h*.5,dx=ex-coreScreen[0],dy=ey-coreScreen[1],length=Math.hypot(dx,dy);
      tether.style.width=Math.round(length)+"px";tether.style.opacity=length>12?".75":"0";
      tether.style.transform="translate3d("+Math.round(coreScreen[0])+"px,"+Math.round(coreScreen[1])+"px,0) rotate("+Math.atan2(dy,dx)+"rad)";
    }
  }
}

function screenDelta(dx,dy,depth){const c=camera(),f=canvas.clientHeight/(2*Math.tan(Math.PI/6));return add(mul3(c.right,dx*depth/f),mul3(c.up,-dy*depth/f))}
function pick(x,y){
  let best=null,bestD=Infinity;
  for(const n of activeNodes()){const p=worldToScreen(nodePosition(n),camera());if(!p)continue;const d=Math.hypot(p[0]-x,p[1]-y);if(d<bestD){bestD=d;best=n;}}
  return bestD<75?best:null;
}
function focus(n){
  S.selected=n.id;S.target=[...nodePosition(n)];if(S.follow){S.yaw+=.0008;S.pitch+=.0004;}S.distance=Math.max(5,Math.min(90,11/Math.max(.5,n.scale||1)));
  ui.querySelector("#jn-name").textContent=n.label;ui.querySelector("#jn-meta").textContent=n.kind+" · "+n.status+" · "+n.source+" · "+n.lifecycle;
  ui.querySelector("#jn-inspector").classList.add("visible");ui.querySelector("#jn-focus").textContent="FOCUS · "+n.label;
}
function spawn(pos,count){
  if(S.quality==="minimal")return;
  for(let i=0;i<Math.min(5,count||2);i++)S.particles.push({pos:[...pos],vel:[(Math.random()-.5)*1.1,(Math.random()-.5)*1.1,(Math.random()-.5)*1.1],life:0,size:5+Math.random()*8});
  if(S.particles.length>180)S.particles.splice(0,S.particles.length-180);
}
function api(){return window.pywebview&&window.pywebview.api}
async function pollAdvanced(){
  const a=api();if(!a||!a.neural_advanced_tick)return;
  try{
    const active=S.nodes.length?Math.min(1,S.nodes.reduce(function(sum,n){return sum+(Number(n.energy)||0)},0)/Math.max(1,S.nodes.length)):0.35;
    const d=await a.neural_advanced_tick(0.016,active);
    S.advanced=d||{physics:{}};
    const p=S.advanced.physics||{};
    ui.querySelector("#jn-ecology").textContent="FLUID ECOLOGY · ENERGY "+Math.round((Number(p.energy_current)||0)*100)+"% · TURB "+Math.round((Number(p.local_turbulence)||0)*100)+"%";
    S.lastAdvanced=performance.now();
  }catch(_){}
}
async function pollSnapshot(){
  const a=api();if(!a||!a.neural_world_snapshot)return;
  try{
    const d=await a.neural_world_snapshot(S.quality==="maximum"?2200:900);
    S.nodes=Array.isArray(d.entities)?d.entities:[];S.links=Array.isArray(d.relations)?d.relations:[];S.windows=Array.isArray(d.windows)?d.windows:[];
    S.quality=d.performance&&d.performance.quality||S.quality;S.mode=d.performance&&d.performance.mode||S.mode;
    ui.querySelector("#jn-status").textContent="NEURAL MESH · "+S.nodes.length+" NEURONS · "+S.links.length+" LINKS · "+S.windows.length+" WINDOWS";
    S.lastSnapshot=performance.now();renderSpatialWindows();
  }catch(_){ui.querySelector("#jn-status").textContent="NEURAL MESH · BACKEND DEGRADED";}
}
async function pollEvents(){
  const a=api();if(!a||!a.neural_events)return;
  try{
    const list=await a.neural_events(S.eventSequence,300);
    for(const e of Array.isArray(list)?list:[]){S.eventSequence=Math.max(S.eventSequence,Number(e.sequence)||0);if(e.kind==="entity.created")S.births.set(e.entity_id,performance.now());else if(e.kind==="entity.retired")S.retirements.set(e.entity_id,performance.now());}
    S.lastEvents=performance.now();
  }catch(_){}
}
async function pollLayouts(){
  const a=api();if(!a||!a.neural_window_list_states)return;
  try{
    const states=await a.neural_window_list_states();
    S.layouts=new Map((Array.isArray(states)?states:[]).map(function(item){return[String(item.key),item]}));
    S.lastLayoutPoll=performance.now();
    renderSpatialWindows();
  }catch(_){}
}
async function pollWindows(){
  if(!S.showWindows)return;
  const a=api();if(!a||!a.spatial_windows_catalog)return;
  try{const list=await a.spatial_windows_catalog();S.windows=Array.isArray(list)?list:[];S.lastWindows=performance.now();renderSpatialWindows();}catch(_){}
}
function makeSurface(info){
  const el=document.createElement("div");el.className="jn-spatial-window";el.dataset.handle=String(info.handle);
  el.innerHTML='<div class="jn-window-head"><span class="jn-window-title"></span><span class="jn-window-status"></span></div><div class="jn-window-empty">LIVE APPLICATION SURFACE</div><div class="jn-window-resize"></div>';
  el.querySelector(".jn-window-title").textContent=String(info.title||"Window").slice(0,80);
  el.querySelector(".jn-window-status").textContent=info.presentation&&info.presentation.windows_graphics_capture?"GFX CAPTURE":"NATIVE";
  const head=el.querySelector(".jn-window-head");
  head.addEventListener("pointerdown",function(e){
    e.stopPropagation();head.setPointerCapture(e.pointerId);head.dataset.dragging="1";head.dataset.x=String(parseFloat(el.dataset.x)||0);head.dataset.y=String(parseFloat(el.dataset.y)||0);head.dataset.lastX=String(e.clientX);head.dataset.lastY=String(e.clientY);
  });
  head.addEventListener("pointermove",function(e){
    if(head.dataset.dragging!=="1")return;
    const dx=e.clientX-Number(head.dataset.lastX),dy=e.clientY-Number(head.dataset.lastY);
    head.dataset.lastX=String(e.clientX);head.dataset.lastY=String(e.clientY);
    const x=Number(head.dataset.x)+dx,y=Number(head.dataset.y)+dy;head.dataset.x=String(x);head.dataset.y=String(y);el.dataset.x=String(x);el.dataset.y=String(y);applySurfaceTransform(el);
  });
  const finish=function(){
    if(head.dataset.dragging!=="1")return;head.dataset.dragging="0";
    const key="window:"+info.handle;const x=Number(el.dataset.x)||0,y=Number(el.dataset.y)||0;
    const nativeApi=api();
    if(nativeApi&&nativeApi.spatial_window_move_resize&&info.embedded){const w=Math.max(80,Math.round(el.getBoundingClientRect().width)),h=Math.max(60,Math.round(el.getBoundingClientRect().height));nativeApi.spatial_window_move_resize(Number(info.handle),Math.round(x),Math.round(y),w,h).catch(function(){});}
    clearTimeout(S.layoutTimers.get(key));S.layoutTimers.set(key,setTimeout(async function(){const a=api();if(a&&a.neural_window_set_state){try{await a.neural_window_set_state(key,{position:[x/70,-y/70,3.5],scale:S.giant?1.28:1});}catch(_){}}},160));
  };
  head.addEventListener("pointerup",finish);head.addEventListener("pointercancel",finish);
  attachResize(info,el);
  el.addEventListener("dblclick",async function(e){e.stopPropagation();const a=api();if(a&&a.spatial_window_focus)try{await a.spatial_window_focus(Number(info.handle));}catch(_){}});
  return el;
}
function attachResize(info,el){
  const grip=el.querySelector(".jn-window-resize");if(!grip)return;
  grip.addEventListener("pointerdown",function(e){
    e.stopPropagation();grip.setPointerCapture(e.pointerId);grip.dataset.dragging="1";
    grip.dataset.startX=String(e.clientX);grip.dataset.startY=String(e.clientY);
    grip.dataset.startScale=String(Number(el.dataset.scale)||1);
  });
  const end=function(){
    if(grip.dataset.dragging!=="1")return;grip.dataset.dragging="0";
    const key="window:"+info.handle;const scale=Math.max(.20,Math.min(4,Number(el.dataset.scale)||1));
    const x=Number(el.dataset.x)||0,y=Number(el.dataset.y)||0;
    const apiObj=api();
    if(apiObj&&apiObj.neural_window_set_state)apiObj.neural_window_set_state(key,{position:[x/70,-y/70,3.5],scale}).catch(function(){});
    if(apiObj&&apiObj.spatial_window_move_resize&&info.embedded){const rect=el.getBoundingClientRect();apiObj.spatial_window_move_resize(Number(info.handle),Math.round(x),Math.round(y),Math.max(80,Math.round(rect.width)),Math.max(60,Math.round(rect.height))).catch(function(){});}
  };
  grip.addEventListener("pointermove",function(e){
    if(grip.dataset.dragging!=="1")return;
    const startScale=Number(grip.dataset.startScale)||1;
    const delta=(e.clientX-Number(grip.dataset.startX))+(e.clientY-Number(grip.dataset.startY));
    el.dataset.scale=String(Math.max(.20,Math.min(4,startScale+delta/420)));
    applySurfaceTransform(el);
  });
  grip.addEventListener("pointerup",end);grip.addEventListener("pointercancel",end);
}
async function preview(info,el,index){
  if(index>2||S.quality==="minimal")return;
  const a=api();if(!a||!a.spatial_window_capture)return;
  if(info.embedded)return;
  try{const cap=await a.spatial_window_capture(Number(info.handle),S.giant?1000:720);if(!cap||!cap.png_base64)return;const img=document.createElement("img");img.className="jn-window-preview";img.alt="";img.src="data:image/png;base64,"+cap.png_base64;const old=el.querySelector(".jn-window-empty,.jn-window-preview");if(old)old.replaceWith(img);}catch(_){}
}
function setSurfaceMode(mode){
  S.surfaceMode=mode==="2d"?"2d":"3d";
  const layer=ui.querySelector("#jn-surfaces");
  layer.classList.toggle("flat-2d",S.surfaceMode==="2d");
  ui.querySelector("#jn-mode").textContent=S.surfaceMode.toUpperCase();
  renderSpatialWindows();
}
function surfaceShapeClass(shape){const n=String(shape&&shape.name||"rectangle").toLowerCase();const m={circle:"circle",sphere:"circle",oval:"oval",pill:"pill",hexagon:"hex",hex:"hex",diamond:"diamond",triangle:"triangle",star:"star"};return m[n]||"";}
function applySurfaceTransform(el){
  const x=Number(el.dataset.x)||0,y=Number(el.dataset.y)||0,scale=Number(el.dataset.scale)||1,z=Number(el.dataset.z)||0;
  el.style.transform="translate3d("+x+"px,"+y+"px,"+z+"px) scale("+scale+")";
}
async function syncEmbeddedVisibility(){
  const now=performance.now();
  if(now-S.lastNativeVisibility<S.nativeVisibilityMs)return;
  S.lastNativeVisibility=now;
  const a=api();if(!a||!a.spatial_window_visibility)return;
  const hidden=document.hidden||S.mode==="background";
  for(const info of S.windows){
    if(!info.embedded)continue;
    const el=ui.querySelector('.jn-spatial-window[data-handle="'+String(info.handle).replace(/"/g,"")+'"]');
    const visible=!hidden&&el?(()=>{
      const rect=el.getBoundingClientRect();
      return rect.right>0&&rect.bottom>0&&rect.left<window.innerWidth&&rect.top<window.innerHeight;
    })():false;
    try{await a.spatial_window_visibility(Number(info.handle),visible);}catch(_){}
  }
}
function renderSpatialWindows(){
  const layer=ui.querySelector("#jn-surfaces");if(!S.showWindows){layer.replaceChildren();return;}
  const current=new Map(Array.from(layer.children).map(function(e){return[e.dataset.handle,e]})),keep=new Set();
  S.windows.slice().sort(function(a,b){return(Number(Boolean(a.minimized))-Number(Boolean(b.minimized)))}).forEach(function(info,index){
    const key=String(info.handle);keep.add(key);let el=current.get(key);if(!el)el=makeSurface(info);
    el.classList.toggle("giant",S.giant);
    for(const cls of ["shape-circle","shape-oval","shape-pill","shape-hex","shape-diamond","shape-triangle","shape-star"])el.classList.remove(cls);
    const saved=S.layouts.get("window:"+info.handle);
    if(saved&&saved.shape){const cls=surfaceShapeClass(saved.shape);if(cls)el.classList.add("shape-"+cls);}

    if(saved&&Array.isArray(saved.position)){
      el.dataset.x=String(Number(saved.position[0]||0)*70);
      el.dataset.y=String(-Number(saved.position[1]||0)*70);
      el.dataset.z=String(Number(saved.position[2]||(-index*25)));
      el.dataset.scale=String(Math.max(.05,Math.min(4,Number(saved.scale||1))));
    }else{
      if(!Number.isFinite(Number(el.dataset.x)))el.dataset.x=String(110+(index%4)*390);
      if(!Number.isFinite(Number(el.dataset.y)))el.dataset.y=String(120+Math.floor(index/4)*280);
      if(!Number.isFinite(Number(el.dataset.z)))el.dataset.z=String(-index*25);
      el.dataset.scale=String(S.giant?1.28:1);
    }
    if(S.giant&&!saved)el.dataset.scale="1.28";
    applySurfaceTransform(el);
    if(!el.parentNode)layer.appendChild(el);
    preview(info,el,index);
  });
  for(const[key,el]of current)if(!keep.has(key))el.remove();
}
async function traceSelected(){
  if(!S.selected)return;
  const a=api();if(!a||!a.neural_trace)return;
  try{
    const path=await a.neural_trace("jarvis.core",S.selected,12);
    S.tracePath=Array.isArray(path)?path:[];S.traceIndex=0;
    if(S.traceTimer)clearInterval(S.traceTimer);
    if(!S.tracePath.length)return;
    const step=function(){
      const item=S.tracePath[S.traceIndex++];
      if(!item||S.traceIndex>S.tracePath.length){clearInterval(S.traceTimer);S.traceTimer=null;return;}
      const node=S.nodes.find(function(n){return n.id===item.to});
      if(node)focus(node);
    };
    step();S.traceTimer=setInterval(step,760);
  }catch(_){}
}
function buildSearchFilters(){
  return {
    kind:(ui.querySelector("#jn-kind")||{}).value||null,
    lifecycle:(ui.querySelector("#jn-life")||{}).value||null,
    connected_to:(ui.querySelector("#jn-connected")||{}).value||null,
    source:(ui.querySelector("#jn-source")||{}).value||null,
    updated_within_seconds:Number((ui.querySelector("#jn-age")||{}).value)||null
  };
}
async function search(value){
  const a=api();
  const filters=buildSearchFilters();
  const hasFilter=Boolean(value.trim()||filters.kind||filters.lifecycle||filters.connected_to||filters.source||filters.updated_within_seconds);
  if(!hasFilter||!a)return;
  try{
    if(S.view==="earth"&&a.gods_eye_globe_search&&value.trim()){
      S.earthData=await a.gods_eye_globe_search(value.trim());
      const box=ui.querySelector("#jn-response");box.textContent=(S.earthData.locators&&S.earthData.locators.length)?("Located "+S.earthData.locators[0].label):"No Earth locations found";box.classList.add("visible");return;
    }
    if(!a.neural_search)return;
    const r=await a.neural_search(value.trim()||"",filters.kind,filters.source,null,filters.lifecycle,filters.connected_to,filters.updated_within_seconds,12);
    if(r.length){focus(r[0]);const box=ui.querySelector("#jn-response");box.textContent="Located "+r[0].label;box.classList.add("visible");}
  }catch(_){ }
}
async function chat(){
  const input=ui.querySelector("#jn-chat-input"),value=input.value.trim(),a=api();if(!value||!a||!a.submit_text)return;
  appendConsoleMessage("user",value);
  input.disabled=true;
  setConsoleStatus("PROCESSING · NEURAL LINK ACTIVE");
  ui.querySelector("#jn-status").textContent="JARVIS · PROCESSING";
  try{
    let result=await a.submit_text(value,false);
    if(result&&result.needs_confirmation){
      appendConsoleMessage("system",result.text||"Jarvis requires confirmation.");
      setConsoleStatus("AWAITING CONFIRMATION");
      const accepted=window.confirm(result.text||"Jarvis requires confirmation.");
      if(accepted)result=await a.submit_text(value,true);
      else result={text:"Command cancelled."};
    }
    const response=(result&&(result.text||result.error))||"Done.";
    appendConsoleMessage("system",response);
    const box=ui.querySelector("#jn-response");box.textContent=response;box.classList.add("visible");
    input.value="";input.style.height="auto";
    setConsoleStatus("3D CORE LINK · ALWAYS IN VIEW");
    await pollSnapshot();
  }catch(e){
    const message="Request failed: "+String(e);
    appendConsoleMessage("system",message);
    const box=ui.querySelector("#jn-response");box.textContent=message;box.classList.add("visible");
    setConsoleStatus("LINK ERROR · RETRY READY");
  }finally{
    input.disabled=false;input.focus();
    resizeNeuralComposer();
    renderNeuralConsolePlacement(true);
  }
}
function resizeNeuralComposer(){
  const input=ui.querySelector("#jn-chat-input");if(!input)return;
  input.style.height="auto";
  input.style.height=Math.min(92,Math.max(34,input.scrollHeight))+"px";
  renderNeuralConsolePlacement(true);
}
function toggleNeuralConsole(){
  setConsoleCollapsed(!S.consoleCollapsed);
  const input=ui.querySelector("#jn-chat-input");
  if(!S.consoleCollapsed&&input)window.setTimeout(function(){input.focus();},0);
}
window.jarvisNeuralCommandSurface={
  setVisible:function(visible){
    const el=ui.querySelector("#jn-neural-console"),tether=ui.querySelector("#jn-console-tether");
    if(el)el.style.display=visible?"":"none";
    if(tether)tether.style.display=visible?"":"none";
    if(visible){renderNeuralConsolePlacement(true);const input=ui.querySelector("#jn-chat-input");if(input)input.focus();}
  },
  focus:function(){
    const input=ui.querySelector("#jn-chat-input");if(input)input.focus();
  }
};
canvas.addEventListener("pointerdown",function(e){
  if(S.view==="earth"){const locator=pickEarthLocator(e.clientX,e.clientY);if(locator){ui.querySelector("#jn-name").textContent=String(locator.label||"Locator");ui.querySelector("#jn-meta").textContent="GOD'S EYE · "+String(locator.kind||"location")+" · "+String(locator.source||"authorized");ui.querySelector("#jn-inspector").classList.add("visible");ui.querySelector("#jn-focus").textContent="LOCATOR · "+String(locator.label||"");}S.orbit=true;S.lastX=e.clientX;S.lastY=e.clientY;canvas.classList.add("dragging");canvas.setPointerCapture(e.pointerId);return;}
  const n=pick(e.clientX,e.clientY);S.lastX=e.clientX;S.lastY=e.clientY;S.pointerMoved=false;
  if(n){S.dragNode=n.id;S.selected=n.id;canvas.setPointerCapture(e.pointerId);return;}
  S.orbit=true;canvas.classList.add("dragging");canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove",function(e){
  const dx=e.clientX-S.lastX,dy=e.clientY-S.lastY;
  if(S.view==="earth"){if(S.orbit){S.earthYaw+=dx*.01;S.earthPitch=Math.max(-1.1,Math.min(1.1,S.earthPitch+dy*.007));S.lastX=e.clientX;S.lastY=e.clientY;}return;}
  if(S.dragNode){
    const n=S.nodes.find(function(x){return x.id===S.dragNode});if(n){const p=worldToScreen(nodePosition(n));if(p){const delta=screenDelta(dx,dy,p[2]),old=S.localOffsets.get(n.id)||[0,0,0];S.localOffsets.set(n.id,add(old,delta));spawn(nodePosition(n),Math.max(1,Math.floor(Math.hypot(dx,dy)/14)));}}
  }else if(S.orbit){S.yaw+=dx*.008;S.pitch=Math.max(-1.35,Math.min(1.35,S.pitch+dy*.006));}
  S.lastX=e.clientX;S.lastY=e.clientY;S.pointerMoved=true;
});
function release(){
  S.orbit=false;canvas.classList.remove("dragging");
  if(S.dragNode){
    const id=S.dragNode,from=S.localOffsets.get(id)||[0,0,0],start=performance.now();S.dragNode=null;
    function settle(){const t=Math.min(1,(performance.now()-start)/780),e=t*t*(3-2*t);S.localOffsets.set(id,[from[0]*(1-e),from[1]*(1-e),from[2]*(1-e)]);if(t<1)requestAnimationFrame(settle);else S.localOffsets.delete(id);}
    requestAnimationFrame(settle);
  }
}
canvas.addEventListener("pointerup",function(){S.orbit=false;release()});
canvas.addEventListener("pointercancel",function(){release()});
canvas.addEventListener("wheel",function(e){e.preventDefault();S.distance=Math.max(3.5,Math.min(180,S.distance*Math.exp(e.deltaY*.001)));},{passive:false});
canvas.addEventListener("dblclick",function(e){const n=pick(e.clientX,e.clientY);if(n)focus(n)});
ui.querySelector("#jn-search").addEventListener("input",function(e){clearTimeout(S.searchTimer);S.searchTimer=setTimeout(function(){search(e.target.value)},260)});
ui.querySelector("#jn-kind").addEventListener("change",function(){search(ui.querySelector("#jn-search").value)});
ui.querySelector("#jn-life").addEventListener("change",function(){search(ui.querySelector("#jn-search").value)});
ui.querySelector("#jn-connected").addEventListener("input",function(){clearTimeout(S.searchTimer);S.searchTimer=setTimeout(function(){search(ui.querySelector("#jn-search").value)},260)});
ui.querySelector("#jn-source").addEventListener("input",function(){clearTimeout(S.searchTimer);S.searchTimer=setTimeout(function(){search(ui.querySelector("#jn-search").value)},260)});
ui.querySelector("#jn-age").addEventListener("change",function(){search(ui.querySelector("#jn-search").value)});
ui.querySelector("#jn-follow").addEventListener("click",function(){S.follow=!S.follow;if(!S.follow)S.followTask=null;ui.querySelector("#jn-follow").textContent=S.follow?"FOLLOWING":"FOLLOW";});
ui.querySelector("#jn-map").addEventListener("click",function(){S.minimap=!S.minimap;ui.querySelector("#jn-map").textContent=S.minimap?"MAP ON":"MAP";renderMinimap();});
ui.querySelector("#jn-trace").addEventListener("click",traceSelected);
ui.querySelector("#jn-home").addEventListener("click",function(){S.view="network";S.target=[0,0,0];S.distance=20;S.yaw=.2;S.pitch=-.12;ui.querySelector("#jn-title").textContent="JARVIS"});
ui.querySelector("#jn-earth").addEventListener("click",function(){S.view=S.view==="earth"?"network":"earth";if(S.view==="earth"){S.target=[0,0,0];pollEarth();}});
ui.querySelector("#jn-mode").addEventListener("click",function(){setSurfaceMode(S.surfaceMode==="3d"?"2d":"3d")});
ui.querySelector("#jn-windows").addEventListener("click",function(){S.showWindows=!S.showWindows;ui.querySelector("#jn-windows").textContent=S.showWindows?"WINDOWS":"WINDOWS OFF";renderSpatialWindows()});
ui.querySelector("#jn-giant").addEventListener("click",function(){S.giant=!S.giant;ui.querySelector("#jn-giant").textContent=S.giant?"NORMAL":"GIANT";renderSpatialWindows()});
ui.querySelector("#jn-perf-btn").addEventListener("click",async function(){const a=api(),next=S.mode==="foreground"?"background":"foreground";if(a&&a.neural_set_performance_mode)try{const r=await a.neural_set_performance_mode(next);S.mode=r.mode||next;S.quality=r.quality||S.quality;}catch(_){}});
ui.querySelector("#jn-freeze").addEventListener("click",function(){S.frozen=!S.frozen;ui.querySelector("#jn-freeze").textContent=S.frozen?"UNFREEZE":"FREEZE"});
ui.querySelector("#jn-chat-send").addEventListener("click",chat);
ui.querySelector("#jn-chat-input").addEventListener("input",resizeNeuralComposer);
ui.querySelector("#jn-chat-input").addEventListener("keydown",function(e){if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();chat()}});
ui.querySelector("#jn-console-float").addEventListener("click",async function(){
  const a=api();
  if(!a||!a.toggle_text_link){appendConsoleMessage("system","Desktop floating link is unavailable in this build.");return;}
  try{
    await a.toggle_text_link(true);
    setConsoleStatus("FLOATING LINK · DESKTOP-WIDE");
    appendConsoleMessage("system","Floating neural command link opened. Use Ctrl+Alt+Shift+F12 to toggle it anywhere.");
  }catch(e){
    appendConsoleMessage("system","Could not open floating link: "+String(e));
  }
});
ui.querySelector("#jn-console-collapse").addEventListener("click",toggleNeuralConsole);
ui.querySelector("#jn-console-hotkey").addEventListener("click",function(){setConsoleCollapsed(false);const input=ui.querySelector("#jn-chat-input");if(input)input.focus();});
ui.querySelectorAll(".jn-console-chip").forEach(function(button){button.addEventListener("click",function(){const input=ui.querySelector("#jn-chat-input");if(!input)return;input.value=String(button.dataset.command||"");resizeNeuralComposer();input.focus();});});
try{S.consoleCollapsed=localStorage.getItem("jarvis.neuralCommand.collapsed")==="1";}catch(_){}
setConsoleCollapsed(S.consoleCollapsed);
window.addEventListener("keydown",function(e){if(e.code==="F13"){e.preventDefault();toggleNeuralConsole();}});
window.addEventListener("resize",function(){resize();resizeNeuralComposer();});
window.addEventListener("scroll",function(){renderNeuralConsolePlacement(true)},{passive:true});
document.addEventListener("visibilitychange",function(){const hidden=document.hidden;canvas.style.visibility=hidden?"hidden":"visible";ui.querySelector("#jn-surfaces").style.visibility=hidden?"hidden":"visible";});
function tick(){const now=performance.now();if(document.hidden){setTimeout(tick,1500);return;}syncEmbeddedVisibility();if(!S.frozen&&now-S.lastSnapshot>S.snapshotMs)pollSnapshot();if(!S.frozen&&now-S.lastEvents>S.eventsMs)pollEvents();if(!S.frozen&&now-S.lastHandPoll>S.handPollMs)pollHand();if(!S.frozen&&now-S.lastWindows>S.windowsMs)pollWindows();if(!S.frozen&&now-S.lastLayoutPoll>S.layoutPollMs)pollLayouts();if(!S.frozen&&now-S.lastAdvanced>S.advancedPollMs)pollAdvanced();if(!S.frozen&&now-S.earthLastPoll>3200)pollEarth();if(!S.frozen&&now-S.lastPoll>900)pollObservation();setTimeout(tick,220)}
pollSnapshot();pollEvents();pollWindows();pollLayouts();pollEarth();pollObservation();pollHand();pollAdvanced();resizeNeuralComposer();renderNeuralConsolePlacement(true);tick();render(performance.now());
})();
"""
}
