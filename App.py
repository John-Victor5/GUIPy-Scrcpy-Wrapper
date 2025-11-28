import eel
import logging
import json
import os
import time
import multiprocessing
import queue
import threading
from scrcpy_wrapper3v import ScrcpyClient

# =========================================================
# CONFIGURATION
# =========================================================
SETTINGS_FILE = 'settings.json'
eel.init('GUI')

# =========================================================
# WORKER PROCESS (Runs on a separate CPU Core)
# =========================================================
def scrcpy_worker_process(command_queue, log_queue):
    """
    This function runs in a completely separate process.
    It handles starting/stopping scrcpy and capturing logs.
    """
    client = None
    
    # Configure logging for this process to send to the Queue
    logger = logging.getLogger("Worker")
    logger.setLevel(logging.INFO)
    
    while True:
        try:
            # 1. Check for new commands from GUI (Non-blocking)
            try:
                msg = command_queue.get(timeout=0.1) # Check every 100ms
                
                if msg['action'] == 'START':
                    settings = msg['data']
                    
                    # Initialize Client in this process
                    env_path = settings.get('env_path', '')
                    env_path = env_path if env_path.strip() != "" else None
                    
                    try:
                        client = ScrcpyClient(ENV=env_path, debug=True)
                        log_queue.put(f"Worker: Scrcpy Client Initialized")

                        # --- APPLY SETTINGS ---
                        # 1. Connection
                        tcp_ip = settings.get('tcp_ip', None)
                        serial = settings.get('serial', None)
                        if tcp_ip and tcp_ip.strip():
                            client.set_connection(tcpip=tcp_ip)
                        elif serial and serial.strip() and serial != "No devices found":
                            client.set_connection(serial=serial)
                        else:
                            client.set_connection(usb=True)

                        # 2. Video
                        client.set_video(
                            max_size=int(settings.get('max_size', 0)),
                            fps=int(settings.get('fps', 0)),
                            bitrate=settings.get('bitrate', None),
                            codec=settings.get('video_codec', 'h265'),
                            buffer=int(settings.get('video_buffer', 0)),
                            codec_options=settings.get('codec_options', None),
                            no_video=settings.get('no_video', False)
                        )

                        # 3. Audio (Fixed Logic)
                        audio_src = settings.get('audio_source', 'playback')
                        use_audio_dup = settings.get('audio_dup', False)
                        if audio_src == 'mic': use_audio_dup = False 

                        client.set_audio(
                            source=audio_src,
                            codec=settings.get('audio_codec', 'aac'),
                            bitrate=settings.get('audio_bitrate', None),
                            audio_dup=use_audio_dup,
                            no_audio=settings.get('no_audio', False)
                        )

                        # 4. App Window
                        wx = int(settings['window_x']) if settings.get('window_x') else None
                        wy = int(settings['window_y']) if settings.get('window_y') else None
                        ww = int(settings['window_width']) if settings.get('window_width') else None
                        wh = int(settings['window_height']) if settings.get('window_height') else None

                        client.set_application(
                            title=settings.get('window_title', "GUIPy Scrcpy"),
                            fullscreen=settings.get('fullscreen', False),
                            always_top=settings.get('always_top', False),
                            borderless=settings.get('borderless', False),
                            window_x=wx, window_y=wy, width=ww, height=wh
                        )

                        # 5. Control
                        client.set_control(
                            no_control=settings.get('no_control', False),
                            stay_awake=settings.get('stay_awake', False),
                            turn_screen_off=settings.get('turn_screen_off', False),
                            power_off_on_close=settings.get('power_off_on_close', False)
                        )

                        # 6. Controller
                        client.set_controller(
                            keyboard=settings.get('keyboard_mode', 'sdk'),
                            mouse=settings.get('mouse_mode', 'sdk'),
                            gamepad=settings.get('gamepad_mode', 'disabled')
                        )

                        # 7. Camera
                        if settings.get('use_camera', False):
                            cid = int(settings['camera_id']) if settings.get('camera_id') else None
                            client.set_camera(
                                video_source="camera",
                                camera_facing=settings.get('camera_facing', None),
                                camera_size=settings.get('camera_size', None),
                                camera_id=cid
                            )

                        # 8. Advanced
                        client.set_advanced(
                            crop=settings.get('crop', None),
                            record_file=settings.get('record_filename', None),
                            record_format=settings.get('record_format', 'mp4'),
                            disable_screensaver=True
                        )

                        # START
                        proc = client.start()
                        log_queue.put("Worker: Scrcpy Process Started Successfully")

                    except Exception as e:
                        log_queue.put(f"Worker Error: {str(e)}")
                        client = None

                elif msg['action'] == 'STOP':
                    if client:
                        log_queue.put("Worker: Stopping Scrcpy...")
                        client.stop()
                        client = None
                        log_queue.put("Worker: Scrcpy Stopped")
                    else:
                        log_queue.put("Worker: Nothing to stop")
                
                elif msg['action'] == 'KILL':
                    break

            except queue.Empty:
                pass
            
            # 2. Check if process died unexpectedly
            if client and client.process:
                if client.process.poll() is not None:
                    log_queue.put("Worker Alert: Scrcpy process exited automatically.")
                    client = None

        except Exception as e:
            log_queue.put(f"Critical Worker Error: {e}")

# =========================================================
# MAIN GUI PROCESS
# =========================================================

# Queues for Inter-Process Communication (IPC)
cmd_queue = multiprocessing.Queue()
log_queue = multiprocessing.Queue()
worker = None

def start_background_log_reader():
    """Reads logs from the worker process and sends to GUI"""
    def runner():
        while True:
            try:
                msg = log_queue.get()
                eel.update_log(msg)
            except:
                break
    t = threading.Thread(target=runner, daemon=True)
    t.start()

# --- EEL EXPOSED FUNCTIONS ---

@eel.expose
def load_settings_py():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f: return json.load(f)
        except: pass
    return {}

@eel.expose
def get_devices_py(scrcpy_path):
    # This runs on Main Thread because it's fast and we need return value immediately
    try:
        env_path = scrcpy_path if scrcpy_path and scrcpy_path.strip() != "" else None
        client = ScrcpyClient(ENV=env_path, debug=False)
        return {'success': True, 'devices': client.list_devices()}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@eel.expose
def start_scrcpy_py(settings):
    # Save settings
    try:
        with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=4)
    except: pass

    # Send command to Worker Process
    cmd_queue.put({'action': 'START', 'data': settings})
    return {'success': True, 'message': "Start command sent to engine..."}

@eel.expose
def stop_scrcpy_py():
    cmd_queue.put({'action': 'STOP'})
    return {'success': True}

# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == '__main__':
    # Windows requires this protection for multiprocessing
    multiprocessing.freeze_support()

    # Start the Scrcpy Worker Process
    worker = multiprocessing.Process(target=scrcpy_worker_process, args=(cmd_queue, log_queue))
    worker.daemon = True # Ensures it dies if main app closes
    worker.start()

    # Start Log Reader Thread
    start_background_log_reader()

    print("GUI Started. Worker Process ID:", worker.pid)

    # Start App
    try:
        eel.start('index.html', size=(1100, 850))
    except (SystemExit, KeyboardInterrupt):
        pass
    finally:
        # Cleanup
        cmd_queue.put({'action': 'KILL'})
        worker.terminate()