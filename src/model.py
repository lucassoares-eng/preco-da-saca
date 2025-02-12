import requests
import pandas as pd
import sqlite3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# Configuração inicial
START_YEAR = datetime.now().year - 30
END_YEAR = datetime.now().year
DB_NAME = "soja_pr.db"

# Criar conexão com banco de dados
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Criar tabelas se não existirem
cursor.execute('''CREATE TABLE IF NOT EXISTS soja_preco (
                    date TEXT PRIMARY KEY, 
                    price REAL, 
                    seasonality TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS clima (
                    date TEXT PRIMARY KEY, 
                    precipitation REAL, 
                    temperature REAL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS cambio (
                    date TEXT PRIMARY KEY, 
                    usd_brl REAL)''')

conn.commit()

# Função para determinar a sazonalidade trimestral
def get_seasonality(date):
    month = datetime.strptime(date, "%d/%m/%Y").month
    if month in [1, 2, 3]:
        return "Q1"
    elif month in [4, 5, 6]:
        return "Q2"
    elif month in [7, 8, 9]:
        return "Q3"
    else:
        return "Q4"

# Função para coletar preços históricos da soja (CEPEA/ESALQ)
def get_soja_prices():
    url = "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Exemplo: Capturar dados da tabela (precisa ser ajustado conforme estrutura do site)
    rows = soup.find_all("tr")
    data = []
    for row in rows[1:]:  # Pulando cabeçalho
        cols = row.find_all("td")
        if len(cols) > 1:
            date = cols[0].text.strip()
            price = float(cols[1].text.replace("R$", "").replace(",", "."))
            seasonality = get_seasonality(date)
            data.append((date, price, seasonality))
            
    df = pd.DataFrame(data, columns=["date", "price", "seasonality"])
    df.to_sql("soja_preco", conn, if_exists="replace", index=False)
    print("Preços da soja coletados!")

# Função para coletar dados climáticos do INMET
def get_climate_data():
    base_url = "https://apitempo.inmet.gov.br/"
    for year in range(START_YEAR, END_YEAR + 1):
        response = requests.get(f"{base_url}/dados/{year}")
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            df = df[["data", "precipitacao", "tempMedia"]]
            df.rename(columns={"data": "date", "precipitacao": "precipitation", "tempMedia": "temperature"}, inplace=True)
            df.to_sql("clima", conn, if_exists="append", index=False)
            print(f"Clima do ano {year} coletado!")

# Função para coletar câmbio do Banco Central
def get_usd_brl():
    url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data)
        df.rename(columns={"data": "date", "valor": "usd_brl"}, inplace=True)
        df.to_sql("cambio", conn, if_exists="replace", index=False)
        print("Câmbio coletado!")

# Executar as coletas de dados
get_soja_prices()
get_climate_data()
get_usd_brl()

# Fechar conexão
conn.close()
print("Dados coletados e armazenados!")