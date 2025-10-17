import csv

def ler_classes_lulc_csv(path_csv):
    """
    Lê o CSV delimitado por ';' e retorna um dicionário:
    classes_lulc[int(Class_ID)] = {'Level':..., 'Description':..., 'Descricao':..., 'Color':..., 'Grupos':..., 'SWAT':...}
    Em caso de duplicidade de Class_ID, mantém a primeira ocorrência.
    """
    classes_lulc = {}
    with open(path_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            cid_raw = row.get('Class_ID') or row.get('ClassId') or row.get('ID')
            if cid_raw is None or cid_raw == '':
                continue
            # remove espaços e possíveis aspas
            cid_raw = cid_raw.strip()
            try:
                cid = int(cid_raw)
            except Exception:
                # pula ids não inteiros
                continue
            if cid in classes_lulc:
                # já temos uma entrada; mantém primeira ocorrência
                continue
            classes_lulc[cid] = {
                'Level': row.get('Level', '').strip() if row.get('Level') else '',
                'Description': row.get('Description', '').strip() if row.get('Description') else '',
                'Descricao': row.get('Descricao', '').strip() if row.get('Descricao') else (row.get('Description', '').strip() if row.get('Description') else ''),
                'Color': row.get('Color', '').strip() if row.get('Color') else '',
                'Grupos': row.get('Grupos', '').strip() if row.get('Grupos') else '',
                'SWAT': row.get('SWAT', '').strip() if row.get('SWAT') else ''
            }
    return classes_lulc