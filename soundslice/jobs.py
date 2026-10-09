"""One short-lived Qt thread per load, trim or export operation."""

from collections.abc import Callable
import logging

from PySide6.QtCore import QThread, Signal

from .audio import AudioError


class AudioJob(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, operation: Callable[[], object], parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.succeeded.emit(self.operation())
        except AudioError as error:
            self.failed.emit(str(error))
        except MemoryError:
            self.failed.emit("Es ist nicht genügend Arbeitsspeicher verfügbar. Bitte eine kleinere Datei öffnen.")
        except Exception:
            logging.exception("Unexpected audio operation failure")
            self.failed.emit("Die Audioverarbeitung ist fehlgeschlagen. Bitte Datei und Speicherplatz prüfen.")
