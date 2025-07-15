import streamlit as st
import easyocr
import pandas as pd
import re
import io
from PIL import Image
import numpy as np

st.set_page_config(page_title="Extrator de Rotas", page_icon="📦")
st.title("📦 Extrator de Endereços de Rotas")
st.markdown("Envie **um ou mais prints** de rotas para extrair os endereços, CEPs e pacotes automaticamente.")

cidade = st.text_input("Cidade", "São José dos Campos")
estado = st.text_input("Estado", "São Paulo")

def formatar_cep(cep):
    cep = ''.join(filter(str.isdigit, str(cep)))
    return f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep

def extrair_dados_texto(linhas, cidade, estado):
    dados = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]

        if not re.search(r'(Rua|Avenida|Travessa|Alameda|Estrada|Viela)', linha, re.IGNORECASE):
            i += 1
            continue

        match_endereco = re.match(r'^(.*?\d{1,5})\b', linha)
        endereco = match_endereco.group(1) if match_endereco else linha

        bairro, cep, unidades, parada = '', '', '', ''

        if i + 1 < len(linhas) and 'CEP' in linhas[i + 1]:
            bairro_match = re.search(r'^(.*?),?\s*CEP', linhas[i + 1])
            cep_match = re.search(r'CEP\s*(\d{8})', linhas[i + 1])
            if bairro_match:
                bairro = bairro_match.group(1).strip()
            if cep_match:
                cep = formatar_cep(cep_match.group(1))
            i += 1

        if i + 1 < len(linhas) and 'horário comercial' in linhas[i + 1].lower():
            i += 1

        if i + 1 < len(linhas) and 'Entrega' in linhas[i + 1]:
            unidades_match = re.search(r'Entrega\s+(\d+)\s+unidade', linhas[i + 1])
            if unidades_match:
                qtd = unidades_match.group(1)
                unidades = f"{qtd} pacote" if qtd == '1' else f"{qtd} pacotes"

            etiqueta_match = re.search(r'NX\d+[_\-\. ]*(\d{1,3})', linhas[i + 1])
            if etiqueta_match:
                parada = f"Parada {etiqueta_match.group(1)}"
            i += 1

        dados.append({
            'Parada': parada,
            'ID do Pacote': '',
            'Total de Pacotes': unidades,
            'Address Line': endereco.strip(),
            'Secondary Address Line': bairro,
            'City': cidade,
            'State': estado,
            'Zip Code': cep
        })

        i += 1
    return dados

arquivos = st.file_uploader("Envie os prints das rotas (JPG ou PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

if arquivos:
    reader = easyocr.Reader(['pt'], gpu=False)
    todas_linhas = []

    for img_file in arquivos:
        img = Image.open(img_file)
        resultado = reader.readtext(np.array(img), detail=0, paragraph=False)
        linhas = [linha.strip() for linha in resultado if linha.strip()]
        dados = extrair_dados_texto(linhas, cidade, estado)
        todas_linhas.extend(dados)

    if todas_linhas:
        df = pd.DataFrame(todas_linhas)
        st.success("✅ Dados extraídos com sucesso!")
        st.dataframe(df)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Baixar Excel", data=output.getvalue(), file_name="rotas_extraidas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.warning("⚠️ Nenhum dado foi encontrado.")
