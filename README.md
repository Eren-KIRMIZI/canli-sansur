# Türkçe Küfür Filtresi & Canlı Sansür Sistemi

Bu proje, mikrofon üzerinden alınan canlı sesleri dinleyerek Türkçe konuşmayı metne dönüştüren ve belirlenen kelimeler (küfür, argo, yasaklı kelimeler vb.) algılandığında sesli uyarı veren bir masaüstü uygulamasıdır.

Uygulama PyQt6 ile geliştirilmiş modern bir arayüze sahiptir ve ayarlar kalıcı olarak saklanır.

---

## Örnek Küfür Listesi

Uygulama aşağıdaki kelimelerle önceden yüklenmiş olarak gelir:
```python
VARSAYILAN_KUFURLER = [
    "yozgat", "aptal",
    "ahmak", "budala",
    "lan", "ulan",
    "beyinsiz", "kafasız", "manyak"
]
```

Listeyi uygulama içinden düzenleyerek genişletebilirsin.

---

<img width="1366" height="724" alt="image" src="https://github.com/user-attachments/assets/4eeb827b-57f5-4142-9dcd-6d7d536bcfd4" />

---

## Özellikler

- Gerçek zamanlı mikrofon dinleme
- Türkçe konuşma tanıma (Google Speech API)
- Küfür tespitinde anlık BİP sansürü
- Kelime bazlı eşleme — yanlış alarm engellenir (`lan` ≠ `lanet`)
- Küfür listesini uygulama içinden düzenleme (ekle / sil)
- BİP frekansı ve süresi ayarlanabilir
- Tüm konuşmalar ve tespitler log dosyasına yazılır
- Ayarlar `kufur_config.json` dosyasında kalıcı olarak saklanır
- Windows, Linux ve macOS desteği

---

## Kurulum

### Gereksinimler

```bash
pip install SpeechRecognition pyaudio PyQt6
```

> **Linux:** PyAudio için önce sistem paketini kur:
> ```bash
> sudo apt install portaudio19-dev
> ```

> **macOS:**
> ```bash
> brew install portaudio
> ```

### Çalıştırma

```bash
python kufur_filtresi_gui.py
```

---

## Kullanım

1. Uygulamayı aç
2. **Başlat** butonuna bas — mikrofon dinlemeye geçer
3. Konuşmalar canlı log panelinde görünür
4. Küfür tespit edildiğinde log kırmızıya döner ve BİP çalar
5. Sağ panelden kelime ekleyip silebilir, ses ayarlarını değiştirebilirsin
6. **Durdur** ile dinleme sonlandırılır

---
