"""Protected Build #2 frontend assets for the Neural JARVIS world.

The asset is deliberately dependency-light: WebGL2, CSS, and the existing pywebview
bridge. It is rendered as an additive UI build and does not replace Jarvis core.
"""

NEURAL_MESH_BUILTIN = {
    "id": "neural-mesh",
    "name": "Neural JARVIS",
    "version": "0.3.0",
    "description": "Blue fully 3D JARVIS world with instanced liquid-cell neurons, lifecycle pulses, fluid grab/return, spatial windows, search, zoom, performance culling, and typed chat.",
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
#jn-chat{position:absolute;left:50%;bottom:22px;transform:translateX(-50%);width:min(820px,calc(100vw - 48px));display:flex;gap:9px;padding:9px;box-sizing:border-box;pointer-events:auto;border:1px solid rgba(91,190,255,.28);border-radius:16px;background:rgba(1,9,18,.76);box-shadow:0 0 36px rgba(20,128,255,.12);backdrop-filter:blur(14px)}
#jn-chat input{min-width:0;flex:1;border:0;outline:none;color:#e6f8ff;background:transparent;padding:10px 11px;font:13px/1.2 Inter,Segoe UI,sans-serif}
#jn-chat input::placeholder{color:rgba(137,190,217,.66)}
#jn-chat button{width:44px;height:40px}
#jn-help{position:absolute;left:50%;bottom:128px;transform:translateX(-50%);color:rgba(120,178,208,.56);font-size:8px;letter-spacing:.13em;pointer-events:none;white-space:nowrap}
#jn-perf{position:absolute;bottom:22px;right:24px;font-size:8px;color:#438eb9;letter-spacing:.12em;pointer-events:none}
#jn-surfaces{position:absolute;inset:0;pointer-events:none;perspective:1600px;transform-style:preserve-3d;overflow:hidden}
.jn-spatial-window{position:absolute;left:0;top:0;width:360px;height:250px;transform-style:preserve-3d;pointer-events:auto;border:1px solid rgba(92,200,255,.25);border-radius:14px;background:rgba(4,16,30,.62);box-shadow:0 18px 70px rgba(0,0,0,.42),0 0 32px rgba(31,151,238,.09),inset 0 0 24px rgba(37,155,232,.05);overflow:hidden;backdrop-filter:blur(7px)}
.jn-spatial-window.giant{width:740px;height:470px}
.jn-window-head{height:28px;display:flex;align-items:center;justify-content:space-between;padding:0 9px;border-bottom:1px solid rgba(92,200,255,.12);background:rgba(3,12,24,.57);font-size:8px;letter-spacing:.08em;color:#86c4e2;user-select:none;cursor:grab}
.jn-window-head:active{cursor:grabbing}
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
  <div id="jn-actions">
    <button class="jn-btn" id="jn-home">CORE</button>
    <button class="jn-btn" id="jn-earth">EARTH</button>
    <button class="jn-btn" id="jn-windows">WINDOWS</button>
    <button class="jn-btn" id="jn-giant">GIANT</button>
    <button class="jn-btn" id="jn-perf-btn">PERF</button>
    <button class="jn-btn" id="jn-freeze">FREEZE</button>
  </div>
  <div id="jn-inspector"><div class="jn-mini">SELECTED NEURON</div><div class="jn-name" id="jn-name"></div><div class="jn-meta" id="jn-meta"></div></div>
  <div id="jn-response"></div>
  <div id="jn-observe"></div>
  <div id="jn-help">DRAG · ORBIT · WHEEL · ZOOM · GRAB NEURON · TYPE TALK · SPATIAL WINDOWS</div>
  <div id="jn-chat"><input id="jn-chat-input" autocomplete="off" spellcheck="false" placeholder="Talk to Jarvis…" /><button class="jn-btn" id="jn-chat-send">↵</button></div>
  <div id="jn-perf">AUTO QUALITY</div>
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
  nodes:[],links:[],windows:[],selected:null,dragNode:null,orbit:false,pointerMoved:false,
  localOffsets:new Map(),births:new Map(),retirements:new Map(),particles:[],eventSequence:0,
  lastSnapshot:0,lastEvents:0,lastWindows:0,lastPoll:0,snapshotMs:2600,eventsMs:320,windowsMs:2200,
  quality:"maximum",mode:"foreground",view:"network",frozen:false,giant:false,showWindows:true,
  earthData:{locators:[]},earthLastPoll:0,observation:{enabled:false,focus:"auto"},
  yaw:.20,pitch:-.12,distance:20,target:[0,0,0],lastX:0,lastY:0,
  frameMs:16,lastFrame:performance.now(),searchTimer:0,layoutTimers:new Map(),
  surfacePositions:new Map(),surfaceScales:new Map()
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
'#version 300 es\nprecision highp float;\nlayout(location=0)in vec3 aPos;layout(location=1)in vec3 aNormal;layout(location=2)in vec3 aCenter;layout(location=3)in float aScale;layout(location=4)in float aEnergy;layout(location=5)in float aPhase;layout(location=6)in float aSelected;layout(location=7)in float aBirth;\nuniform mat4 uMvp;uniform mat4 uView;uniform float uTime;out vec3 vNormal;out vec3 vView;out vec3 vLocal;out float vEnergy;out float vPhase;out float vSelected;\nvoid main(){float life=clamp((uTime-aBirth)/760.0,0.0,1.0);float grow=life*life*(3.0-2.0*life);float wob=1.0+.028*sin(uTime*.0035+aPhase+aPos.y*4.0);vec3 local=aPos*wob;local.y+=.035*sin(uTime*.0025+aPhase*1.7);vec3 world=aCenter+local*(aScale*mix(.08,1.0,grow));world+=vec3(sin(uTime*.0002+aPhase)*.06,cos(uTime*.00017+aPhase*1.4)*.05,sin(uTime*.00018+aPhase*.8)*.06)*min(1.0,aScale);vec4 vp=uView*vec4(world,1.0);gl_Position=uMvp*vec4(world,1.0);vNormal=normalize(mat3(uView)*aNormal);vView=normalize(-vp.xyz);vLocal=local;vEnergy=aEnergy;vPhase=aPhase;vSelected=aSelected;}',
'#version 300 es\nprecision highp float;in vec3 vNormal;in vec3 vView;in vec3 vLocal;in float vEnergy;in float vPhase;in float vSelected;out vec4 outColor;\nvoid main(){vec3 n=normalize(vNormal),light=normalize(vec3(-.35,.62,.74));float diff=max(0.,dot(n,light));float fres=pow(1.-max(0.,dot(n,normalize(vView))),2.);float ring=.5+.5*sin(14.*atan(vLocal.z,vLocal.x)+vPhase+vLocal.y*5.);float e=clamp(vEnergy,0.,1.);vec3 blue=vec3(.05,.31,.73),cyan=vec3(.24,.78,1.),white=vec3(.82,.97,1.);vec3 c=mix(blue,cyan,diff*.6+fres*.4);c=mix(c,white,e*.26+ring*.08);if(vSelected>.5)c=mix(c,vec3(.70,.96,1.),.50);outColor=vec4(c,clamp(.30+.38*fres+.16*e+.07*ring,0.,.96));}'
);

const lineProg=program(
'#version 300 es\nprecision highp float;layout(location=0)in vec3 aPos;layout(location=1)in float aStrength;layout(location=2)in float aProgress;uniform mat4 uMvp;uniform float uTime;out float vStrength;out float vProgress;void main(){gl_Position=uMvp*vec4(aPos,1.);vStrength=aStrength;vProgress=aProgress;}',
'#version 300 es\nprecision highp float;in float vStrength;in float vProgress;uniform float uTime;out vec4 outColor;void main(){float pulse=.5+.5*sin(vProgress*18.-uTime*.004);outColor=vec4(.04,.46,.98,(.035+.27*vStrength)*(.72+.28*pulse));}'
);

const partProg=program(
'#version 300 es\nprecision highp float;layout(location=0)in vec3 aPos;layout(location=1)in float aLife;layout(location=2)in float aSize;uniform mat4 uMvp;out float vLife;void main(){gl_Position=uMvp*vec4(aPos,1.);gl_PointSize=max(2.,aSize*(1.-aLife));vLife=aLife;}',
'#version 300 es\nprecision highp float;in float vLife;out vec4 outColor;void main(){vec2 u=gl_PointCoord*2.-1.;if(length(u)>1.)discard;outColor=vec4(.18,.69,1.,(1.-vLife)*.48);}'
);

const meshPos=gl.createBuffer(),meshNormal=gl.createBuffer(),meshIndex=gl.createBuffer(),centerBuf=gl.createBuffer(),scaleBuf=gl.createBuffer(),energyBuf=gl.createBuffer(),phaseBuf=gl.createBuffer(),selectedBuf=gl.createBuffer(),birthBuf=gl.createBuffer(),lineBuf=gl.createBuffer(),lineStrengthBuf=gl.createBuffer(),lineProgressBuf=gl.createBuffer(),particleBuf=gl.createBuffer(),particleLifeBuf=gl.createBuffer(),particleSizeBuf=gl.createBuffer();

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

function nodePosition(n){const o=S.localOffsets.get(n.id);return o?[n.position[0]+o[0],n.position[1]+o[1],n.position[2]+o[2]]:n.position;}
function activeNodes(){
  const max=S.mode==="background"?320:S.quality==="performance"?720:1500;
  const c=camera();
  return S.nodes.slice().sort(function(a,b){
    if(a.kind==="core")return-1;if(b.kind==="core")return 1;
    const da=Math.hypot(a.position[0]-c.eye[0],a.position[1]-c.eye[1],a.position[2]-c.eye[2]);
    const db=Math.hypot(b.position[0]-c.eye[0],b.position[1]-c.eye[1],b.position[2]-c.eye[2]);
    return(b.energy||0)-(a.energy||0)+(da-db)*.0005;
  }).slice(0,max);
}
function resize(){
  const dpr=Math.min(window.devicePixelRatio||1,S.quality==="maximum"?1.5:1.0),w=Math.max(1,Math.floor(canvas.clientWidth*dpr)),h=Math.max(1,Math.floor(canvas.clientHeight*dpr));
  if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
}
function render(now){
  requestAnimationFrame(render);
  if(document.hidden)return;
  const dt=now-S.lastFrame;S.lastFrame=now;S.frameMs=S.frameMs*.92+dt*.08;
  if(S.mode==="foreground"&&S.frameMs>28)S.quality="performance";
  if(S.mode==="foreground"&&S.frameMs<18&&S.nodes.length<800)S.quality="maximum";
  resize();
  const c=camera(),aspect=canvas.width/Math.max(1,canvas.height),proj=new Float32Array(16),view=new Float32Array(16),mvp=new Float32Array(16);
  perspective(proj,Math.PI/3,aspect,.05,2000);lookAt(view,c.eye,S.target);multiply(mvp,proj,view);
  gl.clearColor(0,.004,.012,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);gl.depthMask(false);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
  const nodes=activeNodes(),nowMs=performance.now();
  const cp=new Float32Array(nodes.length*3),cs=new Float32Array(nodes.length),ce=new Float32Array(nodes.length),ph=new Float32Array(nodes.length),se=new Float32Array(nodes.length),bi=new Float32Array(nodes.length);
  nodes.forEach(function(n,i){cp.set(nodePosition(n),i*3);cs[i]=(n.scale||1)*(n.kind==="core"?1.75:n.kind==="subsystem"?1.30:.72);ce[i]=n.energy||.2;ph[i]=i*.73+(n.id.length%23);se[i]=n.id===S.selected?1:0;bi[i]=S.births.get(n.id)||nowMs-900;});
  upload(centerBuf,cp);upload(scaleBuf,cs);upload(energyBuf,ce);upload(phaseBuf,ph);upload(selectedBuf,se);upload(birthBuf,bi);
  gl.useProgram(droplet);gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uMvp"),false,mvp);gl.uniformMatrix4fv(gl.getUniformLocation(droplet,"uView"),false,view);gl.uniform1f(gl.getUniformLocation(droplet,"uTime"),nowMs);
  attr(droplet,"aPos",3,meshPos);attr(droplet,"aNormal",3,meshNormal);attr(droplet,"aCenter",3,centerBuf,1);attr(droplet,"aScale",1,scaleBuf,1);attr(droplet,"aEnergy",1,energyBuf,1);attr(droplet,"aPhase",1,phaseBuf,1);attr(droplet,"aSelected",1,selectedBuf,1);attr(droplet,"aBirth",1,birthBuf,1);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,meshIndex);gl.drawElementsInstanced(gl.TRIANGLES,meshCount,gl.UNSIGNED_SHORT,0,nodes.length);

  const map=new Map(nodes.map(function(n){return[n.id,n]})),lp=[],ls=[],lg=[];
  for(const r of S.links){if(S.dragNode&&(r.source===S.dragNode||r.target===S.dragNode))continue;const a=map.get(r.source),b=map.get(r.target);if(!a||!b)continue;const ap=nodePosition(a),bp=nodePosition(b),mid=[(ap[0]+bp[0])*.5,(ap[1]+bp[1])*.5,(ap[2]+bp[2])*.5],bend=norm(cross(norm(sub(bp,ap)),[0,1,0])),mag=.16+Math.min(1.1,Math.hypot(...sub(bp,ap))*.055),p1=add(mid,mul3(bend,mag)),p2=add(mid,mul3(bend,-mag)),pts=[ap,p1,p1,p2,p2,bp];pts.forEach(function(p,i){lp.push(...p);ls.push(r.strength||.4);lg.push((i%2)*.5);});}
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
function rootStatus(text){ui.querySelector("#jn-perf").textContent=text}
function worldToScreen(p){
  const c=camera(),rel=sub(p,c.eye),depth=rel[0]*c.forward[0]+rel[1]*c.forward[1]+rel[2]*c.forward[2];if(depth<=.1)return null;
  const focal=canvas.clientHeight/(2*Math.tan(Math.PI/6));
  return[canvas.clientWidth/2+(rel[0]*c.right[0]+rel[1]*c.right[1]+rel[2]*c.right[2])*focal/depth,canvas.clientHeight/2-(rel[0]*c.up[0]+rel[1]*c.up[1]+rel[2]*c.up[2])*focal/depth,depth];
}
function screenDelta(dx,dy,depth){const c=camera(),f=canvas.clientHeight/(2*Math.tan(Math.PI/6));return add(mul3(c.right,dx*depth/f),mul3(c.up,-dy*depth/f))}
function pick(x,y){
  let best=null,bestD=Infinity;
  for(const n of activeNodes()){const p=worldToScreen(nodePosition(n));if(!p)continue;const d=Math.hypot(p[0]-x,p[1]-y);if(d<bestD){bestD=d;best=n;}}
  return bestD<75?best:null;
}
function focus(n){
  S.selected=n.id;S.target=[...nodePosition(n)];S.distance=Math.max(5,Math.min(90,11/Math.max(.5,n.scale||1)));
  ui.querySelector("#jn-name").textContent=n.label;ui.querySelector("#jn-meta").textContent=n.kind+" · "+n.status+" · "+n.source+" · "+n.lifecycle;
  ui.querySelector("#jn-inspector").classList.add("visible");ui.querySelector("#jn-focus").textContent="FOCUS · "+n.label;
}
function spawn(pos,count){
  if(S.quality==="minimal")return;
  for(let i=0;i<Math.min(5,count||2);i++)S.particles.push({pos:[...pos],vel:[(Math.random()-.5)*1.1,(Math.random()-.5)*1.1,(Math.random()-.5)*1.1],life:0,size:5+Math.random()*8});
  if(S.particles.length>180)S.particles.splice(0,S.particles.length-180);
}
function api(){return window.pywebview&&window.pywebview.api}
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
async function pollWindows(){
  if(!S.showWindows)return;
  const a=api();if(!a||!a.spatial_windows_catalog)return;
  try{const list=await a.spatial_windows_catalog();S.windows=Array.isArray(list)?list:[];S.lastWindows=performance.now();renderSpatialWindows();}catch(_){}
}
function makeSurface(info){
  const el=document.createElement("div");el.className="jn-spatial-window";el.dataset.handle=String(info.handle);
  el.innerHTML='<div class="jn-window-head"><span class="jn-window-title"></span><span class="jn-window-status"></span></div><div class="jn-window-empty">LIVE APPLICATION SURFACE</div>';
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
    clearTimeout(S.layoutTimers.get(key));S.layoutTimers.set(key,setTimeout(async function(){const a=api();if(a&&a.neural_window_set_state){try{await a.neural_window_set_state(key,{position:[x/70,-y/70,3.5],scale:S.giant?1.28:1});}catch(_){}}},160));
  };
  head.addEventListener("pointerup",finish);head.addEventListener("pointercancel",finish);
  el.addEventListener("dblclick",async function(e){e.stopPropagation();const a=api();if(a&&a.spatial_window_focus)try{await a.spatial_window_focus(Number(info.handle));}catch(_){}});
  return el;
}
async function preview(info,el,index){
  if(index>2||S.quality==="minimal")return;
  const a=api();if(!a||!a.spatial_window_capture)return;
  try{const cap=await a.spatial_window_capture(Number(info.handle),S.giant?1000:720);if(!cap||!cap.png_base64)return;const img=document.createElement("img");img.className="jn-window-preview";img.alt="";img.src="data:image/png;base64,"+cap.png_base64;const old=el.querySelector(".jn-window-empty,.jn-window-preview");if(old)old.replaceWith(img);}catch(_){}
}
function applySurfaceTransform(el){
  const x=Number(el.dataset.x)||0,y=Number(el.dataset.y)||0,scale=Number(el.dataset.scale)||1,z=Number(el.dataset.z)||0;
  el.style.transform="translate3d("+x+"px,"+y+"px,"+z+"px) scale("+scale+")";
}
function renderSpatialWindows(){
  const layer=ui.querySelector("#jn-surfaces");if(!S.showWindows){layer.replaceChildren();return;}
  const current=new Map(Array.from(layer.children).map(function(e){return[e.dataset.handle,e]})),keep=new Set();
  S.windows.slice().sort(function(a,b){return(Number(Boolean(a.minimized))-Number(Boolean(b.minimized)))}).forEach(function(info,index){
    const key=String(info.handle);keep.add(key);let el=current.get(key);if(!el)el=makeSurface(info);
    el.classList.toggle("giant",S.giant);
    if(!Number.isFinite(Number(el.dataset.x)))el.dataset.x=String(110+(index%4)*390);
    if(!Number.isFinite(Number(el.dataset.y)))el.dataset.y=String(120+Math.floor(index/4)*280);
    if(!Number.isFinite(Number(el.dataset.z)))el.dataset.z=String(-index*25);
    el.dataset.scale=String(S.giant?1.28:1);applySurfaceTransform(el);
    if(!el.parentNode)layer.appendChild(el);
    preview(info,el,index);
  });
  for(const[key,el]of current)if(!keep.has(key))el.remove();
}
async function search(value){
  const a=api();if(!value.trim()||!a||!a.neural_search)return;
  try{const r=await a.neural_search(value.trim(),null,null,null,12);if(r.length){focus(r[0]);const box=ui.querySelector("#jn-response");box.textContent="Located "+r[0].label;box.classList.add("visible");}}catch(_){}
}
async function chat(){
  const input=ui.querySelector("#jn-chat-input"),value=input.value.trim(),a=api();if(!value||!a||!a.submit_text)return;
  input.disabled=true;ui.querySelector("#jn-status").textContent="JARVIS · PROCESSING";
  try{let result=await a.submit_text(value,false);if(result&&result.needs_confirmation){const accepted=window.confirm(result.text||"Jarvis requires confirmation.");if(accepted)result=await a.submit_text(value,true);}
    const box=ui.querySelector("#jn-response");box.textContent=(result&&(result.text||result.error))||"Done.";box.classList.add("visible");input.value="";await pollSnapshot();
  }catch(e){const box=ui.querySelector("#jn-response");box.textContent="Request failed: "+String(e);box.classList.add("visible");}
  finally{input.disabled=false;input.focus();}
}
canvas.addEventListener("pointerdown",function(e){
  const n=pick(e.clientX,e.clientY);S.lastX=e.clientX;S.lastY=e.clientY;S.pointerMoved=false;
  if(n){S.dragNode=n.id;S.selected=n.id;canvas.setPointerCapture(e.pointerId);return;}
  S.orbit=true;canvas.classList.add("dragging");canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener("pointermove",function(e){
  const dx=e.clientX-S.lastX,dy=e.clientY-S.lastY;
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
canvas.addEventListener("pointerup",function(){release()});
canvas.addEventListener("pointercancel",function(){release()});
canvas.addEventListener("wheel",function(e){e.preventDefault();S.distance=Math.max(3.5,Math.min(180,S.distance*Math.exp(e.deltaY*.001)));},{passive:false});
canvas.addEventListener("dblclick",function(e){const n=pick(e.clientX,e.clientY);if(n)focus(n)});
ui.querySelector("#jn-search").addEventListener("input",function(e){clearTimeout(S.searchTimer);S.searchTimer=setTimeout(function(){search(e.target.value)},260)});
ui.querySelector("#jn-home").addEventListener("click",function(){S.target=[0,0,0];S.distance=20;S.yaw=.2;S.pitch=-.12});
ui.querySelector("#jn-windows").addEventListener("click",function(){S.showWindows=!S.showWindows;ui.querySelector("#jn-windows").textContent=S.showWindows?"WINDOWS":"WINDOWS OFF";renderSpatialWindows()});
ui.querySelector("#jn-giant").addEventListener("click",function(){S.giant=!S.giant;ui.querySelector("#jn-giant").textContent=S.giant?"NORMAL":"GIANT";renderSpatialWindows()});
ui.querySelector("#jn-perf-btn").addEventListener("click",async function(){const a=api(),next=S.mode==="foreground"?"background":"foreground";if(a&&a.neural_set_performance_mode)try{const r=await a.neural_set_performance_mode(next);S.mode=r.mode||next;S.quality=r.quality||S.quality;}catch(_){}});
ui.querySelector("#jn-freeze").addEventListener("click",function(){S.frozen=!S.frozen;ui.querySelector("#jn-freeze").textContent=S.frozen?"UNFREEZE":"FREEZE"});
ui.querySelector("#jn-chat-send").addEventListener("click",chat);
ui.querySelector("#jn-chat-input").addEventListener("keydown",function(e){if(e.key==="Enter"){e.preventDefault();chat()}});
window.addEventListener("resize",resize);
document.addEventListener("visibilitychange",function(){const hidden=document.hidden;canvas.style.visibility=hidden?"hidden":"visible";ui.querySelector("#jn-surfaces").style.visibility=hidden?"hidden":"visible";});
function tick(){const now=performance.now();if(!S.frozen&&now-S.lastSnapshot>S.snapshotMs)pollSnapshot();if(!S.frozen&&now-S.lastEvents>S.eventsMs)pollEvents();if(!S.frozen&&now-S.lastWindows>S.windowsMs)pollWindows();setTimeout(tick,220)}
pollSnapshot();pollEvents();pollWindows();tick();render(performance.now());
})();
"""
}
