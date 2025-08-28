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

# --- Função para Carregar e Preparar os Dados (com a correção) ---
@st.cache_data
def carregar_dados(arquivos):
    """
    Carrega, limpa e concatena múltiplos arquivos CSV de forma robusta.
    """
    lista_dfs = []
    for arquivo in arquivos:
        try:
            # Pula as duas primeiras linhas que contêm metadados
            df = pd.read_csv(arquivo, header=2)
            lista_dfs.append(df)
        except Exception as e:
            st.warning(f"Não foi possível processar o arquivo {arquivo.name}: {e}")
    
    if not lista_dfs:
        return pd.DataFrame()

    # Concatena todos os DataFrames
    df_completo = pd.concat(lista_dfs, ignore_index=True)

    # --- Limpeza e Transformação dos Dados (VERSÃO CORRIGIDA) ---
    # Remover colunas completamente vazias
    df_completo.dropna(axis=1, how='all', inplace=True)
    
    # Converter a coluna de data, tratando erros de formato
    # 'errors=coerce' transforma datas mal formatadas em NaT (Not a Time) em vez de travar
    df_completo['Data criação'] = pd.to_datetime(df_completo['Data criação'], errors='coerce')
    
    # Remove as linhas onde a conversão da data falhou
    # Isso garante a integridade dos dados para os filtros e análises
    linhas_originais = len(df_completo)
    df_completo.dropna(subset=['Data criação'], inplace=True)
    linhas_removidas = linhas_originais - len(df_completo)
    if linhas_removidas > 0:
        st.warning(f"{linhas_removidas} linha(s) foram removidas por conterem um formato de data inválido na coluna 'Data criação'.")

    # Renomear colunas para facilitar o uso
    # Usando um 'try-except' para o caso de alguma coluna não existir no arquivo
    try:
        df_completo.rename(columns={
            'Tempo Resolvido (Horas)': 'Tempo Resolvido (h)',
            'Analista Responsável': 'Analista',
            'Categoria 1': 'Categoria',
            'PK Dataset Chamados': 'ID Chamado',
            'Flag Atendeu SLA': 'Status SLA'
        }, inplace=True)
    except KeyError as e:
        st.error(f"Erro ao renomear colunas. Verifique se a coluna {e} existe no seu arquivo.")

    return df_completo


# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.header("Upload de Arquivos")
    arquivos_carregados = st.file_uploader(
        "Selecione os arquivos CSV para análise",
        type=["csv"],
        accept_multiple_files=True
    )

if not arquivos_carregados:
    st.info("Por favor, carregue um ou mais arquivos CSV para iniciar a análise.")
    st.stop()

# Carrega e processa os dados
df_dados = carregar_dados(arquivos_carregados)

if df_dados.empty:
    st.error("Nenhum dado válido foi encontrado nos arquivos carregados.")
    st.stop()

# --- Filtros na Barra Lateral ---
st.sidebar.header("Filtros da Análise")

# Filtro por Analista
analistas = sorted(df_dados['Analista'].dropna().unique())
analista_selecionado = st.sidebar.multiselect(
    'Filtro por Analista',
    options=analistas,
    default=analistas
)

# Filtro por Categoria
categorias = sorted(df_dados['Categoria'].dropna().unique())
categoria_selecionada = st.sidebar.multiselect(
    'Filtro por Categoria',
    options=categorias,
    default=categorias
)

# Filtro por Data
data_min = df_dados['Data criação'].min().date()
data_max = df_dados['Data criação'].max().date()
periodo_selecionado = st.sidebar.date_input(
    'Filtro por Período',
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
    format="DD/MM/YYYY"
)

# --- Aplicação dos Filtros ---
# Verifica se o período selecionado tem duas datas
if len(periodo_selecionado) != 2:
    st.warning("Por favor, selecione um período de início e fim válido.")
    st.stop()

df_filtrado = df_dados[
    (df_dados['Analista'].isin(analista_selecionado)) &
    (df_dados['Categoria'].isin(categoria_selecionada)) &
    (df_dados['Data criação'].dt.date >= periodo_selecionado[0]) &
    (df_dados['Data criação'].dt.date <= periodo_selecionado[1])
]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

# --- Abas para as Análises ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Tempo Médio por Categoria",
    "🧑‍💻 Tempo por Analista e Categoria",
    "🏆 Desempenho por Analista",
    "🗂️ Visão Geral por Categoria"
])

# --- Aba 1: Tempo Gasto por Tipo de Chamado ---
with tab1:
    st.header("Análise do Tempo Médio de Resolução por Categoria")
    
    tempo_por_categoria = df_filtrado.groupby('Categoria')['Tempo Resolvido (h)'].mean().sort_values(ascending=False).reset_index()
    
    fig = px.bar(
        tempo_por_categoria,
        x='Tempo Resolvido (h)',
        y='Categoria',
        orientation='h',
        title='Tempo Médio (em horas) para Resolução por Categoria',
        labels={'Tempo Resolvido (h)': 'Tempo Médio (horas)', 'Categoria': 'Categoria do Chamado'},
        text_auto='.2f'
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig, use_container_width=True)

# --- Aba 2: Tempo Gasto por Analista em Cada Tipo de Chamado ---
with tab2:
    st.header("Análise de Tempo por Analista e Categoria")
    
    tempo_analista_categoria = df_filtrado.groupby(['Analista', 'Categoria'])['Tempo Resolvido (h)'].mean().reset_index()
    
    tabela_pivot = tempo_analista_categoria.pivot(
        index='Analista', 
        columns='Categoria', 
        values='Tempo Resolvido (h)'
    ).fillna(0)
    
    st.dataframe(tabela_pivot.style.background_gradient(cmap='viridis', axis=1).format("{:.2f} h"), use_container_width=True)

# --- Aba 3: Análise de Desempenho por Analista ---
with tab3:
    st.header("Análise de Desempenho por Analista")
    
    desempenho_analista = df_filtrado.groupby('Analista').agg(
        total_chamados=('ID Chamado', 'count'),
        tempo_medio_resolucao=('Tempo Resolvido (h)', 'mean')
    ).reset_index()

    sla_por_analista = df_filtrado.groupby(['Analista', 'Status SLA']).size().unstack(fill_value=0)
    if 'ATENDEU O SLA' in sla_por_analista.columns:
        sla_por_analista['taxa_sla_%'] = (sla_por_analista['ATENDEU O SLA'] / (sla_por_analista.sum(axis=1))) * 100
    else:
        sla_por_analista['taxa_sla_%'] = 0

    desempenho_final = pd.merge(desempenho_analista, sla_por_analista[['taxa_sla_%']], on='Analista')
    desempenho_final.columns = ['Analista', 'Total de Chamados', 'Tempo Médio de Resolução (h)', 'Taxa de SLA (%)']

    st.dataframe(
        desempenho_final.sort_values(by='Total de Chamados', ascending=False).style.format({
            'Tempo Médio de Resolução (h)': '{:.2f} h',
            'Taxa de SLA (%)': '{:.1f}%'
        }), 
        use_container_width=True
    )

# --- Aba 4: Análise por Categoria ---
with tab4:
    st.header("Análise Geral por Categoria")
    
    analise_categoria = df_filtrado.groupby('Categoria').agg(
        total_chamados=('ID Chamado', 'count'),
        tempo_medio_resolucao=('Tempo Resolvido (h)', 'mean')
    ).reset_index()
    
    sla_por_categoria = df_filtrado.groupby(['Categoria', 'Status SLA']).size().unstack(fill_value=0)
    if 'ATENDEU O SLA' in sla_por_categoria.columns:
        sla_por_categoria['taxa_sla_%'] = (sla_por_categoria['ATENDEU O SLA'] / (sla_por_categoria.sum(axis=1))) * 100
    else:
         sla_por_categoria['taxa_sla_%'] = 0
    
    analise_final = pd.merge(analise_categoria, sla_por_categoria[['taxa_sla_%']], on='Categoria')
    analise_final.columns = ['Categoria', 'Total de Chamados', 'Tempo Médio de Resolução (h)', 'Taxa de SLA (%)']
    
    st.dataframe(
        analise_final.sort_values(by='Total de Chamados', ascending=False).style.format({
            'Tempo Médio de Resolução (h)': '{:.2f} h',
            'Taxa de SLA (%)': '{:.1f}%'
        }), 
        use_container_width=True
    )
