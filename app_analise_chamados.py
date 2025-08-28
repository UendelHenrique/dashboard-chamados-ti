import streamlit as st
import pandas as pd
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(
    page_title="Análise de Chamados de TI",
    page_icon="📊",
    layout="wide"
)

# --- Título do Dashboard ---
st.title("📊 Dashboard de Análise de Chamados")

# --- Função para Carregar e Preparar os Dados ---
@st.cache_data
def carregar_dados(arquivos):
    """
    Carrega, limpa e concatena múltiplos arquivos CSV de forma robusta.
    """
    if not arquivos:
        return pd.DataFrame()

    lista_dfs = []
    for arquivo in arquivos:
        try:
            df = pd.read_csv(arquivo, header=2, low_memory=False)
            lista_dfs.append(df)
        except Exception as e:
            st.warning(f"Não foi possível processar o arquivo {arquivo.name}: {str(e)}")
    
    if not lista_dfs:
        return pd.DataFrame()

    df_completo = pd.concat(lista_dfs, ignore_index=True)
    
    # --- PASSO 1: PADRONIZAR A COLUNA DE DATA ---
    if 'Data criação' in df_completo.columns:
        df_completo.rename(columns={'Data criação': 'Data Padronizada'}, inplace=True)
    elif 'Data/Hora criação' in df_completo.columns:
        df_completo.rename(columns={'Data/Hora criação': 'Data Padronizada'}, inplace=True)
    else:
        st.error("Erro Crítico: Nenhuma coluna de data ('Data criação' ou 'Data/Hora criação') foi encontrada nos arquivos.")
        return pd.DataFrame()

    # --- PASSO 2: PADRONIZAR OUTRAS COLUNAS ---
    mapa_renomear = {
        'Analista Responsável': 'Analista',
        'Categoria 1': 'Categoria',
        'Tempo Resolvido (Horas)': 'Tempo Resolvido (h)',
        'PK Dataset Chamados': 'ID Chamado',
        'Flag Atendeu SLA': 'Status SLA'
    }
    df_completo.rename(columns={k: v for k, v in mapa_renomear.items() if k in df_completo.columns}, inplace=True)

    # --- PASSO 3: VERIFICAR COLUNAS ESSENCIAIS ---
    colunas_essenciais = ['Data Padronizada', 'Tempo Resolvido (h)', 'Analista', 'Categoria', 'ID Chamado', 'Status SLA']
    for col in colunas_essenciais:
        if col not in df_completo.columns:
            st.error(f"Erro Crítico: A coluna essencial '{col}' não foi encontrada nos arquivos após a padronização.")
            return pd.DataFrame()

    # --- PASSO 4: LIMPEZA E CONVERSÃO DE TIPOS ---
    df_completo['Data Padronizada'] = pd.to_datetime(df_completo['Data Padronizada'], errors='coerce', dayfirst=True)
    df_completo['Tempo Resolvido (h)'] = pd.to_numeric(df_completo['Tempo Resolvido (h)'], errors='coerce')

    df_completo.dropna(subset=['Data Padronizada', 'Tempo Resolvido (h)'], inplace=True)

    return df_completo

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("Upload de Arquivos")
    arquivos_carregados = st.file_uploader("Selecione os arquivos CSV", type=["csv"], accept_multiple_files=True)

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
analista_selecionado = st.sidebar.multiselect('Filtro por Analista', options=analistas, default=analistas)

categorias = sorted(df_dados['Categoria'].dropna().unique())
categoria_selecionada = st.sidebar.multiselect('Filtro por Categoria', options=categorias, default=categorias)

# --- Filtro por Data (usando a coluna padronizada) ---
try:
    min_val = df_dados['Data Padronizada'].min()
    max_val = df_dados['Data Padronizada'].max()
    data_min = pd.to_datetime(min_val).date()
    data_max = pd.to_datetime(max_val).date()

    periodo_selecionado = st.sidebar.date_input('Filtro por Período', value=(data_min, data_max), min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
    
    if not isinstance(periodo_selecionado, tuple) or len(periodo_selecionado) != 2:
        st.warning("Aguardando um período de data válido...")
        st.stop()

except Exception as e:
    st.error(f"Ocorreu um erro ao criar o filtro de data: {str(e)}")
    st.stop()

# --- Aplicação dos Filtros ---
df_filtrado = df_dados[
    (df_dados['Analista'].isin(analista_selecionado)) &
    (df_dados['Categoria'].isin(categoria_selecionada)) &
    (df_dados['Data Padronizada'].dt.date >= periodo_selecionado[0]) &
    (df_dados['Data Padronizada'].dt.date <= periodo_selecionado[1])
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# --- Abas para as Análises ---
st.success(f"Exibindo {len(df_filtrado)} registros com base nos filtros selecionados.")
tab1, tab2, tab3, tab4 = st.tabs(["📈 T. Médio Categoria", "🧑‍💻 T. Analista/Categoria", "🏆 Desempenho Analista", "🗂️ Visão Categoria"])

with tab1:
    st.header("Análise do Tempo Médio de Resolução por Categoria")
    # ... (o resto do código das abas continua o mesmo, sem necessidade de alteração)
    tempo_por_categoria = df_filtrado.groupby('Categoria')['Tempo Resolvido (h)'].mean().sort_values(ascending=False).reset_index()
    fig = px.bar(tempo_por_categoria, x='Tempo Resolvido (h)', y='Categoria', orientation='h', title='Tempo Médio (em horas) para Resolução por Categoria', labels={'Tempo Resolvido (h)': 'Tempo Médio (horas)', 'Categoria': 'Categoria do Chamado'}, text_auto='.2f')
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
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
