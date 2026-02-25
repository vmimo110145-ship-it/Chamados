import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import base64
import uuid
from datetime import datetime

# --- CONFIGURAÇÕES DE DIRETÓRIO ---
APP_DIR = os.path.join(os.path.expanduser("~"), ".condominio_final_v8")
DB_PATH = os.path.join(APP_DIR, "condominio.db")
UPLOAD_DIR = os.path.join(APP_DIR, "evidencias")

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- FUNÇÕES DE SEGURANÇA E CÁLCULO ---
def hash_password(plain: str) -> str:
    salt = b'salt_condo_pro_2026_final' 
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100_000)
    return base64.b64encode(dk).decode()

def verify_password(plain: str, stored: str) -> bool:
    return hash_password(plain) == stored

def calcular_tempo_finalizacao(data_inicio_str, data_fim_str):
    try:
        fmt = "%d/%m/%Y %H:%M"
        inicio = datetime.strptime(data_inicio_str, fmt)
        fim = datetime.strptime(data_fim_str, fmt)
        diferenca = fim - inicio
        dias = diferenca.days
        horas = diferenca.seconds // 3600
        minutos = (diferenca.seconds // 60) % 60
        
        resultado = []
        if dias > 0: resultado.append(f"{dias}d")
        if horas > 0: resultado.append(f"{horas}h")
        if minutos > 0 or not resultado: resultado.append(f"{minutos}min")
        
        return " ".join(resultado)
    except:
        return "N/A"

# --- BANCO DE DADOS ---
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, role TEXT NOT NULL)")
    cur.execute("""CREATE TABLE IF NOT EXISTS ocorrencias (
                    id TEXT PRIMARY KEY, tipo_registro TEXT, categoria TEXT NOT NULL, 
                    local_detalhado TEXT, descricao TEXT NOT NULL, foto_path TEXT, 
                    status TEXT DEFAULT 'Pendente', data_envio TEXT, data_conclusao TEXT)""")
    cur.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios VALUES (?, ?, ?)", ("admin", hash_password("admin123"), "admin"))
    conn.commit()
    conn.close()

init_db()

# --- INTERFACE ---
st.set_page_config(page_title="Condomínio Pro", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #007BFF; color: white; }
    .stTextInput>div>div>input { border-radius: 10px; }
    [data-testid="stExpander"] { border-radius: 12px; border: 1px solid #ddd; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

if "auth_adm" not in st.session_state:
    st.session_state.auth_adm = False

st.sidebar.title("🏢 Gestão Pro")
menu = st.sidebar.radio("Navegação", ["📝 Abrir Registro", "🔍 Consultar Protocolo", "📊 Painel Administrativo"])

# --- 1. ABRIR REGISTRO (PÚBLICO) ---
if menu == "📝 Abrir Registro":
    st.header("Novo Registro")
    with st.container(border=True):
        tipo_reg = st.radio("O que deseja realizar?", ["Abertura de Chamado", "Denúncia"], horizontal=True)
        
        if tipo_reg == "Denúncia":
            st.info("🔒 **Sua denúncia é 100% anônima.** Não solicitamos dados pessoais. O síndico visualizará apenas o local e as evidências relatadas.")
        
        categorias = ["Corredor/Andar", "Garagem", "Jardim", "Academia", "Piscina", "Elevador", "Salão de Festas", "Outros"]
        cat_sel = st.selectbox("Selecione a área:", categorias)
        
        detalhe = ""
        if cat_sel == "Corredor/Andar":
            detalhe = st.selectbox("Escolha o Andar:", [f"{i}º Andar" for i in range(1, 21)])
        elif cat_sel == "Garagem":
            detalhe = st.selectbox("Nível da Garagem:", ["G1", "G2", "G3"])
        
        # AJUSTE: Texto conforme solicitado
        desc = st.text_area("Relato da Ocorrência:", placeholder="Descreva os detalhes aqui...")
        
        # AJUSTE: Foto opcional para todos os casos
        foto = st.file_uploader("📸 Anexar Foto (Opcional)", type=["jpg", "png", "jpeg"])
        
        if st.button("ENVIAR REGISTRO", type="primary"):
            if not desc:
                st.error("Por favor, preencha o relato da ocorrência.")
            else:
                protocolo = str(uuid.uuid4())[:8].upper()
                caminho_foto = None
                if foto:
                    caminho_foto = os.path.join(UPLOAD_DIR, f"{protocolo}_{foto.name}")
                    with open(caminho_foto, "wb") as f: f.write(foto.getbuffer())
                
                with get_conn() as conn:
                    conn.execute("""INSERT INTO ocorrencias 
                        (id, tipo_registro, categoria, local_detalhado, descricao, foto_path, data_envio) 
                        VALUES (?,?,?,?,?,?,?)""",
                        (protocolo, tipo_reg, cat_sel, detalhe, desc, caminho_foto, datetime.now().strftime("%d/%m/%Y %H:%M")))
                
                st.success(f"✅ {tipo_reg} enviado com sucesso!")
                st.markdown(f"### Protocolo: `{protocolo}`")

# --- 2. CONSULTAR PROTOCOLO ---
elif menu == "🔍 Consultar Protocolo":
    st.header("Acompanhar Status")
    busca = st.text_input("Digite o Protocolo:").upper().strip()
    if busca:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM ocorrencias WHERE id = ?", (busca,))
            res = cur.fetchone()
        if res:
            with st.container(border=True):
                st.subheader(f"Status Atual: {res[6]}")
                st.write(f"**Tipo:** {res[1]}")
                st.write(f"**Aberto em:** {res[7]}")
                st.write(f"**Relato da Ocorrência:** {res[4]}")
                
                # AJUSTE: Exibe quando foi finalizado e o tempo decorrido
                if res[8]:
                    tempo_total = calcular_tempo_finalizacao(res[7], res[8])
                    st.success(f"✅ **Serviço Finalizado em:** {res[8]} \n\n **Tempo de Resolução:** {tempo_total}")
                
                if res[5]: st.image(res[5])
        else:
            st.error("Protocolo não localizado.")

# --- 3. PAINEL ADMINISTRATIVO ---
elif menu == "📊 Painel Administrativo":
    if not st.session_state.auth_adm:
        st.header("Acesso Restrito")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT password_hash FROM usuarios WHERE username = ?", (u,))
                db_res = cur.fetchone()
            if db_res and verify_password(p, db_res[0]):
                st.session_state.auth_adm = True
                st.rerun()
            else: st.error("Acesso negado.")
    else:
        st.header("Gestão do Condomínio")
        tab1, tab2 = st.tabs(["Atendimentos Ativos", "Relatório de Conclusão"])
        
        with tab1:
            df = pd.read_sql("SELECT * FROM ocorrencias WHERE status != 'Concluído' ORDER BY data_envio DESC", get_conn())
            for _, row in df.iterrows():
                icone = "🚨" if row['tipo_registro'] == "Denúncia" else "🛠️"
                with st.expander(f"{icone} {row['tipo_registro']} | {row['id']}"):
                    st.write(f"**Data de Abertura:** {row['data_envio']}")
                    st.write(f"**Relato:** {row['descricao']}")
                    if row['foto_path']: st.image(row['foto_path'])
                    
                    st.divider()
                    # AJUSTE: Campo de status
                    novo_st = st.selectbox("Status Mudar:", ["Pendente", "Em Manutenção", "Concluído"], 
                                         index=["Pendente", "Em Manutenção", "Concluído"].index(row['status']),
                                         key=f"st_{row['id']}")
                    
                    if st.button("Salvar Alteração", key=f"sv_{row['id']}"):
                        # AJUSTE: Registra a data de conclusão se o status for finalizado
                        data_fim = datetime.now().strftime("%d/%m/%Y %H:%M") if novo_st == "Concluído" else None
                        with get_conn() as conn:
                            conn.execute("UPDATE ocorrencias SET status = ?, data_conclusao = ? WHERE id = ?", (novo_st, data_fim, row['id']))
                        st.success("Status atualizado com sucesso!")
                        st.rerun()
                    
                    if st.button("🗑️ Deletar Registro", key=f"del_{row['id']}"):
                        with get_conn() as conn:
                            conn.execute("DELETE FROM ocorrencias WHERE id = ?", (row['id'],))
                        st.rerun()

        with tab2:
            st.subheader("Histórico de Serviços Resolvidos")
            df_rep = pd.read_sql("SELECT * FROM ocorrencias WHERE status = 'Concluído' ORDER BY data_conclusao DESC", get_conn())
            if not df_rep.empty:
                # AJUSTE: Coluna de tempo decorrido no relatório
                df_rep['Tempo p/ Conclusão'] = df_rep.apply(lambda r: calcular_tempo_finalizacao(r['data_envio'], r['data_conclusao']), axis=1)
                st.dataframe(df_rep[['id', 'tipo_registro', 'data_envio', 'data_conclusao', 'Tempo p/ Conclusão']], 
                             use_container_width=True, hide_index=True)
                st.metric("Total de Ocorrências Finalizadas", len(df_rep))
            else:
                st.info("Nenhum serviço finalizado para exibir no relatório.")