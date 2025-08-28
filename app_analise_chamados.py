import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(page_title="Análise de Chamados de TI", page_icon="📊", layout="wide")
st.title("📊 Dashboard de Análise de Chamados")

# --- Função para Carregar e Preparar os Dados ---
@st.cache_data
def carregar_dados(arquivos_carregados):
    if not arquivos_carregados:
        return pd.DataFrame()

    lista_dfs_limpos = []
    for arquivo in arquivos_carregados:
        try:
            df_temp = pd.read_csv(arquivo, header=2, low_memory=False)

            # 1. Padronizar coluna de data
            if 'Data criação' in df_temp.columns:
                df_temp.rename(columns={'Data criação': 'Data Padronizada'}, inplace=True)
            elif 'Data/Hora criação' in df_temp.columns:
                df_temp.rename(columns={'Data/Hora criação': 'Data Padronizada'}, inplace=True)
            else:
                st.warning(f"O arquivo '{arquivo.name}' foi ignorado por não conter uma coluna de data esperada.")
                continue

            # 2. Padronizar outras colunas
            mapa_renomear = {
                'Analista Responsável': 'Analista', 'Categoria 1': 'Categoria',
                'Tempo Resolvido (Horas)': 'Tempo Resolvido (h)', 'PK Dataset Chamados': 'ID Chamado',
                'Flag Atendeu SLA': 'Status SLA'
            }
            df_temp.rename(columns={k: v for k, v in mapa_renomear.items() if k in df_temp.columns}, inplace=True)
            
            # 3. Converter tipos de dados
            df_temp['Data Padronizada'] = pd.to_datetime(df_temp['Data Padronizada'], errors='coerce', dayfirst=True)
            df_temp['Tempo Resolvido (h)'] = pd.to_numeric(df_temp['Tempo Resolvido (h)'], errors='coerce')

            # 4. Remover linhas com dados inválidos
            df_temp.dropna(subset=['Data Padronizada', 'Tempo Resolvido (h)', 'Analista', 'Categoria'], inplace=True)
            
            if not df_temp.empty:
                lista_dfs_limpos.append(df_temp)

        except Exception as e:
            st.warning(f"Ocorreu um erro ao processar o arquivo '{arquivo.name}': {str(e)}")

    if not lista_dfs_limpos:
        return pd.DataFrame()
    
    return pd.concat(lista_dfs_limpos, ignore_index=True)


# --- Barra Lateral e Carregamento de Arquivos ---
with st.sidebar:
    st.header("Upload de Arquivos")
    arquivos_carregados = st.file_uploader("Selecione os arquivos CSV", type=["csv"], accept_multiple_files=True)
    if st.button('Limpar Cache e Recarregar'):
        st.cache_data.clear()
        st.rerun()

if not arquivos_carregados:
    st.info("Por favor, carregue um ou mais arquivos CSV para iniciar a análise.")
    st.stop()

df_dados = carregar_dados(arquivos_carregados)

if df_dados.empty:
    st.error("Nenhum dado válido foi encontrado nos arquivos. Verifique o conteúdo dos arquivos ou os avisos acima.")
    st.stop()

# --- Filtros na Barra Lateral ---
st.sidebar.header("Filtros da Análise")
analistas = sorted(df_dados['Analista'].dropna().unique())
categorias = sorted(df_dados['Categoria'].dropna().unique())

analista_selecionado = st.sidebar.multiselect('Filtro por Analista', options=analistas, default=analistas)
categoria_selecionada = st.sidebar.multiselect('Filtro por Categoria', options=categorias, default=categorias)

try:
    data_min = df_dados['Data Padronizada'].min().date()
    data_max = df_dados['Data Padronizada'].max().date()
    periodo_selecionado = st.sidebar.date_input('Filtro por Período', value=(data_min, data_max), min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
except Exception as e:
    st.error(f"Ocorreu um erro ao criar o filtro de data: {str(e)}")
    st.stop()

# --- LÓGICA DE FILTRAGEM CORRIGIDA ---
if not periodo_selecionado or len(periodo_selecionado) != 2:
    st.warning("Aguardando um período de data válido...")
    st.stop()
else:
    start_date = pd.to_datetime(periodo_selecionado[0])
    end_date = pd.to_datetime(periodo_selecionado[1]) + pd.Timedelta(days=1) # Garante inclusão do dia inteiro

    df_filtrado = df_dados[
        (df_dados['Analista'].isin(analista_selecionado)) &
        (df_dados['Categoria'].isin(categoria_selecionada)) &
        (df_dados['Data Padronizada'] >= start_date) &
        (df_dados['Data Padronizada'] < end_date)
    ]

# --- Painel de Status na Barra Lateral ---
st.sidebar.header("Status da Carga")
st.sidebar.info(f"Total de Registros Carregados: **{len(df_dados)}**")
st.sidebar.info(f"Período Detectado: **{data_min.strftime('%d/%m/%Y')}** a **{data_max.strftime('%d/%m/%Y')}**")
st.sidebar.success(f"Registros Após Filtro: **{len(df_filtrado)}**")


if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# --- Abas para as Análises ---
st.success(f"Exibindo {len(df_filtrado)} registros com base nos filtros selecionados.")
tab1, tab2, tab3, tab4 = st.tabs(["📈 T. Médio Categoria", "🧑‍💻 T. Analista/Categoria", "🏆 Desempenho Analista", "🗂️ Visão Categoria"])

with tab1:
    # O código das abas continua o mesmo
    st.header("Análise do Tempo Médio de Resolução por Categoria")
    tempo_por_categoria = df_filtrado.groupby('Categoria')['Tempo Resolvido (h)'].mean().sort_values(ascending=False).reset_index()
    fig = px.bar(tempo_por_categoria, x='Tempo Resolvido (h)', y='Categoria', orientation='h', title='Tempo Médio (em horas)', text_auto='.2f')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Análise de Tempo por Analista e Categoria")
    tempo_analista_categoria = df_filtrado.groupby(['Analista', 'Categoria'])['Tempo Resolvido (h)'].mean().reset_index()
    tabela_pivot = tempo_analista_categoria.pivot(index='Analista', columns='Categoria', values='Tempo Resolvido (h)').fillna(0)
    st.dataframe(tabela_pivot.style.background_gradient(cmap='viridis', axis=1).format("{:.2f} h"), use_container_width=True)

with tab3:
    st.header("Análise de Desempenho por Analista")
    desempenho_analista = df_filtrado.groupby('Analista').agg(total_chamados=('ID Chamado', 'count'), tempo_medio_resolucao=('Tempo Resolvido (h)', 'mean')).reset_index()
    sla_por_analista = df_filtrado.groupby(['Analista', 'Status SLA']).size().unstack(fill_value=0)
    if 'ATENDEU O SLA' in sla_por_analista.columns:
        sla_por_analista['taxa_sla_%'] = (sla_por_analista['ATENDEU O SLA'] / sla_por_analista.sum(axis=1)) * 100
    else:
        sla_por_analista['taxa_sla_%'] = 0
    desempenho_final = pd.merge(desempenho_analista, sla_por_analista[['taxa_sla_%']], on='Analista', how='left').fillna(0)
    desempenho_final.columns = ['Analista', 'Total de Chamados', 'Tempo Médio de Resolução (h)', 'Taxa de SLA (%)']
    st.dataframe(desempenho_final.sort_values(by='Total de Chamados', ascending=False).style.format({'Tempo Médio de Resolução (h)': '{:.2f} h', 'Taxa de SLA (%)': '{:.1f}%'}), use_container_width=True)

with tab4:
    st.header("Análise Geral por Categoria")
    analise_categoria = df_filtrado.groupby('Categoria').agg(total_chamados=('ID Chamado', 'count'), tempo_medio_resolucao=('Tempo Resolvido (h)', 'mean')).reset_index()
    sla_por_categoria = df_filtrado.groupby(['Categoria', 'Status SLA']).size().unstack(fill_value=0)
    if 'ATENDEU O SLA' in sla_por_categoria.columns:
        sla_por_categoria['taxa_sla_%'] = (sla_por_categoria['ATENDEU O SLA'] / sla_por_categoria.sum(axis=1)) * 100
    else:
        sla_por_categoria['taxa_sla_%'] = 0
    analise_final = pd.merge(analise_categoria, sla_por_categoria[['taxa_sla_%']], on='Categoria', how='left').fillna(0)
    analise_final.columns = ['Categoria', 'Total de Chamados', 'Tempo Médio de Resolução (h)', 'Taxa de SLA (%)']
    st.dataframe(analise_final.sort_values(by='Total de Chamados', ascending=False).style.format({'Tempo Médio de Resolução (h)': '{:.2f} h', 'Taxa de SLA (%)': '{:.1f}%'}), use_container_width=True)
