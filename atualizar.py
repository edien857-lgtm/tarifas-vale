import json
import re
from datetime import date
import requests
from bs4 import BeautifulSoup

ARQUIVO = "tarifas_vale.json"

FONTES = {
    "Lorena ↔ Guaratinguetá (Comum - Linha 5312)": (
        "https://emtu.sp.gov.br",
        "Tarifa Autorizada"
    ),
    "Aparecida ↔ Guaratinguetá (Comum - Linha 5316)": (
        "https://emtu.sp.gov.br",
        "5316"
    ),
    "Lorena ↔ Guaratinguetá (Seletivo - Linha 5305)": (
        "https://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=50094",
        "LORENA (TERMINAL RODOVIARIO DE LORENA) - GUARATINGUETA"
    ),
    "Guaratinguetá ↔ Aparecida (Seletivo - Linha 5305)": (
        "https://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=50094",
        "GUARATINGUETA (TERMINAL ROD. DE GUARATINGUETA) - APARECIDA"
    ),
    "Lorena ↔ São José dos Campos (Seletivo - Linha 5305)": (
        "https://www.emtu.sp.gov.br/sistemas/linha/resultado_imp.htm?numlinha=50094",
        "Tarifa Autorizada"
    )
}

def buscar_tarifa(url, termo_busca):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.encoding = "iso-8859-1"
        soup = BeautifulSoup(resp.text, "html.parser")

        for linha in soup.find_all(["tr", "p", "div"]):
            texto = " ".join(linha.get_text().split())
            if termo_busca in texto:
                match = re.search(r"R\$\s*(\d+,\d{2})", texto)
                if match:
                    return float(match.group(1).replace(",", "."))
    except Exception as e:
        print(f"Erro ao acessar {url}: {e}")
    return None

def main():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except FileNotFoundError:
        dados = {}

    alterou = False
    for trecho, (url, termo) in FONTES.items():
        valor_novo = buscar_tarifa(url, termo)
        valor_antigo = dados.get(trecho, {}).get("valor")

        if valor_novo and 2.0 <= valor_novo <= 150.0 and valor_novo != valor_antigo:
            dados[trecho] = {
                "valor": valor_novo,
                "atualizado_em": str(date.today())
            }
            alterou = True
            print(f"[ATUALIZADO] {trecho}: R$ {valor_novo:.2f}")
        else:
            print(f"[SEM ALTERAÇÃO] {trecho}: mantido em R$ {valor_antigo}")

    if alterou:
        with open(ARQUIVO, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
