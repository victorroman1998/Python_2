"""Recupera exactamente las páginas y fotografías del manifiesto, sin texto sintético."""
from pathlib import Path
import hashlib,json
import pandas as pd
from PIL import Image,ImageOps
from red import descargar
BASE=Path(__file__).resolve().parent

def recuperar():
    m=pd.read_csv(BASE/'datos/seleccion_documentos.csv',dtype=str,keep_default_na=False)
    originales=BASE/'datos/raw/documentos/fuentes';originales.mkdir(parents=True,exist_ok=True)
    for r in m.itertuples():
        salida=BASE/r.archivo
        if salida.exists() and hashlib.sha256(salida.read_bytes()).hexdigest()==r.sha256:continue
        es_pdf=bool(r.pagina_origen);ori=originales/(r.sha256_original+('.pdf' if es_pdf else '.jpg'))
        if not ori.exists():descargar(r.url_descarga,ori)
        if hashlib.sha256(ori.read_bytes()).hexdigest()!=r.sha256_original:raise ValueError('El original cambió: '+r.id)
        if es_pdf:
            import pypdfium2 as pdfium
            pdf=pdfium.PdfDocument(ori);im=pdf[int(r.pagina_origen)-1].render(scale=2.5).to_pil().convert('RGB')
        else:im=ImageOps.exif_transpose(Image.open(ori)).convert('RGB')
        if r.recorte_relativo:
            crop=json.loads(r.recorte_relativo);w,h=im.size;im=im.crop(tuple(round(x*n) for x,n in zip(crop,[w,h,w,h])))
        salida.parent.mkdir(parents=True,exist_ok=True);im.save(salida,quality=95)
        if hashlib.sha256(salida.read_bytes()).hexdigest()!=r.sha256:raise ValueError('Raster distinto: comprobar versiones Pillow/pypdfium2 para '+r.id)
        print('Recuperado:',r.id,flush=True)
if __name__=='__main__':recuperar()
