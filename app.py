import requests
import datetime
import time
import pandas as pd
import json # import json library
import pytz # import pytz library for timezone handling
import streamlit as st
import altair as alt
from streamlit_autorefresh import st_autorefresh

# Sua URL base, com placeholders para a data
URL_TEMPLATE = "https://api.grupoconstruserv.eng.br/lerMedicoes?data={data}&token=faef3e92795eee743adf6d5c9e725647&codigo=1476&tipo=json"

# Função para obter data atual no formato YYYY-MM-DD considerando o fuso horário de São Paulo
def get_data_atual():
    sao_paulo_timezone = pytz.timezone('America/Sao_Paulo')
    sao_paulo_time = datetime.datetime.now(sao_paulo_timezone)
    print(f"Data atual em São Paulo: {sao_paulo_time}")
    return sao_paulo_time.strftime('%Y-%m-%d')

# função para importar o json da url
def import_json_from_url():
    data_atual = get_data_atual() # Obtém a data atual
    url = URL_TEMPLATE.format(data=data_atual) # Constroi a URL com a data atual
    print(url)
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    try:
        dados_json = response.json()
        return dados_json
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format at {url}")
        return None

def gerar_dataframe_medicoes():
    dados_json = import_json_from_url()
    df = pd.DataFrame(dados_json)
    df_medicoes = pd.json_normalize(df['medicoes']) # type: ignore
    df_medicoes.set_index('data', inplace=True)
    df_medicoes['hora'] = pd.to_datetime(df_medicoes.index).strftime('%H:%M')
    df = df_medicoes[['hora','cotareal']].copy() # separa somente a série cotareal
    df.rename(columns={'cotareal': 'montante'}, inplace=True) # rename cotareal column to montante
    # Converter colunas para número
    df['montante'] = pd.to_numeric(df['montante'], errors='coerce')
    return df

def frange(start, stop, step):
    vals = []
    while start <= stop:
        vals.append(start)
        start += step
    return vals

def app():
    st.set_page_config(page_title="UHE Teles Pires - Hidrologia", layout="wide", page_icon="📈")
    st.title("UHE Teles Pires - Hidrologia")

    # Atualização automática a cada minuto
    st_autorefresh(interval=60 * 1000, key="refresh")

    df = gerar_dataframe_medicoes()
    if df.empty:
        st.warning("Nenhum dado disponível para exibir.")
        return

    # Gráfico de linhas suavizadas
    chart_base = (
        alt.Chart(df.reset_index())
        .mark_line(color='green', interpolate='monotone', strokeWidth=5)
        .encode(
            x=alt.X('hora', title='Hora', sort=None),
            y=alt.Y(
                'montante',
                title='Montante',
                scale=alt.Scale(domain=[220.39, 220.45]),
                axis=alt.Axis(format='.2f', values=[round(x, 2) for x in list(frange(220.39, 220.45, 0.01))])
            ),
            tooltip=[alt.Tooltip('hora', title='Hora'), alt.Tooltip('montante', title='Montante', format='.2f')]
        )
        .properties(
            width=1800,  # largura aumentada
            height=500
        )
    )

    # Linhas horizontais de limite em vermelho, tracejadas e mais finas que a série montante
    limites = pd.DataFrame({'y': [220.40, 220.44]})
    linhas_limite = alt.Chart(limites).mark_rule(color='red', strokeWidth=1, strokeDash=[6,4]).encode(y='y')

    # Adiciona marcador e rótulo no último valor da série
    ultimo_ponto = df.reset_index().iloc[[-1]]
    marcador = alt.Chart(ultimo_ponto).mark_circle(color='green', size=100).encode(
        x='hora',
        y='montante',
        tooltip=[alt.Tooltip('hora', title='Hora'), alt.Tooltip('montante', title='Montante', format='.2f')]
    )
    rotulo = alt.Chart(ultimo_ponto).mark_text(
        align='center',
        baseline='bottom',
        dy=-15,  # desloca o texto para cima do ponto
        color='yellow',
        fontSize=18
    ).encode(
        x='hora',
        y='montante',
        text=alt.Text('montante', format='.2f')
    )

    # Combina o gráfico base, linhas de limite, marcador e rótulo
    chart = (
        (chart_base + linhas_limite + marcador + rotulo)
        .properties(
            padding={"left": 20, "right": 20, "top": 20, "bottom": 20},
            background='black'
        )
        .configure_axis(labelFontSize=18, titleFontSize=20)
        .configure_legend(labelFontSize=18, titleFontSize=20)
        .configure_title(fontSize=24)
    )

    st.altair_chart(chart, use_container_width=True)
    st.experimental_rerun = lambda: None  # type: ignore # Evita erro caso não exista
    st.experimental_rerun() # type: ignore

if __name__ == "__main__":
    app()