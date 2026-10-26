"""Inventario curado. --descargar recupera los documentos exactos del manifiesto."""
import argparse
import pandas as pd
from recuperar_documentos import BASE,recuperar
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--descargar',action='store_true');args=p.parse_args()
    if args.descargar:recuperar()
    else:
        d=pd.read_csv(BASE/'datos/seleccion_documentos.csv');print(d[['id','tipo','fuente_url','licencia','observaciones']].to_string(index=False))
