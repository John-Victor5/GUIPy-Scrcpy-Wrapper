import eel
import logging
import json
import os
import multiprocessing
import queue
import threading
from scrcpy_wrapper3v import ScrcpyClient

SETTINGS_FILE = 'settings.json'
eel.init('GUI')

# =========================================================
# WORKER PROCESS (Scrcpy Engine)
# =========================================================
def scrcpy_worker_process(command_queue, log_queue):
    client = None
    logger = logging.getLogger("Worker")
    logger.setLevel(logging.INFO)
    
    while True:
        try:
            try:
                msg = command_queue.get(timeout=0.1)
                
                if msg['action'] == 'START':
                    s = msg['data']
                    env_path = s.get('env_path', '')
                    env_path = env_path if env_path.strip() != "" else None
                    
                    try:
                        client = ScrcpyClient(ENV=env_path, debug=True)
                        log_queue.put(f"Worker: Initializing Scrcpy...")

                        # 1. Connection (Fixed Logic)
                        tcp_ip = s.get('tcp_ip', None)
                        serial = s.get('serial', None)
                        
                        # Only use --tcpip if strictly needed (connecting to disconnected device)
                        # If user already connected via the "Connect" button, we treat it as a specific serial
                        if tcp_ip and tcp_ip.strip():
                             # If we are manually targeting an IP
                             client.set_connection(tcpip=tcp_ip)
                        elif serial and serial != "No devices found":
                             client.set_connection(serial=serial)
                        else:
                             client.set_connection(usb=True)

                        # 2. Video
                        client.set_video(
                            max_size=int(s.get('max_size', 0)),
                            fps=int(s.get('fps', 0)),
                            bitrate=s.get('bitrate', None),
                            codec=s.get('video_codec', 'h265'),
                            buffer=int(s.get('video_buffer', 0)),
                            codec_options=s.get('codec_options', None),
                            no_video=s.get('no_video', False)
                        )

                        # 3. Audio
                        audio_src = s.get('audio_source', 'playback')
                        dup = s.get('audio_dup', False)
                        if audio_src == 'mic': dup = False 

                        client.set_audio(
                            source=audio_src, codec=s.get('audio_codec', 'aac'),
                            bitrate=s.get('audio_bitrate', None), audio_dup=dup,
                            no_audio=s.get('no_audio', False)
                        )

                        # 4. App
                        wx = int(s['window_x']) if s.get('window_x') else None
                        wy = int(s['window_y']) if s.get('window_y') else None
                        ww = int(s['window_width']) if s.get('window_width') else None
                        wh = int(s['window_height']) if s.get('window_height') else None

                        client.set_application(
                            title=s.get('window_title', "GUIPy Scrcpy"),
                            fullscreen=s.get('fullscreen', False),
                            always_top=s.get('always_top', False),
                            borderless=s.get('borderless', False),
                            window_x=wx, window_y=wy, width=ww, height=wh
                        )

                        # 5. Control & Controller
                        client.set_control(
                            no_control=s.get('no_control', False),
                            stay_awake=s.get('stay_awake', False),
                            turn_screen_off=s.get('turn_screen_off', False),
                            power_off_on_close=s.get('power_off_on_close', False)
                        )
                        client.set_controller(
                            keyboard=s.get('keyboard_mode', 'sdk'),
                            mouse=s.get('mouse_mode', 'sdk'),
                            gamepad=s.get('gamepad_mode', 'disabled')
                        )

                        # 6. Camera & Advanced
                        if s.get('use_camera', False):
                            cid = int(s['camera_id']) if s.get('camera_id') else None
                            client.set_camera(video_source="camera", camera_facing=s.get('camera_facing', None),
                                              camera_size=s.get('camera_size', None), camera_id=cid)

                        client.set_advanced(
                            crop=s.get('crop', None),
                            record_file=s.get('record_filename', None),
                            record_format=s.get('record_format', 'mp4'),
                            disable_screensaver=True
                        )

                        client.start()
                        log_queue.put("Worker: Streaming Started!")

                    except Exception as e:
                        log_queue.put(f"Worker Error: {str(e)}")
                        client = None

                elif msg['action'] == 'STOP':
                    if client:
                        client.stop()
                        client = None
                        log_queue.put("Worker: Streaming Stopped.")
                
                elif msg['action'] == 'KILL':
                    break

            except queue.Empty: pass
            
            if client and client.process and client.process.poll() is not None:
                log_queue.put("Worker Alert: Process ended unexpectedly.")
                client = None

        except Exception as e:
            log_queue.put(f"Critical Worker Error: {e}")

# =========================================================
# MAIN GUI PROCESS
# =========================================================

cmd_queue = multiprocessing.Queue()
log_queue = multiprocessing.Queue()

def start_background_log_reader():
    def runner():
        while True:
            try:
                msg = log_queue.get()
                eel.update_log(msg)
            except: break
    t = threading.Thread(target=runner, daemon=True)
    t.start()

# --- EEL EXPOSED FUNCTIONS ---

@eel.expose
def adb_pair_py(path, ip, code):
    """Pairs device using ADB Pair (Run on thread to prevent freeze)"""
    try:
        env = path if path and path.strip() != "" else None
        client = ScrcpyClient(ENV=env)
        success = client.pair_device(ip, code)
        return {'success': success, 'message': 'Paired Successfully' if success else 'Pairing Failed (Check Log)'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@eel.expose
def adb_connect_py(path, ip):
    """Connects to device using ADB Connect"""
    try:
        env = path if path and path.strip() != "" else None
        client = ScrcpyClient(ENV=env)
        success = client.connect_device(ip)
        return {'success': success, 'message': 'Connected Successfully' if success else 'Connection Failed (Check Log)'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

@eel.expose
def load_settings_py():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f: return json.load(f)
        except: pass
    return {}

@eel.expose
def get_devices_py(scrcpy_path):
    try:
        env_path = scrcpy_path if scrcpy_path and scrcpy_path.strip() != "" else None
        client = ScrcpyClient(ENV=env_path, debug=False)
        return {'success': True, 'devices': client.list_devices()}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def start_scrcpy_py(settings):
    try:
        with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=4)
    except: pass
    cmd_queue.put({'action': 'START', 'data': settings})
    return {'success': True}

@eel.expose
def stop_scrcpy_py():
    cmd_queue.put({'action': 'STOP'})
    return {'success': True}

if __name__ == '__main__':
    multiprocessing.freeze_support()
    worker = multiprocessing.Process(target=scrcpy_worker_process, args=(cmd_queue, log_queue))
    worker.daemon = True
    worker.start()
    start_background_log_reader()
    
    try:
        eel.start('index.html', size=(1100, 900))
    except: pass
    finally:
        cmd_queue.put({'action': 'KILL'})
        worker.terminate()