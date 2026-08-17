# Photo EXIF Extractor

Copia le foto da una cartella sorgente in sottocartelle per data EXIF (`YYYY_MM_DD`), dentro `estrazione_del_YYYY_MM_DD` (data di esecuzione). Le originali non vengono spostate.

Richiede **Python 3.11+**.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Modifica `.env` con i path reali.

## Uso

Dalla root del progetto:

```bash
python -m src.main
```

Le foto senza data EXIF vanno nella cartella configurata con `NO_DATE_FOLDER` nel `.env` (default: `senza_data`). File con lo stesso nome vengono rinominati `foto_1.jpg`, `foto_2.jpg`, …

## Test

```bash
pytest
```
