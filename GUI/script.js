let isRunning = false;
let connectionMode = 'usb';

window.onload = async function() {
    await loadSavedSettings();
    setMode('usb'); // Default
    fetchDevices();
};

window.addEventListener("resize", function() {
    window.resizeTo(900, 700);
});

async function loadSavedSettings() {
    let s = await eel.load_settings_py()();
    if (!s || Object.keys(s).length === 0) return;

    log("Restoring settings...");
    const setVal = (id, val) => { let el = document.getElementById(id); if(el && val != null) el.value = val; };
    const setCheck = (id, val) => { let el = document.getElementById(id); if(el && val != null) el.checked = val; };

    setVal('env_path', s.env_path);
    setVal('tcp_ip', s.tcp_ip); // Wi-Fi IP
    
    // Video
    setVal('max_size', s.max_size); setVal('fps', s.fps); setVal('bitrate', s.bitrate);
    setVal('video_buffer', s.video_buffer); setVal('video_codec', s.video_codec);
    setVal('codec_options', s.codec_options); setCheck('no_video', s.no_video);

    // Audio
    setVal('audio_source', s.audio_source); setVal('audio_codec', s.audio_codec);
    setVal('audio_bitrate', s.audio_bitrate); setCheck('audio_dup', s.audio_dup);
    setCheck('no_audio', s.no_audio);

    // Inputs
    setVal('keyboard_mode', s.keyboard_mode); setVal('mouse_mode', s.mouse_mode);
    setVal('gamepad_mode', s.gamepad_mode);

    // App
    setVal('window_title', s.window_title); setVal('window_x', s.window_x);
    setVal('window_y', s.window_y); setVal('window_width', s.window_width);
    setVal('window_height', s.window_height); setCheck('fullscreen', s.fullscreen);
    setCheck('always_top', s.always_top); setCheck('borderless', s.borderless);

    // Control
    setCheck('no_control', s.no_control); setCheck('stay_awake', s.stay_awake);
    setCheck('turn_screen_off', s.turn_screen_off); setCheck('power_off_on_close', s.power_off_on_close);

    // Camera
    setCheck('use_camera', s.use_camera); setVal('camera_id', s.camera_id);
    setVal('camera_facing', s.camera_facing); setVal('camera_size', s.camera_size);

    // Adv
    setVal('crop', s.crop); setVal('record_filename', s.record_filename);
    setVal('record_format', s.record_format);

    // Switch mode if IP was saved
    if(s.tcp_ip && s.tcp_ip.length > 5) setMode('tcp');
}

function setMode(mode) {
    connectionMode = mode;
    document.getElementById('tab-usb').classList.toggle('active', mode === 'usb');
    document.getElementById('tab-tcp').classList.toggle('active', mode === 'tcp');
    document.getElementById('panel-usb').style.display = (mode === 'usb') ? 'block' : 'none';
    document.getElementById('panel-tcp').style.display = (mode === 'tcp') ? 'block' : 'none';
}

function togglePairing() {
    const box = document.getElementById('pairing-box');
    const arrow = document.getElementById('pair-arrow');
    if (box.style.display === 'none') {
        box.style.display = 'block';
        arrow.innerText = '▲';
    } else {
        box.style.display = 'none';
        arrow.innerText = '▼';
    }
}

// === NEW PAIRING FUNCTIONS ===
async function adbPair() {
    const ip = document.getElementById('pair_ip').value;
    const code = document.getElementById('pair_code').value;
    const path = document.getElementById('env_path').value;
    
    if(!ip || !code) { log("Error: Enter IP:Port and Pairing Code"); return; }
    
    log(`Attempting to pair ${ip}...`);
    let res = await eel.adb_pair_py(path, ip, code)();
    log(res.message);
}

async function adbConnect() {
    const ip = document.getElementById('tcp_ip').value;
    const path = document.getElementById('env_path').value;

    if(!ip) { log("Error: Enter Device IP (e.g. 192.168.1.5:5555)"); return; }

    log(`Attempting to connect to ${ip}...`);
    let res = await eel.adb_connect_py(path, ip)();
    log(res.message);
}
// ==============================

async function fetchDevices() {
    const path = document.getElementById('env_path').value;
    log("Scanning USB devices...");
    const select = document.getElementById('device_select');
    select.innerHTML = "<option>Scanning...</option>";

    let response = await eel.get_devices_py(path)();
    select.innerHTML = "";

    if (response.success && response.devices.length > 0) {
        response.devices.forEach(dev => {
            let opt = document.createElement('option');
            opt.value = dev.serial;
            opt.text = `${dev.model} (${dev.serial})`;
            select.appendChild(opt);
        });
        log(`Found ${response.devices.length} USB devices.`);
    } else {
        let opt = document.createElement('option');
        opt.text = "No USB devices found";
        select.appendChild(opt);
        log("No USB devices found.");
    }
}

async function toggleScrcpy() {
    if (!isRunning) start();
    else stop();
}

async function start() {
    const s = {
        env_path: document.getElementById('env_path').value,
        serial: document.getElementById('device_select').value,
        tcp_ip: (connectionMode === 'tcp') ? document.getElementById('tcp_ip').value : null,

        // Video
        max_size: document.getElementById('max_size').value,
        fps: document.getElementById('fps').value,
        bitrate: document.getElementById('bitrate').value,
        video_buffer: document.getElementById('video_buffer').value,
        video_codec: document.getElementById('video_codec').value,
        codec_options: document.getElementById('codec_options').value,
        no_video: document.getElementById('no_video').checked,

        // Audio
        audio_source: document.getElementById('audio_source').value,
        audio_codec: document.getElementById('audio_codec').value,
        audio_bitrate: document.getElementById('audio_bitrate').value,
        audio_dup: document.getElementById('audio_dup').checked,
        no_audio: document.getElementById('no_audio').checked,

        // Inputs
        keyboard_mode: document.getElementById('keyboard_mode').value,
        mouse_mode: document.getElementById('mouse_mode').value,
        gamepad_mode: document.getElementById('gamepad_mode').value,

        // App
        window_title: document.getElementById('window_title').value,
        window_x: document.getElementById('window_x').value,
        window_y: document.getElementById('window_y').value,
        window_width: document.getElementById('window_width').value,
        window_height: document.getElementById('window_height').value,
        fullscreen: document.getElementById('fullscreen').checked,
        always_top: document.getElementById('always_top').checked,
        borderless: document.getElementById('borderless').checked,

        // Control
        no_control: document.getElementById('no_control').checked,
        stay_awake: document.getElementById('stay_awake').checked,
        turn_screen_off: document.getElementById('turn_screen_off').checked,
        power_off_on_close: document.getElementById('power_off_on_close').checked,

        // Camera
        use_camera: document.getElementById('use_camera').checked,
        camera_id: document.getElementById('camera_id').value,
        camera_facing: document.getElementById('camera_facing').value,
        camera_size: document.getElementById('camera_size').value,

        // Advanced
        crop: document.getElementById('crop').value,
        record_filename: document.getElementById('record_filename').value,
        record_format: document.getElementById('record_format').value,
    };

    if (connectionMode === 'usb' && (s.serial === "No USB devices found" || !s.serial)) {
        log("Error: Select a USB device."); return;
    }
    if (connectionMode === 'tcp' && !s.tcp_ip) {
        log("Error: Enter Device IP or Connect first."); return;
    }

    setUIState(true);
    let result = await eel.start_scrcpy_py(s)();
    if (!result.success) {
        log("Error starting: " + result.message);
        setUIState(false);
    }
}

async function stop() {
    log("Stopping...");
    await eel.stop_scrcpy_py()();
    setUIState(false);
    log("Stopped.");
}

function setUIState(running) {
    isRunning = running;
    const btnStart = document.getElementById('btn_start');
    const btnStop = document.getElementById('btn_stop');
    const status = document.getElementById('status_text');

    if (running) {
        btnStart.style.display = 'none';
        btnStop.style.display = 'block';
        status.innerText = "Running";
        status.style.color = "#00b894";
    } else {
        btnStart.style.display = 'block';
        btnStop.style.display = 'none';
        status.innerText = "Ready";
        status.style.color = "#a0a0a0";
    }
}

eel.expose(update_log);
function update_log(msg) {
    const container = document.getElementById('log-container');
    const div = document.createElement('div');
    div.innerText = `>> ${msg}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
function log(msg) { update_log(msg); }