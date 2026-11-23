import json
import re
from datetime import date
import requests
from bs4 import BeautifulSoup

ARQUIVO = "tarifas_vale.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"
}

def limpar(txt):
    return " ".join(txt.split())

def salvar_se_mudou(dados, chave, novo_valor, vigencia, hoje):
    if novo_valor and 2.50 <= novo_valor <= 150.00:
        atual = dados.get(chave, {})
        if atual.get("valor") != novo_valor or atual.get("vigencia_oficial") != vigencia:
            dados[chave] = {
                "valor": round(novo_valor, 2),
                "vigencia_oficial": vigencia,
                "atualizado_em": hoje
            }
            print(f"[ATUALIZADO] {chave}: R$ {novo_valor:.2f}")

def buscar_internas_guara(dados, hoje):
    url = "https://otimizapro.com"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        texto = limpar(BeautifulSoup(r.text, "html.parser").get_text())
        m_val = re.search(r"custa R\$\s*(\d+,\d{2})", texto)
        m_vig = re.search(r"desde\s*(\d{2}/\d{2}/\d{4})", texto)
        if m_val:
            val = float(m_val.group(1).replace(",", "."))
            vig = m_vig.group(1) if m_vig else "Decreto Municipal"
            for chave in list(dados.keys()):
                if chave.startswith("INTERNA "):
                    salvar_se_mudou(dados, chave, val, vig, hoje)
    except Exception as e:
        print("Erro internas Guará:", e)

def buscar_todas_emtu_guara(dados, hoje):
    # 1. Consulta todas as linhas da Pássaro Marron no Vale do Paraíba (EMTU)
    url_lista = "http://emtu.sp.gov.br"
    try:
        r = requests.get(url_lista, headers=HEADERS, timeout=25)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")

        for tr in soup.find_all("tr"):
            tds = [limpar(td.get_text()) for td in tr.find_all("td")]
            if len(tds) >= 4:
                linha_cod = tds
                trajeto = tds
                tarifa_txt = tds
                if "GUARATINGUETA" in trajeto.upper() and "R$" in tarifa_txt:
                    m_val = re.search(r"R\$\s*(\d+,\d{2})", tarifa_txt)
                    if m_val:
                        val = float(m_val.group(1).replace(",", "."))
                        partes = [p.strip().title() for p in trajeto.split("-")]
                        if len(partes) >= 2:
                            c1, c2 = partes, partes[-1]
                            salvar_se_mudou(dados, f"IDA • {c1} → {c2} (EMTU {linha_cod})", val, "Tabela EMTU", hoje)
                            salvar_se_mudou(dados, f"VOLTA • {c2} → {c1} (EMTU {linha_cod})", val, "Tabela EMTU", hoje)
    except Exception as e:
        print("Erro lista geral EMTU:", e)

    # 2. Consulta todos os seccionamentos (trechos intermediários) da linha 5305 que ligam Guará
    url_5305 = "https://emtu.sp.gov.br"
    try:
        r = requests.get(url_5305, headers=HEADERS, timeout=25)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")
        texto_full = limpar(soup.get_text())
        m_data = re.search(r"Data da base de dados:\s*(\d{2}/\d{2}/\d{4})", texto_full)
        vig = f"Base EMTU {m_data.group(1)}" if m_data else "Tabela EMTU 5305"

        for tr in soup.find_all("tr"):
            tds = [limpar(td.get_text()) for td in tr.find_all("td")]
            if len(tds) >= 2 and "GUARATINGUETA" in tds.upper() and "R$" in tds:
                m_val = re.search(r"R\$\s*(\d+,\d{2})", tds)
                if m_val:
                    val = float(m_val.group(1).replace(",", "."))
                    trecho = re.sub(r"\([^)]*\)", "", tds).strip().title()
                    partes = [p.strip() for p in trecho.split("-")]
                    if len(partes) >= 2:
                        c1, c2 = partes, partes[-1]
                        salvar_se_mudou(dados, f"IDA • {c1} → {c2} (Seletivo 5305)", val, vig, hoje)
                        salvar_se_mudou(dados, f"VOLTA • {c2} → {c1} (Seletivo 5305)", val, vig, hoje)
    except Exception as e:
        print("Erro seccionamentos 5305:", e)

def buscar_rodoviarios_passaro_marron(dados, hoje):
    # Consulta rotas rodoviárias onde Ida e Volta podem ter valores distintos
    rotas_rodoviarias = [
        ("IDA • Guaratinguetá → São José dos Campos (Pássaro Marron)", "https://passaromarron.com.br"),
        ("VOLTA • São José dos Campos → Guaratinguetá (Pássaro Marron)", "https://passaromarron.com.br"),
        ("IDA • Guaratinguetá → Taubaté (Rodoviário Pássaro Marron)", "https://passaromarron.com.br"),
        ("VOLTA • Taubaté → Guaratinguetá (Rodoviário Pássaro Marron)", "https://passaromarron.com.br")
    ]
    for chave, url in rotas_rodoviarias:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                texto = limpar(BeautifulSoup(r.text, "html.parser").get_text())
                # Busca valores em reais listados na página da rota e pega a tarifa base (menor valor válido)
                valores = [float(v.replace(",", ".")) for v in re.findall(r"R\$\s*(\d+,\d{2})", texto)]
                valores_validos = [v for v in valores if 10.0 <= v <= 120.0]
                if valores_validos:
                    salvar_se_mudou(dados, chave, min(valores_validos), "Site Pássaro Marron", hoje)
        except Exception as e:
            print(f"Erro rota rodoviária {chave}:", e)

def main():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = {}

    hoje = date.today().strftime("%d/%m/%Y")
    buscar_internas_guara(dados, hoje)
    buscar_todas_emtu_guara(dados, hoje)
    buscar_rodoviarios_passaro_marron(dados, hoje)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False, sort_keys=True)

if __name__ == "__main__":
    main()
