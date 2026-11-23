import json
import re
from datetime import date
import requests
from bs4 import BeautifulSoup

ARQUIVO = "tarifas_vale.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def limpar(txt):
    return " ".join(txt.split())

def atualizar_municipal_guara(dados):
    url = "https://otimizapro.com/tarifa/sp/guaratingueta"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        texto = limpar(BeautifulSoup(r.text, "html.parser").get_text())
        m_val = re.search(r"custa R\$\s*(\d+,\d{2})", texto)
        m_vig = re.search(r"desde\s*(\d{2}/\d{2}/\d{4})", texto)
        if m_val:
            val = float(m_val.group(1).replace(",", "."))
            vig = m_vig.group(1) if m_vig else "Decreto Municipal"
            chave = "Municipal Guaratinguetá (TUG - Urbano Interno)"
            if dados.get(chave, {}).get("valor") != val:
                dados[chave] = {
                    "valor": val,
                    "vigencia_oficial": vig,
                    "atualizado_em": date.today().strftime("%d/%m/%Y")
                }
    except Exception as e:
        print("Erro municipal Guará:", e)

def atualizar_emtu_passaro_marron(dados):
    # 1. Busca todas as linhas da Pássaro Marron (operadora=273) no Vale (regiao=257)
    url_empresa = "http://www.emtu.sp.gov.br/sistemas/linha/resultado.htm?pag=buscaempresa.htm&operadora=273&regiao=257"
    try:
        r = requests.get(url_empresa, headers=HEADERS, timeout=20)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")
        for tr in soup.find_all("tr"):
            cols = [limpar(td.get_text()) for td in tr.find_all("td")]
            if len(cols) >= 4 and "GUARATINGUETA" in cols[1].upper():
                num = cols[0]
                desc = cols[1].title()
                m = re.search(r"R\$\s*(\d+,\d{2})", cols[3])
                if m:
                    val = float(m.group(1).replace(",", "."))
                    chave = f"EMTU {num} • {desc}"
                    if dados.get(chave, {}).get("valor") != val:
                        dados[chave] = {
                            "valor": val,
                            "vigencia_oficial": "Tabela EMTU/ARTESP",
                            "atualizado_em": date.today().strftime("%d/%m/%Y")
                        }
    except Exception as e:
        print("Erro lista Pássaro Marron EMTU:", e)

    # 2. Busca todos os seccionamentos da Linha 5305 (Seletivo) ligando Guaratinguetá
    url_5305 = "https://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=50094"
    try:
        r = requests.get(url_5305, headers=HEADERS, timeout=20)
        r.encoding = "iso-8859-1"
        soup = BeautifulSoup(r.text, "html.parser")
        texto_geral = limpar(soup.get_text())
        m_vig = re.search(r"Vig[êe]ncia[^0-9]*(\d{2}/\d{2}/\d{4})", texto_geral, re.I)
        vig = m_vig.group(1) if m_vig else "Tabela EMTU 5305"

        for tr in soup.find_all("tr"):
            cols = [limpar(td.get_text()) for td in tr.find_all("td")]
            if len(cols) >= 2 and "GUARATINGUETA" in cols[0].upper() and "R$" in cols[1]:
                m = re.search(r"R\$\s*(\d+,\d{2})", cols[1])
                if m:
                    val = float(m.group(1).replace(",", "."))
                    trecho_limpo = re.sub(r"\([^)]*\)", "", cols[0]).strip().title()
                    chave = f"Seletivo 5305 • {trecho_limpo}"
                    if dados.get(chave, {}).get("valor") != val:
                        dados[chave] = {
                            "valor": val,
                            "vigencia_oficial": vig,
                            "atualizado_em": date.today().strftime("%d/%m/%Y")
                        }
    except Exception as e:
        print("Erro seccionamentos 5305:", e)

def main():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = {}

    # Garante linhas adicionais importantes (ex: Cunha e Rodoviário Guará x SJC)
    extras = {
        "EMTU 5319 • Guaratinguetá ↔ Cunha (Rodov. São José)": 19.20,
        "Rodoviário Pássaro Marron • Guaratinguetá ↔ SJC": 39.40
    }
    for k, v in extras.items():
        if k not in dados:
            dados[k] = {
                "valor": v,
                "vigencia_oficial": "Tabela ARTESP 2026",
                "atualizado_em": date.today().strftime("%d/%m/%Y")
            }

    atualizar_municipal_guara(dados)
    atualizar_emtu_passaro_marron(dados)

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False, sort_keys=True)

if __name__ == "__main__":
    main()
