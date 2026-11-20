async function sendLedCommand(command, brightness) {
  const msg = document.getElementById('controlMessage');
  try {
    const res = await fetch('/api/control', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command,brightness})});
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Command failed');
    if (msg) msg.textContent = data.message;
    updateLed(command, brightness);
  } catch(e) { if (msg) msg.textContent = e.message; }
}
function updateLed(command, brightness) {
  const status=document.getElementById('ledStatus'), visual=document.getElementById('ledVisual'), val=document.getElementById('brightnessValue');
  if (!status) return;
  const on=command!=='OFF';
  status.innerHTML='<i></i> '+(on?'LED ON':'LED OFF');
  status.className='status-pill '+(on?'active':'offline');
  visual.classList.toggle('glowing',on);
  val.innerHTML=(on?brightness:0)+'<small>%</small>';
}
document.addEventListener('DOMContentLoaded',()=>{
 const slider=document.getElementById('brightness'), sliderValue=document.getElementById('sliderValue');
 if(slider) slider.addEventListener('input',()=>sliderValue.textContent=slider.value+'%');
 const on=document.getElementById('onBtn'), off=document.getElementById('offBtn'), apply=document.getElementById('applyBtn');
 if(on) on.addEventListener('click',()=>sendLedCommand('ON',Number(slider.value)));
 if(off) off.addEventListener('click',()=>sendLedCommand('OFF',0));
 if(apply) apply.addEventListener('click',()=>sendLedCommand('DIM',Number(slider.value)));
 const connect=document.getElementById('connectBtn');
 if(connect) connect.addEventListener('click',()=>{const m=document.getElementById('controlMessage'); if(m)m.textContent='Demo mode: pair your ESP32 and configure serial_bridge.py for hardware connection.';});
});
