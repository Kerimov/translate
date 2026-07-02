import argparse
import sys
import threading

from src.audio import AudioCapture, list_audio_devices
from src.config import Settings
from src.overlay import SubtitleOverlay
from src.platform_util import is_macos, is_windows
from src.segment_worker import SegmentQueueWorker
from src.stt import SpeechToText
from src.translate import Translator
from src.tts import TextToSpeech
from src.voice_audio import enhance_voice, is_mostly_speech


class App:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.overlay = SubtitleOverlay(
            show_original=settings.show_original,
            enable_outgoing=settings.enable_outgoing,
        )
        self.stt_in = SpeechToText(
            settings.whisper_model_in, label="stt-in", for_loopback=True
        )
        self.translator = Translator(settings.deepseek_api_key)
        self.stt_out: SpeechToText | None = None
        self.tts: TextToSpeech | None = None
        self.mic_capture: AudioCapture | None = None

        if settings.enable_outgoing:
            self.stt_out = SpeechToText(settings.whisper_model_out, label="stt-out")
            self.tts = TextToSpeech(settings.tts_voice, settings.virtual_mic_device)

        self._outgoing_lock = threading.Lock()
        self._team_worker = SegmentQueueWorker(self._stt_team_segment)

        self.team_capture = AudioCapture(
            self._team_worker.submit,
            device=settings.team_audio_device,
            label="team",
            loopback=settings.team_loopback,
            silence_frames=settings.segment_silence_frames,
            min_speech_frames=settings.segment_min_speech_frames,
            energy_threshold=0.004 if settings.team_loopback else 0.008,
        )
        if settings.enable_outgoing:
            self.mic_capture = AudioCapture(
                self._on_mic_segment,
                device=settings.mic_input_device,
                label="mic",
                silence_frames=settings.segment_silence_frames,
                min_speech_frames=settings.segment_min_speech_frames,
            )

    def _stt_team_segment(self, audio) -> None:
        try:
            if not is_mostly_speech(audio):
                return
            audio = enhance_voice(audio)
            self.overlay.show_incoming_progress("Распознаю...")
            text = self.stt_in.transcribe(audio, language="en")
            if not text:
                return
            print(f"[team en] {text}")
            self.overlay.show_incoming(text, "…")
            threading.Thread(
                target=self._translate_team,
                args=(text,),
                daemon=True,
            ).start()
        except Exception as exc:
            print(f"[error/in] {exc}")
            self.overlay.show_error(str(exc))

    def _translate_team(self, text: str) -> None:
        try:
            translated = self.translator.translate(text, direction="en_to_ru")
            print(f"[team ru] {translated}")
            self.overlay.show_incoming(text, translated)
        except Exception as exc:
            print(f"[error/translate] {exc}")

    def _on_mic_segment(self, audio) -> None:
        if not self.settings.enable_outgoing:
            return
        if not self._outgoing_lock.acquire(blocking=False):
            return

        def work() -> None:
            try:
                assert self.stt_out is not None and self.tts is not None
                text = self.stt_out.transcribe(audio, language="ru")
                if not text:
                    return
                print(f"[you ru] {text}")
                self.overlay.show_outgoing(text, "…")
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
        if self.settings.enable_outgoing:
            print("[app] Режим: субтитры команды + перевод вашего голоса")
        else:
            print("[app] Режим: только субтитры команды (ваш голос не переводится)")
        if self.settings.team_loopback:
            if is_windows():
                print("[app] Team audio: WASAPI loopback (game/system sound)")
                print("[tip] В CS2: громкость голоса команды выше, звуки игры ниже")
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
        if self.settings.enable_outgoing and self.mic_capture is not None:
            self.mic_capture.start()
        try:
            self.overlay.run()
        finally:
            self.team_capture.stop()
            if self.mic_capture is not None:
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
