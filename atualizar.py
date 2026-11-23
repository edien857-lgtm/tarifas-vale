import json
import re
from datetime import date
import requests
from bs4 import BeautifulSoup

ARQUIVO = "tarifas_vale.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# Mapeamento direto das fichas oficiais da EMTU (Pássaro Marron) ligadas a Guaratinguetá
FICHAS_EMTU = [
    ("5316", "http://www.emtu.sp.gov.br/Sistemas/linha/resultado.htm?numlinha=5316&pag=buscanumero.htm", "Guaratinguetá", "Aparecida (EMTU 5316 Comum)"),
    ("5318", "http://www.emtu.sp.gov.br/Sistemas/linha/resultado.htm?numlinha=5318&pag=buscanumero.htm", "Guaratinguetá", "Potim (EMTU 5318 Comum)"),
    ("5312", "http://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=50836", "Guaratinguetá", "Lorena (EMTU 5312 Comum)"),
    ("5311", "http://www.emtu.sp.gov.br/Sistemas/linha/resultado.htm?numlinha=5311&pag=buscanumero.htm", "Guaratinguetá", "Pindamonhangaba (EMTU 5311 / 5311EX1)"),
    ("5402", "http://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=43008", "Guaratinguetá", "Bananal (EMTU 5402 Seletivo)")
]

def limpar(txt):
    return " ".join(txt.split())

def atualizar_internas_guara(dados, hoje):
    url = "https://otimizapro.com"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        texto = limpar(BeautifulSoup(r.text, "html.parser").get_text())
        m_val = re.search(r"custa R\$\s*(\d+,\d{2})", texto)
        m_vig = re.search(r"desde\s*(\d{2}/\d{2}/\d{4})", texto)
        if m_val:
            val = float(m_val.group(1).replace(",", "."))
            vig = m_vig.group(1) if m_vig else "25/03/2026"
            for chave in list(dados.keys()):
                if chave.startswith("INTERNA "):
                    if dados[chave].get("valor") != val or dados[chave].get("vigencia_oficial") != vig:
                        dados[chave]["valor"] = val
                        dados[chave]["vigencia_oficial"] = vig
                        dados[chave]["atualizado_em"] = hoje
    except Exception as e:
        print("Erro internas Guará:", e)

def atualizar_emtu(dados, hoje):
    for codigo, url, orig, dest in FICHAS_EMTU:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            r.encoding = "iso-8859-1"
            texto = limpar(BeautifulSoup(r.text, "html.parser").get_text())

            # Captura a data oficial da base de dados da EMTU (ex: Data da base de dados: 23/11/2026)
            m_data = re.search(r"Data da base de dados:\s*(\d{2}/\d{2}/\d{4})", texto)
            vig = f"Base EMTU {m_data.group(1)}" if m_data else "Tabela EMTU"

            m_val = re.search(r"R\$\s*(\d+,\d{2})", texto)
            if m_val:
                val = float(m_val.group(1).replace(",", "."))
                if 2.0 <= val <= 150.0:
                    for prefixo, c1, c2 in [("IDA", orig, dest), ("VOLTA", dest.split(" (")[0], f"{orig} ({dest.split(' (')[1]}")]:
                        chave = f"{prefixo} • {c1} → {c2}"
                        if chave in dados and (dados[chave].get("valor") != val or dados[chave].get("vigencia_oficial") != vig):
                            dados[chave]["valor"] = val
                            dados[chave]["vigencia_oficial"] = vig
                            dados[chave]["atualizado_em"] = hoje
        except Exception as e:
            print(f"Erro EMTU {codigo}:", e)

def main():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = {}

    hoje = date.today().strftime("%d/%m/%Y")
    atualizar_internas_guara(dados, hoje)
    atualizar_emtu(dados, hoje)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
