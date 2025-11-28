import subprocess
import logging
import os
import shutil
from typing import List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='| [%(asctime)s] - %(levelname)s | >> %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

__version__ = "0.1.3"

class ScrcpyClient:
    def __init__(self, ENV: Optional[str] = None, debug: bool = False):
        logger.disabled = not debug
        self.args = []
        self.process = None
        base_dir = Path(__file__).parent

        local_scrcpy = None
        local_adb = None

        if ENV:
            local_env_path = (base_dir / ENV).resolve()
            local_scrcpy = local_env_path / "scrcpy.exe"
            local_adb = local_env_path / "adb.exe"
            self.scrcpy_dir = str(local_env_path)
        
        if local_scrcpy and local_scrcpy.exists() and local_adb.exists():
            logger.info(f"Using LOCAL scrcpy: {local_scrcpy}")
            logger.info(f"Using LOCAL adb: {local_adb}")
            self.scrcpy_path = str(local_scrcpy)
            self.adb_path = str(local_adb)
            return

        logger.info("Local scrcpy not found in ENV. Trying system PATH...")

        system_scrcpy = shutil.which("scrcpy")
        system_adb = shutil.which("adb")

        if system_scrcpy and system_adb:
            logger.info(f"Using SYSTEM scrcpy: {system_scrcpy}")
            logger.info(f"Using SYSTEM adb: {system_adb}")
            self.scrcpy_path = system_scrcpy
            self.adb_path = system_adb
            self.scrcpy_dir = str(Path(system_scrcpy).parent)
            return

        missing = []
        if not (local_scrcpy and local_scrcpy.exists()) and not system_scrcpy:
            missing.append("scrcpy.exe")
        if not (local_adb and local_adb.exists()) and not system_adb:
            missing.append("adb.exe")

        raise FileNotFoundError(
            f"Missing required files: {', '.join(missing)}. "
            "Provide a valid ENV folder or install scrcpy/adb in PATH."
        )
    
    def list_devices(self) -> List[dict]:
        if not os.path.exists(self.adb_path):
            logger.error("ADB not found, cannot list devices.")
            return []

        try:
            result = subprocess.run(
                [self.adb_path, "devices"], 
                capture_output=True, text=True, cwd=self.scrcpy_dir
            )
            # Skip the first line ("List of devices attached")
            lines = result.stdout.strip().split("\n")[1:]
            devices_info = []

            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 2 and parts[1] == "device":
                    serial = parts[0]
                    brand = self._get_adb_prop(serial, "ro.product.brand")
                    model = self._get_adb_prop(serial, "ro.product.model")
                    
                    devices_info.append({
                        "serial": serial,
                        "brand": brand,
                        "model": model
                    })
            return devices_info
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
    
    def _get_adb_prop(self, serial: str, prop: str) -> str:
        try:
            res = subprocess.run(
                [self.adb_path, "-s", serial, "shell", "getprop", prop],
                capture_output=True, text=True, cwd=self.scrcpy_dir
            )
            return res.stdout.strip()
        except Exception:
            return "Unknown"

    def set_video(self, max_size: int = 0, fps: int = 0, bitrate: str = None, 
                  codec: str = "h265", buffer: int = 0, codec_options: str = None, 
                  no_video: bool = False):
        if no_video:
            self.args.append("--no-video")
            return
        if fps:
            fps = max(30, min(fps, 120))
            self.args.append(f"--max-fps={fps}")

        valid_codecs = ["h264", "h265", "av1"]
        self.args.append(f"--video-codec={codec if codec in valid_codecs else 'h265'}")

        if bitrate and len(bitrate) > 1:
            if bitrate[-1].upper() in ["K", "M"]: 
                self.args.append(f"--video-bit-rate={bitrate}")
            else: 
                self.args.append("--video-bit-rate=8M")

        if max_size: self.args.append(f"--max-size={max_size}")
        if buffer: self.args.append(f"--video-buffer={buffer}")
        if codec_options: self.args.append(f"--video-codec-options={codec_options}")

    def set_audio(self, bitrate: str = None, source: str = None, codec: str = "aac", 
                  audio_dup: bool = False, no_audio: bool = False):
        if no_audio:
            self.args.append("--no-audio")
            return
        if source: self.args.append(f"--audio-source={source}")
        
        valid_codecs = ["opus", "aac", "flac", "raw"]
        self.args.append(f"--audio-codec={codec if codec in valid_codecs else 'aac'}")

        if bitrate: self.args.append(f"--audio-bit-rate={bitrate}")
        if audio_dup: self.args.append("--audio-dup")

    def set_application(self, title: str = None, fullscreen: bool = False, 
                        always_top: bool = False, borderless: bool = False, 
                        window_x: int = None, window_y: int = None,
                        width: int = None, height: int = None):
        if title: self.args.append(f"--window-title={title}")
        if fullscreen: self.args.append("--fullscreen")
        if always_top: self.args.append("--always-on-top")
        if borderless: self.args.append("--window-borderless")
        if width: self.args.append(f"--window-width={width}")
        if height: self.args.append(f"--window-height={height}")
        if window_x is not None: self.args.append(f"--window-x={window_x}")
        if window_y is not None: self.args.append(f"--window-y={window_y}")

    def set_connection(self, usb: bool = False, tcp: bool = False, serial: str = None, tcpip: str = None):
        if usb: self.args.append("--select-usb")
        if tcp: self.args.append("--select-tcp")
        if tcpip: self.args.append(f"--tcp-ip={tcpip}")
        if serial: self.args.append(f"--serial={serial}")

    def set_control(self, no_control: bool = False, stay_awake: bool = False, 
                    turn_screen_off: bool = False, power_off_on_close: bool = False):
        if no_control: self.args.append("--no-control")
        if stay_awake: self.args.append("--stay-awake")
        if turn_screen_off: self.args.append("--turn-screen-off")
        if power_off_on_close: self.args.append("--power-off-on-close")

    def set_camera(self, video_source: str = "display", camera_id: int = None, 
                   camera_size: str = None, camera_facing: str = None):
        if video_source.lower() == "camera":
            self.args.append("--video-source=camera")
            
            for item in list(self.args): 
                if item.startswith("--turn-screen-off"):
                    logger.warning("Camera Mode: Removing --turn-screen-off (Incompatible with camera mode)")
                    self.args.remove(item)
                if item.startswith("--stay-awake"):
                    logger.warning("Camera Mode: Removing --stay-awake (Incompatible with camera mode)")
                    self.args.remove(item)

            if camera_id is not None: 
                self.args.append(f"--camera-id={camera_id}")
            elif camera_facing: 
                self.args.append(f"--camera-facing={camera_facing}")
            
            if camera_size: 
                self.args.append(f"--camera-size={camera_size}")
            
            if camera_id is not None and camera_facing is not None:
                logger.warning("Both camera-id and camera-facing provided. Scrcpy may prioritize one or fail.")

    def set_controller(self, keyboard: str = None, mouse: str = None, gamepad: str = None):
        valid = ['sdk', 'uhid', 'aoa']
        gamepad_valid = ['aoa', 'uhid', 'disabled']
        if keyboard in valid: self.args.append(f"--keyboard={keyboard}")
        if mouse in valid: self.args.append(f"--mouse={mouse}")
        if gamepad in gamepad_valid: self.args.append(f"--gamepad={gamepad}")

    def set_advanced(self, crop: str = None, record_file: str = None, 
                     record_format: str = "mp4", disable_screensaver: bool = False):
        if crop: self.args.append(f"--crop={crop}")
        if record_file:
            logger.info(f"Record file saved on scrcpy folder: {record_file}")
            self.args.append(f"--record={record_file}")
            self.args.append(f"--record-format={record_format}")
        if disable_screensaver:
            self.args.append("--disable-screensaver")

    def get_args(self): return self.args

    def start(self):
        full_command = [self.scrcpy_path] + self.args
        
        logger.info(f"Target EXE: {self.scrcpy_path}")
        logger.info(f"Working Dir: {self.scrcpy_dir}")
        logger.info(f"Command: {' '.join(full_command)}")
        devices = self.list_devices()
        if not devices: raise RuntimeError("No devices found. Please connect a device and try again.")

        try:
            self.process = subprocess.Popen(
                full_command, 
                cwd=self.scrcpy_dir,
                stdout=None,
                stderr=None, 
                text=True
            )
            return self.process
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            raise e
        
    def stop(self):
        if self.process:
            logger.info("Stopping local process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
                logger.info("Local process stopped.")
                return
            except subprocess.TimeoutExpired:
                self.process.kill()
                logger.warning("Local process force killed.")
                return

        logger.warning("Process handle not found. Force killing all scrcpy.exe instances.")
        try:
            subprocess.run(["taskkill", "/F", "/IM", "scrcpy.exe"], 
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except Exception as e:
            logger.error(f"Failed to stop process: {e}")
            raise e

if __name__ == "__main__":
    Client = ScrcpyClient(debug=True)
    
    devices = Client.list_devices()
    print(f"Devices found: {devices}")

    Client.set_video(
        fps=60,
        bitrate="18M",
        codec="h265",
    )

    proc = Client.start()
    
    try:
        print("Scrcpy running... Press Ctrl+C to stop.")
        proc.wait() 
    except KeyboardInterrupt:
        Client.stop()