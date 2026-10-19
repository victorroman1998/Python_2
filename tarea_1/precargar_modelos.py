"""Descarga a la caché local los modelos base del segundo notebook."""
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODELOS = [
    ("Recognai/bert-base-spanish-wwm-cased-xnli", None),
    ("distilbert/distilbert-base-multilingual-cased", 4),
]


def main() -> None:
    for nombre, clases in MODELOS:
        print(f"Descargando {nombre}...", flush=True)
        AutoTokenizer.from_pretrained(nombre)
        parametros = {"num_labels": clases} if clases else {}
        AutoModelForSequenceClassification.from_pretrained(nombre, **parametros)
        print(f"Listo: {nombre}", flush=True)


if __name__ == "__main__":
    main()
