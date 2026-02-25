import sys
import os
import threading
import json
import time
from datetime import datetime
from pathlib import Path

try:
    import speech_recognition as sr
except ImportError:
    print("Eksik: pip install SpeechRecognition")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QTextEdit, QListWidget, QLineEdit, QLabel,
    QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QSpinBox, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

# ─────────────────────────────────────────
# Sabitler & Varsayılanlar
# ─────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "kufur_config.json"

VARSAYILAN_KUFURLER = [
    "yozgat", "aptal",
    "ahmak", "budala",
    "lan", "ulan",
    "beyinsiz", "kafasız", "manyak"
]

# Dinleme döngüsü kontrolü
_calisma_durumu = threading.Event()


# ─────────────────────────────────────────
# Yardımcı Fonksiyonlar
# ─────────────────────────────────────────

def bip_sesi(frekans: int = 1500, sure_ms: int = 700):
    """Platform bağımsız BİP sesi."""
    try:
        if sys.platform == "win32":
            import winsound
            winsound.Beep(frekans, sure_ms)
        else:
            try:
                import subprocess
                subprocess.run(["beep", f"-f{frekans}", f"-l{sure_ms}"],
                               capture_output=True, timeout=2)
            except Exception:
                sys.stdout.write("\a")
                sys.stdout.flush()
                time.sleep(sure_ms / 1000)
    except Exception:
        pass


def normalize(metin: str) -> str:
    """Türkçe karakterleri normalize eder, küçük harfe çevirir."""
    for kaynak, hedef in {"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü",
                          "Ş": "ş", "Ö": "ö", "Ç": "ç"}.items():
        metin = metin.replace(kaynak, hedef)
    return metin.lower().strip()


def kufur_tespit(metin: str, kufur_listesi: list[str]) -> list[str]:
    """Metindeki tam kelime küfürleri döndürür (yanlış alarm engellenir)."""
    kelimeler = normalize(metin).split()
    return [k for k in kufur_listesi if normalize(k) in kelimeler]


def log_yaz_dosya(mesaj: str, log_dosyasi: str):
    """Mesajı log dosyasına tarih/saatle yazar."""
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_dosyasi, "a", encoding="utf-8") as f:
            f.write(f"[{zaman}] {mesaj}\n")
    except Exception:
        pass


def konfig_yukle() -> dict:
    """config.json'ı yükler; yoksa varsayılan döndürür."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "dil": "tr-TR",
        "bip_frekans": 1500,
        "bip_sure_ms": 700,
        "log_dosyasi": "kufur_log.txt",
        "kufur_listesi": VARSAYILAN_KUFURLER[:]
    }


def konfig_kaydet(konfig: dict):
    """Yapılandırmayı diske yazar."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(konfig, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Kaydetme hatası: {e}")


def kelime_ekle(konfig: dict, kelime: str) -> bool:
    kelime = normalize(kelime)
    mevcut = [normalize(k) for k in konfig["kufur_listesi"]]
    if kelime and kelime not in mevcut:
        konfig["kufur_listesi"].append(kelime)
        konfig_kaydet(konfig)
        return True
    return False


def kelime_sil(konfig: dict, kelime: str) -> bool:
    kelime = normalize(kelime)
    onceki = len(konfig["kufur_listesi"])
    konfig["kufur_listesi"] = [k for k in konfig["kufur_listesi"] if normalize(k) != kelime]
    if len(konfig["kufur_listesi"]) < onceki:
        konfig_kaydet(konfig)
        return True
    return False


# ─────────────────────────────────────────
# Dinleme Thread'i
# ─────────────────────────────────────────

class DinlemeThread(QThread):
    log_sinyal = pyqtSignal(str)      # Normal log mesajı
    kufur_sinyal = pyqtSignal(str)    # Küfür uyarısı (kırmızı)
    durum_sinyal = pyqtSignal(bool)   # Başladı / durdu

    def __init__(self, konfig: dict):
        super().__init__()
        self.konfig = konfig

    def run(self):
        recognizer = sr.Recognizer()
        dil          = self.konfig.get("dil", "tr-TR")
        frekans      = self.konfig.get("bip_frekans", 1500)
        sure         = self.konfig.get("bip_sure_ms", 700)
        kufur_listesi = self.konfig.get("kufur_listesi", VARSAYILAN_KUFURLER)
        log_dosyasi  = self.konfig.get("log_dosyasi", "kufur_log.txt")

        try:
            with sr.Microphone() as source:
                self.log_sinyal.emit("Ortam gürültüsü ayarlanıyor...")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                self.log_sinyal.emit("Dinleme başladı — konuşabilirsin!")
                self.durum_sinyal.emit(True)

                while _calisma_durumu.is_set():
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        metin = recognizer.recognize_google(audio, language=dil).lower()

                        self.log_sinyal.emit(f"{metin}")
                        log_yaz_dosya(f"KONUŞMA: {metin}", log_dosyasi)

                        bulunanlar = kufur_tespit(metin, kufur_listesi)
                        if bulunanlar:
                            self.kufur_sinyal.emit(
                                f"KÜFÜR ALGILANDI → {', '.join(bulunanlar)}"
                            )
                            log_yaz_dosya(f"KÜFÜR: {bulunanlar} | {metin}", log_dosyasi)
                            threading.Thread(
                                target=bip_sesi,
                                args=(frekans, sure),
                                daemon=True
                            ).start()

                    except sr.WaitTimeoutError:
                        pass
                    except sr.UnknownValueError:
                        self.log_sinyal.emit("Anlaşılamadı")
                    except sr.RequestError as e:
                        self.log_sinyal.emit(f"API hatası: {e}")

        except OSError as e:
            self.log_sinyal.emit(f"Mikrofon açılamadı: {e}")
        except Exception as e:
            self.log_sinyal.emit(f"Beklenmedik hata: {e}")
        finally:
            self.durum_sinyal.emit(False)
            self.log_sinyal.emit("Dinleme durduruldu.")


# ─────────────────────────────────────────
# Ana Pencere
# ─────────────────────────────────────────

KOYU_TEMA = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #45475a;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
    font-weight: bold;
    color: #cba6f7;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
}
QTextEdit {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #cdd6f4;
    font-family: 'Consolas', monospace;
    font-size: 12px;
    padding: 4px;
}
QListWidget {
    background-color: #181825;
    border: 1px solid #45475a;
    border-radius: 6px;
    color: #cdd6f4;
}
QListWidget::item:selected {
    background-color: #cba6f7;
    color: #1e1e2e;
}
QLineEdit, QSpinBox {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    color: #cdd6f4;
    padding: 4px 8px;
}
QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #cba6f7;
}
QPushButton {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 16px;
    color: #cdd6f4;
}
QPushButton:hover {
    background-color: #45475a;
}
QPushButton#baslat_btn {
    background-color: #a6e3a1;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#baslat_btn:hover {
    background-color: #94e2d5;
}
QPushButton#durdur_btn {
    background-color: #f38ba8;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#durdur_btn:hover {
    background-color: #fab387;
}
QLabel {
    color: #a6adc8;
}
QSplitter::handle {
    background-color: #45475a;
}
"""


class KufurFiltresiGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.konfig = konfig_yukle()
        self.thread: DinlemeThread | None = None

        self.setWindowTitle("Küfür Filtresi & Canlı Sansür Sistemi")
        self.setMinimumSize(900, 620)
        self.resize(960, 660)
        self.setStyleSheet(KOYU_TEMA)

        self._arayuz_olustur()
        self.liste_yenile()

    # ── Arayüz Kurulum ─────────────────────

    def _arayuz_olustur(self):
        merkez = QWidget()
        self.setCentralWidget(merkez)
        kok = QVBoxLayout(merkez)
        kok.setSpacing(10)
        kok.setContentsMargins(12, 12, 12, 12)

        # Başlık
        baslik = QLabel("Türkçe Küfür Filtresi & Canlı Sansür Sistemi")
        baslik.setAlignment(Qt.AlignmentFlag.AlignCenter)
        baslik.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        baslik.setStyleSheet("color: #cba6f7; padding: 6px;")
        kok.addWidget(baslik)

        # Ana splitter: sol log | sağ panel
        splitter = QSplitter(Qt.Orientation.Horizontal)
        kok.addWidget(splitter, stretch=1)

        # ── SOL: Log Alanı ──
        sol = QGroupBox("Canlı Log")
        sol_layout = QVBoxLayout(sol)

        self.log_alani = QTextEdit()
        self.log_alani.setReadOnly(True)
        sol_layout.addWidget(self.log_alani)

        temizle_btn = QPushButton("Logu Temizle")
        temizle_btn.clicked.connect(self.log_alani.clear)
        sol_layout.addWidget(temizle_btn)

        splitter.addWidget(sol)

        # ── SAĞ: Kontrol Paneli ──
        sag = QWidget()
        sag_layout = QVBoxLayout(sag)
        sag_layout.setSpacing(10)

        # Başlat / Durdur
        kontrol_group = QGroupBox("Kontrol")
        kontrol_layout = QHBoxLayout(kontrol_group)

        self.baslat_btn = QPushButton("Başlat")
        self.baslat_btn.setObjectName("baslat_btn")
        self.baslat_btn.clicked.connect(self.baslat)

        self.durdur_btn = QPushButton("Durdur")
        self.durdur_btn.setObjectName("durdur_btn")
        self.durdur_btn.setEnabled(False)
        self.durdur_btn.clicked.connect(self.durdur)

        kontrol_layout.addWidget(self.baslat_btn)
        kontrol_layout.addWidget(self.durdur_btn)
        sag_layout.addWidget(kontrol_group)

        # Durum
        self.durum_label = QLabel("Bekliyor")
        self.durum_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.durum_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #a6adc8;"
        )
        sag_layout.addWidget(self.durum_label)

        # Ayarlar
        ayar_group = QGroupBox("Ayarlar")
        ayar_form = QFormLayout(ayar_group)

        self.frekans_spin = QSpinBox()
        self.frekans_spin.setRange(200, 4000)
        self.frekans_spin.setSingleStep(100)
        self.frekans_spin.setValue(self.konfig.get("bip_frekans", 1500))
        self.frekans_spin.valueChanged.connect(self._ayar_guncelle)
        ayar_form.addRow("BİP Frekansı (Hz):", self.frekans_spin)

        self.sure_spin = QSpinBox()
        self.sure_spin.setRange(100, 3000)
        self.sure_spin.setSingleStep(100)
        self.sure_spin.setValue(self.konfig.get("bip_sure_ms", 700))
        self.sure_spin.valueChanged.connect(self._ayar_guncelle)
        ayar_form.addRow("BİP Süresi (ms):", self.sure_spin)

        test_btn = QPushButton("BİP Testi")
        test_btn.clicked.connect(lambda: threading.Thread(
            target=bip_sesi,
            args=(self.frekans_spin.value(), self.sure_spin.value()),
            daemon=True
        ).start())
        ayar_form.addRow("", test_btn)

        sag_layout.addWidget(ayar_group)

        # Küfür Listesi
        liste_group = QGroupBox("Küfür Listesi")
        liste_layout = QVBoxLayout(liste_group)

        self.liste_widget = QListWidget()
        liste_layout.addWidget(self.liste_widget)

        self.kelime_input = QLineEdit()
        self.kelime_input.setPlaceholderText("Yeni kelime gir...")
        self.kelime_input.returnPressed.connect(self.ekle)
        liste_layout.addWidget(self.kelime_input)

        kelime_btn_layout = QHBoxLayout()
        ekle_btn = QPushButton("Ekle")
        ekle_btn.clicked.connect(self.ekle)
        sil_btn = QPushButton("Seçileni Sil")
        sil_btn.clicked.connect(self.sil)
        kelime_btn_layout.addWidget(ekle_btn)
        kelime_btn_layout.addWidget(sil_btn)
        liste_layout.addLayout(kelime_btn_layout)

        self.kelime_sayisi_label = QLabel()
        self.kelime_sayisi_label.setStyleSheet("color: #6c7086; font-size: 11px;")
        liste_layout.addWidget(self.kelime_sayisi_label)

        sag_layout.addWidget(liste_group, stretch=1)
        splitter.addWidget(sag)
        splitter.setSizes([560, 380])

    # ── Slot'lar ───────────────────────────

    def _log(self, metin: str):
        self.log_alani.append(metin)

    def _kufur_log(self, metin: str):
        self.log_alani.append(
            f'<span style="color:#f38ba8; font-weight:bold;">{metin}</span>'
        )

    def _durum_guncelle(self, aktif: bool):
        if aktif:
            self.durum_label.setText("Aktif — Dinleniyor")
            self.durum_label.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #a6e3a1;"
            )
            self.baslat_btn.setEnabled(False)
            self.durdur_btn.setEnabled(True)
        else:
            self.durum_label.setText("Bekliyor")
            self.durum_label.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: #a6adc8;"
            )
            self.baslat_btn.setEnabled(True)
            self.durdur_btn.setEnabled(False)

    def _ayar_guncelle(self):
        self.konfig["bip_frekans"] = self.frekans_spin.value()
        self.konfig["bip_sure_ms"] = self.sure_spin.value()
        konfig_kaydet(self.konfig)

    def liste_yenile(self):
        self.liste_widget.clear()
        for k in sorted(self.konfig["kufur_listesi"]):
            self.liste_widget.addItem(k)
        n = len(self.konfig["kufur_listesi"])
        self.kelime_sayisi_label.setText(f"Toplam: {n} kelime")

    def baslat(self):
        if self.thread and self.thread.isRunning():
            return
        _calisma_durumu.set()
        self.thread = DinlemeThread(self.konfig)
        self.thread.log_sinyal.connect(self._log)
        self.thread.kufur_sinyal.connect(self._kufur_log)
        self.thread.durum_sinyal.connect(self._durum_guncelle)
        self.thread.start()
        self._log("Filtre başlatılıyor...")

    def durdur(self):
        _calisma_durumu.clear()
        self._durum_guncelle(False)

    def ekle(self):
        kelime = self.kelime_input.text().strip()
        if not kelime:
            return
        if kelime_ekle(self.konfig, kelime):
            self.kelime_input.clear()
            self.liste_yenile()
            self._log(f"'{kelime}' listeye eklendi.")
        else:
            self._log(f"'{kelime}' zaten listede.")

    def sil(self):
        secili = self.liste_widget.currentItem()
        if not secili:
            QMessageBox.information(self, "Uyarı", "Silmek için listeden bir kelime seç.")
            return
        kelime = secili.text()
        if kelime_sil(self.konfig, kelime):
            self.liste_yenile()
            self._log(f"'{kelime}' listeden silindi.")

    def closeEvent(self, event):
        _calisma_durumu.clear()
        if self.thread and self.thread.isRunning():
            self.thread.wait(2000)
        event.accept()


# ─────────────────────────────────────────
# Giriş Noktası
# ─────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pencere = KufurFiltresiGUI()
    pencere.show()
    sys.exit(app.exec())
