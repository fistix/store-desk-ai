"""
Speech-to-Text: Google Web Speech (preferred) with Vosk offline fallback,
plus light domain-term corrections for StoreDesk vocabulary.
"""

import io
import os
import re
import wave
import json
import logging
import tempfile
import subprocess
from typing import Optional, Tuple
from fastapi import HTTPException

logger = logging.getLogger(__name__)

try:
    import vosk
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    logger.warning("Vosk package not installed - falling back to SpeechRecognition")

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# (download_url, extracted_directory_name)
VOSK_MODELS = {
    "en": (
        "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "vosk-model-small-en-us-0.15",
    ),
    "es": (
        "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
        "vosk-model-small-es-0.42",
    ),
    "fr": (
        "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
        "vosk-model-small-fr-0.22",
    ),
    "de": (
        "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
        "vosk-model-small-de-0.15",
    ),
}


# Common Vosk small-model mishears for StoreDesk domain terms.
_DOMAIN_WORD_FIXES = (
    (r"\bspock\b", "stock"),
    (r"\bstalk\b", "stock"),
    (r"\bstuck\b", "stock"),
    (r"\bstocks\b", "stock"),
    (r"\bstocked\b", "stock"),
    (r"\bstark\b", "stock"),
    (r"\bprize\b", "price"),
    (r"\bprizes\b", "price"),
    (r"\bprise\b", "price"),
    (r"\bmonitor in\b", "monitoring"),
    (r"\bmonitor ring\b", "monitoring"),
    (r"\bmonitorings\b", "monitoring"),
)


class VoskSTT:
    def __init__(self, model_path: Optional[str] = None, lang: str = "en"):
        self.model_path = model_path
        self.lang = lang
        self.model = None
        self.recognizer = None
        self.sample_rate = 16000
        self._initialize_models()

    def _initialize_models(self) -> None:
        if VOSK_AVAILABLE:
            try:
                logger.info("Loading Vosk model for language=%s", self.lang)
                if self.model_path is None:
                    self.model_path = self._ensure_model()
                self.model = vosk.Model(self.model_path)
                logger.info("Vosk model loaded from %s", self.model_path)
            except Exception as exc:
                logger.warning("Failed to load Vosk (%s); falling back to SpeechRecognition", exc)
                self.model = None

        # Keep SpeechRecognition ready as a network fallback when Vosk returns empty.
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            if self.model is None:
                logger.info("Using SpeechRecognition as primary STT")
            else:
                logger.info("SpeechRecognition available as empty-result fallback")
        elif self.model is None:
            logger.error("No speech recognition backend available")

    def _ensure_model(self) -> str:
        url, folder_name = VOSK_MODELS.get(self.lang, VOSK_MODELS["en"])
        cache_root = os.environ.get("VOSK_MODEL_DIR", "/tmp/vosk-models")
        model_dir = os.path.join(cache_root, folder_name)

        if os.path.isdir(model_dir) and os.listdir(model_dir):
            logger.info("Using cached Vosk model at %s", model_dir)
            return model_dir

        os.makedirs(cache_root, exist_ok=True)
        zip_path = os.path.join(cache_root, f"{folder_name}.zip")

        logger.info("Downloading Vosk model from %s", url)
        import urllib.request
        import zipfile

        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(cache_root)
        os.remove(zip_path)

        if not os.path.isdir(model_dir):
            raise FileNotFoundError(f"Expected Vosk model directory missing after extract: {model_dir}")

        logger.info("Vosk model ready at %s", model_dir)
        return model_dir

    def transcribe_audio(self, audio_data: bytes, format: str = "webm") -> str:
        if not audio_data:
            raise HTTPException(status_code=400, detail="Empty audio payload")

        try:
            logger.info("STT input bytes=%s format=%s", len(audio_data), format)
            wav_data = self._convert_to_wav(audio_data, format)
            duration_s = self._wav_duration_seconds(wav_data)
            logger.info("Converted WAV bytes=%s duration=%.2fs", len(wav_data), duration_s)

            if duration_s < 0.4:
                raise HTTPException(
                    status_code=422,
                    detail="Recording too short. Please speak for at least 2–3 seconds.",
                )

            # Prefer Google Web Speech when available — small Vosk models often
            # mishear domain words ("stock" → "spock"). Vosk remains offline fallback.
            text = ""
            prefer_google = os.environ.get("STT_PREFER_GOOGLE", "true").lower() in (
                "1",
                "true",
                "yes",
            )

            if prefer_google and self.recognizer is not None:
                try:
                    text = self._transcribe_with_speech_recognition(wav_data)
                except Exception as google_exc:
                    logger.warning("Google STT failed (%s); trying Vosk", google_exc)
                    if self.model is not None:
                        text = self._transcribe_with_vosk(wav_data)
            elif self.model is not None:
                text = self._transcribe_with_vosk(wav_data)
                if not text.strip() and self.recognizer is not None:
                    logger.info("Vosk returned empty text; trying SpeechRecognition fallback")
                    try:
                        text = self._transcribe_with_speech_recognition(wav_data)
                    except Exception as fallback_exc:
                        logger.warning("SpeechRecognition fallback failed: %s", fallback_exc)
            elif self.recognizer is not None:
                text = self._transcribe_with_speech_recognition(wav_data)
            else:
                raise HTTPException(status_code=503, detail="No transcription service available")

            text = self._apply_domain_corrections(text)

            if not text.strip():
                raise HTTPException(
                    status_code=422,
                    detail="Could not understand audio. Please speak clearly for 2–3 seconds and try again.",
                )
            return text
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Transcription failed")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc

    def _apply_domain_corrections(self, text: str) -> str:
        if not text:
            return text
        corrected = text.lower().strip()
        for pattern, replacement in _DOMAIN_WORD_FIXES:
            corrected = re.sub(pattern, replacement, corrected)
        if corrected != text.lower().strip():
            logger.info("STT domain correction: %r → %r", text, corrected)
        return corrected

    def _wav_duration_seconds(self, wav_data: bytes) -> float:
        try:
            with wave.open(io.BytesIO(wav_data), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate() or self.sample_rate
                width = wf.getsampwidth() or 2
                channels = wf.getnchannels() or 1
                # ffmpeg WAV-to-pipe often writes 0xFFFFFFFF size fields; fall back to byte length.
                if frames <= 0 or frames > 10_000_000:
                    pcm_bytes = max(len(wav_data) - 44, 0)
                    frames = pcm_bytes // max(width * channels, 1)
                return frames / float(rate)
        except Exception:
            return 0.0

    def _convert_to_wav(self, audio_data: bytes, input_format: str) -> bytes:
        """Convert browser audio to a real on-disk WAV (correct headers).

        ffmpeg cannot write a valid WAV size header to a pipe, so piping
        produces frames=0x7FFFFFFF and breaks duration / STT quality.
        """
        in_path = out_path = None
        try:
            suffix = f".{input_format}" if input_format else ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as in_f:
                in_f.write(audio_data)
                in_path = in_f.name
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
                out_path = out_f.name

            # Mild gain only — heavy dynaudnorm was warping speech for Vosk.
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-i",
                    in_path,
                    "-ac",
                    "1",
                    "-ar",
                    str(self.sample_rate),
                    "-af",
                    "highpass=f=80,volume=2.0",
                    "-acodec",
                    "pcm_s16le",
                    out_path,
                ],
                capture_output=True,
                check=True,
            )
            with open(out_path, "rb") as out_f:
                wav_data = out_f.read()
            if not wav_data:
                raise RuntimeError("ffmpeg produced empty WAV output")
            return wav_data
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=500,
                detail="ffmpeg is required to convert browser audio (webm) to WAV",
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or b"").decode(errors="replace")
            logger.error("ffmpeg conversion failed: %s", stderr)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported or corrupt audio payload: {stderr[:200]}",
            ) from exc
        finally:
            for path in (in_path, out_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _transcribe_with_vosk(self, wav_data: bytes) -> str:
        with io.BytesIO(wav_data) as bio:
            with wave.open(bio, "rb") as wf:
                sample_rate = wf.getframerate()
                sample_width = wf.getsampwidth()
                channels = wf.getnchannels()
                frames = wf.getnframes()
                if frames <= 0 or frames > 10_000_000:
                    pcm_bytes = max(len(wav_data) - 44, 0)
                    frames = pcm_bytes // max(sample_width * channels, 1)
                logger.info(
                    "Vosk WAV rate=%s width=%s channels=%s frames=%s duration=%.2fs",
                    sample_rate,
                    sample_width,
                    channels,
                    frames,
                    frames / float(sample_rate or self.sample_rate),
                )
                rec = vosk.KaldiRecognizer(self.model, sample_rate)
                rec.SetWords(False)

                # Feed PCM in ~0.25s chunks (even-sized for 16-bit samples).
                chunk_frames = max(int(sample_rate / 4), 4000)
                while True:
                    data = wf.readframes(chunk_frames)
                    if not data:
                        break
                    rec.AcceptWaveform(data)
                result = json.loads(rec.FinalResult())

        transcription = (result.get("text") or "").strip()
        logger.info("Vosk transcription: %r", transcription)
        return transcription.lower()

    def _transcribe_with_speech_recognition(self, wav_data: bytes) -> str:
        audio_file = io.BytesIO(wav_data)
        with wave.open(audio_file, "rb") as wf:
            audio_data = sr.AudioData(
                wf.readframes(wf.getnframes()),
                sample_rate=wf.getframerate(),
                sample_width=wf.getsampwidth(),
            )

        errors = []
        try:
            text = self.recognizer.recognize_google(audio_data)
            logger.info("Google Web Speech transcription: %r", text)
            return text.lower()
        except sr.UnknownValueError:
            errors.append("google: could not understand audio")
        except sr.RequestError as exc:
            errors.append(f"google: request failed ({exc})")
        except Exception as exc:
            errors.append(f"google: {exc!r}")

        detail = "; ".join(errors) if errors else "no recognition engine succeeded"
        raise Exception(detail)

    def get_model_info(self) -> dict:
        return {
            "model_type": "vosk" if self.model else "speech_recognition",
            "model_path": self.model_path if self.model else None,
            "language": self.lang,
            "sample_rate": self.sample_rate,
            "vosk_available": VOSK_AVAILABLE,
            "speech_recognition_available": SPEECH_RECOGNITION_AVAILABLE,
        }


_stt_instance = None


def get_stt_instance(model_path: str = None, lang: str = "en") -> VoskSTT:
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = VoskSTT(model_path, lang)
    return _stt_instance


def transcribe_audio(audio_data: bytes, format: str = "webm") -> str:
    return get_stt_instance().transcribe_audio(audio_data, format)
