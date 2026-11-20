async function api(path, body) {
 const opts=body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{};
 const r=await fetch(path,opts); const d=await r.json(); if(!r.ok) throw new Error(d.message||'Request failed'); return d;
}
function setText(id, value){const e=document.getElementById(id);if(e)e.textContent=value;}
function renderEvents(events){
 const box=document.getElementById('activityList');
 if(!events.length){box.innerHTML='<p class="muted">No operations recorded yet.</p>';return;}
 box.innerHTML=events.map(e=>`<div class="activity-row"><span class="activity-dot ${String(e.command).toLowerCase()}"></span><div><b>${e.command}</b><small>${e.timestamp.replace('T',' ')}</small></div><strong>${e.brightness}%</strong></div>`).join('');
}
async function refreshLive(){
 try{
  const d=await api('/api/live'), s=d.status, v=d.reading;
  const badge=document.getElementById('connectionBadge');
  badge.className='status-pill '+(s.connected?'active':'offline');
  badge.innerHTML='<i></i> '+(s.connected?(s.mode==='demo'?'Demo link active':'Bluetooth connected'):'Disconnected');
  setText('deviceConnection',s.connected?'Connected':'Disconnected');
  setText('deviceName',s.device||'ESP32_LED'); setText('modeTag',s.mode.toUpperCase());
  setText('lastSeen',s.last_seen?s.last_seen.slice(11,19):'—');
  setText('readingCount',d.reading_count);setText('readingCount2',d.reading_count);
  const led=document.getElementById('ledStatus'), visual=document.getElementById('ledVisual');
  led.className='status-pill '+(v.led_on?'active':'offline');led.innerHTML='<i></i> '+(v.led_on?'LED ON':'LED OFF');
  visual.classList.toggle('glowing',!!v.led_on);
  document.getElementById('brightnessValue').innerHTML=(v.brightness||0)+'<small>%</small>';
  setText('operatingTime',d.operating_seconds+'s');
  setText('voltageValue',v.voltage==null?'—':v.voltage+' V');
  setText('currentValue',v.current_ma==null?'—':v.current_ma+' mA');
  setText('powerValue',v.power_mw==null?'—':v.power_mw);
  setText('temperatureValue',v.temperature==null?'—':v.temperature+' °C');
  setText('clock',new Date(d.server_time).toLocaleString());
  renderEvents(d.events);
  document.getElementById('connectionMessage').textContent=s.connected?(s.mode==='demo'?'Demo Bluetooth link is simulated. Readings are generated every 2 seconds.':'Connected through '+s.port+'. Ensure ESP32 firmware sends STATUS responses.'):(s.last_error||'Choose Demo Bluetooth for presentation, or Real COM after pairing your ESP32 in Windows.');
 }catch(e){setText('connectionMessage',e.message);}
}
document.addEventListener('DOMContentLoaded',()=>{
 const mode=document.getElementById('connectionMode'), portWrap=document.getElementById('portWrap');
 mode.addEventListener('change',()=>portWrap.style.display=mode.value==='serial'?'block':'none');
 document.getElementById('connectBtn').addEventListener('click',async()=>{
  try{const d=await api('/api/connect',{mode:mode.value,port:document.getElementById('comPort').value,device:'ESP32_LED'});setText('connectionMessage',d.message);refreshLive();}
  catch(e){setText('connectionMessage',e.message);}
 });
 document.getElementById('disconnectBtn').addEventListener('click',async()=>{try{const d=await api('/api/disconnect',{});setText('connectionMessage',d.message);refreshLive();}catch(e){setText('connectionMessage',e.message);}});
 const slider=document.getElementById('brightness');
 slider.addEventListener('input',()=>setText('sliderValue',slider.value+'%'));
 async function command(c,b){try{const d=await api('/api/control',{command:c,brightness:b});setText('controlMessage',d.message);refreshLive();}catch(e){setText('controlMessage',e.message);}}
 document.getElementById('onBtn').addEventListener('click',()=>command('ON',Number(slider.value)));
 document.getElementById('offBtn').addEventListener('click',()=>command('OFF',0));
 document.getElementById('applyBtn').addEventListener('click',()=>command('DIM',Number(slider.value)));
 refreshLive();setInterval(refreshLive,2000);
});
