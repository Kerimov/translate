import argparse
import sys
import threading

from src.audio import AudioCapture, list_audio_devices
from src.config import Settings
from src.overlay import SubtitleOverlay
from src.platform_util import is_macos, is_windows
from src.stt import SpeechToText
from src.translate import Translator
from src.tts import TextToSpeech


class App:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.overlay = SubtitleOverlay(
            show_original=settings.show_original,
            enable_outgoing=settings.enable_outgoing,
        )
        self.stt_in = SpeechToText(settings.whisper_model_in, label="stt-in")
        self.stt_out = SpeechToText(settings.whisper_model_out, label="stt-out")
        self.translator = Translator(settings.deepseek_api_key)
        self.tts = TextToSpeech(settings.tts_voice, settings.virtual_mic_device)

        self._incoming_lock = threading.Lock()
        self._outgoing_lock = threading.Lock()

        self.team_capture = AudioCapture(
            self._on_team_segment,
            device=settings.team_audio_device,
            label="team",
            loopback=settings.team_loopback,
        )
        self.mic_capture = AudioCapture(
            self._on_mic_segment,
            device=settings.mic_input_device,
            label="mic",
        )

    def _on_team_segment(self, audio) -> None:
        if not self._incoming_lock.acquire(blocking=False):
            return

        def work() -> None:
            try:
                text = self.stt_in.transcribe(audio, language="en")
                if not text:
                    return
                print(f"[team en] {text}")
                translated = self.translator.translate(text, direction="en_to_ru")
                print(f"[team ru] {translated}")
                self.overlay.show_incoming(text, translated)
            except Exception as exc:
                print(f"[error/in] {exc}")
                self.overlay.show_error(str(exc))
            finally:
                self._incoming_lock.release()

        threading.Thread(target=work, daemon=True).start()

    def _on_mic_segment(self, audio) -> None:
        if not self.settings.enable_outgoing:
            return
        if not self._outgoing_lock.acquire(blocking=False):
            return

        def work() -> None:
            try:
                text = self.stt_out.transcribe(audio, language="ru")
                if not text:
                    return
                print(f"[you ru] {text}")
                translated = self.translator.translate(text, direction="ru_to_en")
                print(f"[you en] {translated}")
                self.overlay.show_outgoing(text, translated)
                self.tts.speak(translated)
            except Exception as exc:
                print(f"[error/out] {exc}")
                self.overlay.show_error(str(exc))
            finally:
                self._outgoing_lock.release()

        threading.Thread(target=work, daemon=True).start()

    def run(self) -> None:
        print("[app] Starting. Press Escape on overlay to quit.")
        if self.settings.team_loopback:
            if is_windows():
                print("[app] Team audio: WASAPI loopback (game/system sound)")
            else:
                print("[error] TEAM_LOOPBACK=true works only on Windows.")
                print("        On macOS set TEAM_LOOPBACK=false and use BlackHole (see README).")
                sys.exit(1)
        if self.settings.enable_outgoing and self.settings.virtual_mic_device is None:
            print("[warn] VIRTUAL_MIC_DEVICE not set — TTS will use default output.")
            if is_windows():
                print("       Set it to CABLE Input (VB-Audio) so Steam can use CABLE Output as mic.")
            elif is_macos():
                print("       Set it to BlackHole output so Steam can use it as mic.")
        self.team_capture.start()
        if self.settings.enable_outgoing:
            self.mic_capture.start()
        try:
            self.overlay.run()
        finally:
            self.team_capture.stop()
            if self.settings.enable_outgoing:
                self.mic_capture.stop()
            self.translator.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CS2 live voice translator (EN↔RU, subtitles + virtual mic)"
    )
    parser.add_argument("--list-devices", action="store_true", help="List audio devices")
    args = parser.parse_args()

    if args.list_devices:
        list_audio_devices()
        return

    settings = Settings.load()
    if not settings.deepseek_api_key:
        print("Error: set DEEPSEEK_API_KEY in .env (copy from .env.example)")
        sys.exit(1)

    App(settings).run()


if __name__ == "__main__":
    main()
