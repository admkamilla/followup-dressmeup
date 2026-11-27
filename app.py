"""FOLLOW UP - DRESS ME UP GOIANIA

App da equipe de vendas: lista de clientes para follow-up, atualizada com a agenda da loja.
Não mostra valores, pedidos ou faturamento.
"""
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="FOLLOW UP - DRESS ME UP GOIANIA", page_icon="📋", layout="wide")

STATUS = ["Por fazer", "Tentei, sem resposta", "Em conversa", "Reagendou", "Dados para contrato", "Fechou", "Não vai fechar"]
MOTIVOS = ["", "Preço", "Alugou em outro lugar", "Não encontrou o vestido", "Desistiu do evento", "Comprou vestido", "Outro"]
SITUACAO = {"Não compareceu": "Faltou", "Atendida, não fechou": "Veio e não fechou", "Em aberto": "Veio, conferir se fechou"}
COR_SIT = {"Faltou": "#8a2f3b", "Veio e não fechou": "#9a5a2b", "Veio, conferir se fechou": "#2d3f5f"}
EQUIPE_VENDAS = ["Natalya", "Raquel", "Jéssica Martins", "Andressa", "Kerem"]
VENDEDORAS = ["Todas"] + EQUIPE_VENDAS + ["Sem vendedora"]
POR_PAGINA = 25
INATIVIDADE_MIN = 5  # desconecta depois de 5 minutos sem uso
DOMINIO = "followup.dressmeup.com.br"  # e-mail interno: usuario@DOMINIO (não recebe mensagens)

st.markdown("""
<style>
/* esconde a barra do Streamlit (Share, estrela, editar, GitHub, Deploy, menu) */
[data-testid="stToolbar"],[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"],.stAppDeployButton,
[data-testid="stMainMenu"],#MainMenu,[data-testid="stDecoration"]{display:none!important}
header[data-testid="stHeader"]{background:transparent;height:0}
/* dados internos: não imprime (sai página em branco) e não deixa selecionar/copiar texto da tela */
@media print{body *{display:none!important}body:after{content:"Conteúdo interno da DRESS ME UP. Impressão não permitida.";display:block;padding:40px;font:16px sans-serif}}
.stApp{-webkit-user-select:none;user-select:none}
.stApp input,.stApp textarea{-webkit-user-select:text;user-select:text}
.marca{position:fixed;right:14px;bottom:10px;font-size:.7rem;color:#6e2a4f;opacity:.55;pointer-events:none;z-index:999}
.block-container{max-width:1400px;padding-top:1.8rem!important}
h1{font-size:1.6rem!important;padding-bottom:0!important}
.quem{font-size:1.15rem;color:#6e2a4f;margin:.35rem 0 .6rem;letter-spacing:.02em}
.cab{display:flex;flex-wrap:wrap;align-items:center;gap:6px;line-height:1.6;padding-bottom:2px}
.cli-nome{font-size:.98rem;font-weight:600;margin:0;text-transform:capitalize}
.cli-meta{color:#6b6570;font-size:.8rem;margin:0;line-height:1.45}
.cli-meta a{color:#1a7f4b;font-weight:600;text-decoration:none}
.pill{display:inline-block;font-size:.68rem;font-weight:600;border-radius:999px;padding:1px 8px;color:#fff}
.auto{color:#6e2a4f;font-size:.78rem;margin:0}
.stamp{color:#8a8590;font-size:.7rem}
.enviada{color:#2f5f9e;font-size:.78rem;font-weight:600}
/* cartão enxuto */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{gap:.5rem}
[data-testid="stForm"]{padding:0}
[data-testid="stForm"] label p{font-size:.72rem;color:#6b6570}
[data-testid="stForm"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap;gap:.5rem}
[data-testid="stForm"] [data-testid="stColumn"],[data-testid="stForm"] [data-testid="column"]{min-width:0!important}
[data-testid="stExpander"] details{border:none}
[data-testid="stExpander"] summary{padding:.15rem 0;font-size:.8rem;color:#6e2a4f}
[data-testid="stForm"] button{padding:.25rem .4rem;min-height:2.4rem;white-space:nowrap}
[data-testid="stForm"] button p{font-size:.85rem}
.dia{display:flex;justify-content:space-between;align-items:baseline;gap:8px;background:#2b2a2e;color:#fff;
 border-radius:10px;padding:10px 14px;margin:22px 0 8px}
.dia b{font-size:1.05rem}.dia span{font-size:.8rem;opacity:.8}
.dia.hoje{background:#6e2a4f}.dia.sem{background:#6b6570}
.cli-nome.nc{text-transform:none}
table.resumo{width:100%;border-collapse:collapse;font-size:.82rem;background:#fff;border-radius:10px;overflow:hidden;margin:4px 0 10px}
table.resumo th{background:#2b2a2e;color:#fff;font-weight:600;padding:6px 6px;text-align:center;font-size:.72rem}
table.resumo th:first-child,table.resumo td:first-child{text-align:left;padding-left:10px}
table.resumo td{padding:6px;text-align:center;border-top:1px solid #ece9ee;font-variant-numeric:tabular-nums}
table.resumo tr.total td{font-weight:700;background:#f6f2f5}
table.resumo td.alerta{color:#8a2f3b;font-weight:700}
.resumo-wrap{overflow-x:auto}
.hora{font-weight:700;color:#6e2a4f;margin-right:2px}
[data-testid="stRadio"] label p{font-size:.8rem}
[data-testid="stRadio"] [role="radiogroup"]{gap:.15rem .55rem!important}
[data-testid="stRadio"] [role="radiogroup"] label{margin-right:0!important;padding-right:0!important}
[data-testid="stPopover"] button{min-height:2.2rem;padding:.3rem .6rem}
[data-testid="stPopover"] button p{font-size:.85rem}
.nota{color:#6e2a4f;font-size:.8rem}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTextInput"] [data-baseweb="input"]{background:#fff;border:1px solid #e3dee6;border-radius:8px}
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stTextInput"] input{font-size:.85rem}
.falta{color:#8a2f3b;font-size:.78rem;font-weight:600}
[data-testid="stLinkButton"] a{padding:.3rem .6rem;min-height:2.2rem}
[data-testid="stLinkButton"] p{font-size:.85rem}
</style>
""", unsafe_allow_html=True)


# ---------- conexão e login ----------
def cliente_supabase():
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return st.session_state.sb


def tela_login():
    _, meio, _ = st.columns([1, 1.4, 1])
    with meio:
        st.title("Follow up · DRESS ME UP Goiânia")
        st.caption("Entre com o usuário e a senha que a Kami cadastrou para você.")
        if st.session_state.pop("msg_saida", None):
            st.info(f"Você foi desconectada depois de {INATIVIDADE_MIN} minutos sem uso. Entre de novo.")
        with st.form("login"):
            usuario = st.text_input("Usuário").strip().lower()
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary"):
                email = usuario if "@" in usuario else f"{usuario}@{DOMINIO}"
                try:
                    res = cliente_supabase().auth.sign_in_with_password({"email": email, "password": senha})
                    st.session_state.user_email = res.user.email.split("@")[0]
                    st.rerun()
                except Exception:
                    st.error("Usuário ou senha incorretos. Confira e tente de novo.")


def sair():
    try:
        cliente_supabase().auth.sign_out()
    except Exception:
        pass
    for k in ("sb", "user_email", "nome_vendedora", "gestora", "ultima_atividade"):
        st.session_state.pop(k, None)
    st.rerun()


# ---------- dados ----------
def carregar():
    sb = cliente_supabase()
    try:
        clientes = sb.table("clientes").select("*").execute().data or []
        fus = sb.table("followups").select("*").execute().data or []
    except Exception:
        # sessão expirada: tenta renovar uma vez
        try:
            sb.auth.refresh_session()
            clientes = sb.table("clientes").select("*").execute().data or []
            fus = sb.table("followups").select("*").execute().data or []
        except Exception:
            st.warning("Sua sessão expirou. Entre de novo.")
            sair()
            return [], {}
    return clientes, {f["cliente_id"]: f for f in fus}


def status_efetivo(c, f):
    """O que a agenda informou vale se for mais recente que o último registro da equipe."""
    auto_em, f_em = c.get("auto_em"), (f or {}).get("em")
    if c.get("auto_status") and (not f_em or (auto_em and auto_em > f_em)):
        return c["auto_status"], True
    return (f or {}).get("status") or "Por fazer", False


def salvar(cliente_id, status, proximo, motivo, nota):
    cliente_supabase().table("followups").upsert({
        "cliente_id": cliente_id,
        "status": status,
        "proximo": proximo.isoformat() if proximo else None,
        "motivo": motivo or None,
        "nota": nota or None,
        "por": st.session_state.get("user_email"),
        "em": datetime.now(timezone.utc).isoformat(),
    }).execute()


SEMANA = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


def titulo_dia(agendado):
    """Título do grupo: dia em que a cliente estava agendada na agenda da loja."""
    if not agendado:
        return "Sem data na agenda", "sem"
    d = date.fromisoformat(agendado)
    dias = (date.today() - d).days
    rotulo = f"{SEMANA[d.weekday()]}, {d:%d/%m}"
    if dias == 0: return f"Agendadas hoje · {rotulo}", "hoje"
    if dias == 1: return f"Agendadas ontem · {rotulo}", ""
    if dias < 0: return f"Agendadas para {rotulo}", ""
    return f"Agendadas {rotulo} · há {dias} dias", ""


def ddmm(s):
    return f"{s[8:10]}/{s[5:7]}/{s[2:4]}" if s else "—"


def fone(t):
    if not t:
        return ""
    vis = f"({t[:2]}) {t[2:-4]}-{t[-4:]}" if len(t) >= 10 else t
    return f"[WhatsApp {vis}](https://wa.me/55{t})"


def fone_html(t):
    vis = f"({t[:2]}) {t[2:-4]}-{t[-4:]}" if len(t) >= 10 else t
    return f'<a href="https://wa.me/55{t}" target="_blank">WhatsApp {vis}</a>'


def tabela_resumo(linhas, colunas, alerta=()):
    """linhas: lista de (nome, {coluna: n}); última linha = total."""
    th = "".join(f"<th>{c}</th>" for c in ["Vendedora"] + colunas)
    corpo = ""
    for i, (nome, cont) in enumerate(linhas):
        cls = ' class="total"' if i == len(linhas) - 1 else ""
        tds = "".join(f'<td class="{"alerta" if c in alerta and cont.get(c) else ""}">{cont.get(c, 0) or "–"}</td>' for c in colunas)
        corpo += f"<tr{cls}><td>{nome}</td>{tds}</tr>"
    st.markdown(f'<div class="resumo-wrap"><table class="resumo"><tr>{th}</tr>{corpo}</table></div>', unsafe_allow_html=True)


# ---------- acesso só na rede da loja ----------
def ip_cliente():
    try:
        h = st.context.headers
        ip = (h.get("X-Forwarded-For") or "").split(",")[0].strip() or (h.get("X-Real-Ip") or "").strip()
    except Exception:
        ip = ""
    return ip


def rede_de(ip):
    """IPv4 inteiro; IPv6 pelo prefixo /64 (a parte final muda sozinha)."""
    if not ip:
        return ""
    return ":".join(ip.split(":")[:4]) + "::/64" if ":" in ip else ip


def redes_liberadas():
    try:
        return cliente_supabase().table("redes_liberadas").select("*").execute().data or []
    except Exception:
        return None  # se não der para ler, não trava ninguém


def bloqueio_fora_da_loja():
    """Vendedora fora da internet da loja: mostra aviso e não abre os dados."""
    lib = redes_liberadas()
    if not lib:  # nenhuma rede cadastrada ainda = sem restrição
        return False
    if rede_de(ip_cliente()) in {r["rede"] for r in lib}:
        return False
    st.error("🔒 Este app só abre na internet da loja. Conecte no Wi-Fi da DRESS ME UP e entre de novo.")
    return True


def painel_rede(nome):
    """Para as gestoras: liberar ou remover a internet da loja."""
    lib = redes_liberadas() or []
    rede = rede_de(ip_cliente())
    ativo = bool(lib)
    with st.expander("🔒 Acesso das vendedoras: " + ("só na internet da loja" if ativo else "liberado em qualquer lugar")):
        st.caption("Com uma rede cadastrada, as vendedoras só conseguem abrir o app conectadas nela. "
                   "Você e a Tamires entram de qualquer lugar. Se a internet da loja trocar de endereço "
                   "(acontece quando o roteador reinicia), as vendedoras vão ver o aviso: é só uma de vocês, "
                   "na loja, tocar em Liberar de novo.")
        st.markdown(f"Internet desta conexão agora: **{rede or 'não identificada'}**")
        for r in lib:
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.markdown(f"✅ **{r.get('nome') or 'Loja'}** · {r['rede']} · liberada por {(r.get('por') or '').capitalize()}")
            if b.button("Remover", key=f"rm_{r['rede']}"):
                cliente_supabase().table("redes_liberadas").delete().eq("rede", r["rede"]).execute()
                st.rerun()
        if rede and rede not in {r["rede"] for r in lib}:
            if st.button("📍 Estou na loja: liberar esta internet", type="primary"):
                cliente_supabase().table("redes_liberadas").insert(
                    {"rede": rede, "nome": "Loja", "por": st.session_state.get("user_email")}).execute()
                st.rerun()
        elif not rede:
            st.warning("Não consegui identificar a internet desta conexão, então não dá para liberar daqui.")


# ---------- tela principal ----------
def tela_lista():
    topo, botao = st.columns([6, 1], vertical_alignment="center")
    topo.title("Follow up · DRESS ME UP Goiânia")
    if botao.button("Sair", icon="🚪", use_container_width=True):
        sair()
    nome = st.session_state.get("nome_vendedora")
    if nome is None:
        try:
            r = cliente_supabase().table("equipe").select("nome,papel").execute().data
            nome = r[0]["nome"].split()[0] if r else ""
            st.session_state.gestora = bool(r) and r[0].get("papel") == "gestora"
        except Exception:
            nome = ""
        st.session_state.nome_vendedora = nome
    gestora = st.session_state.get("gestora", False)
    if nome:
        st.markdown(f'<div class="marca">Uso interno DRESS ME UP · {nome} · {hoje_local():%d/%m/%Y}</div>', unsafe_allow_html=True)
        st.markdown(f'<p class="quem">{"Gestora" if gestora else "Vendedora"}: <b>{nome.upper()}</b></p>',
                    unsafe_allow_html=True)
    if not gestora and bloqueio_fora_da_loja():
        return
    if gestora:
        painel_rede(nome)
    if gestora:
        # gestoras acompanham só o follow-up (resumo por vendedora); a confirmação fica com as vendedoras
        tela_followup(nome, gestora)
        return
    aba = st.radio("Tela", ["📲 Confirmar agendamentos", "📋 Follow-up"], horizontal=True,
                   label_visibility="collapsed", key="aba")
    if aba.startswith("📲"):
        tela_confirmar(nome, gestora)
    else:
        tela_followup(nome, gestora)


def tela_followup(nome, gestora):
    st.caption("Clientes que faltaram ou não fecharam, com evento por vir.")

    clientes, fus = carregar()
    hoje = date.today().isoformat()
    lista = []
    for c in clientes:
        if c.get("evento") and c["evento"] < hoje:
            continue
        f = fus.get(c["id"])
        st_ef, auto = status_efetivo(c, f)
        c = dict(c, _f=f or {}, _status=st_ef, _auto=auto,
                 _sit=SITUACAO.get(c.get("etapa"), ""),
                 _vend=(c.get("vend_atend") or ""))
        lista.append(c)

    if not lista:
        st.info("A lista está vazia. Ela é preenchida automaticamente com a agenda da loja.")
        return

    # retorno vencido: tinha próximo contato marcado para antes de hoje e não foi resolvida
    for c in lista:
        prox = c["_f"].get("proximo")
        c["_vencido"] = bool(prox and prox < hoje and c["_status"] not in ("Fechou", "Não vai fechar"))

    semana_ini = (hoje_local() - timedelta(days=6)).isoformat()  # últimos 7 dias, contando hoje
    if gestora:
        resumo_semana(lista, semana_ini)
    else:
        cont = {s: sum(1 for c in lista if c["_status"] == s) for s in STATUS}
        st.markdown(" · ".join(f"**{n}** {s.lower()}" for s, n in cont.items() if n))

    PERIODOS = ["Últimos 7 dias", "Fila antiga (mais de 7 dias)", "Todos"]
    cols_f = st.columns(4)
    filtro_per = cols_f[0].selectbox("Período na agenda", PERIODOS, index=0 if gestora else 2)
    filtro_status = cols_f[1].selectbox("Follow-up", ["Todos"] + STATUS + ["Retorno vencido"], index=1)
    filtro_sit = cols_f[2].selectbox("Situação", ["Todas"] + list(SITUACAO.values()))
    if gestora:
        filtro_vend = cols_f[3].selectbox("Vendedora", ["Todas"] + EQUIPE_VENDAS)
    else:
        filtro_vend = "Todas"
        ordem = cols_f[3].selectbox("Ordenar por", ORDENS)

    ocasioes = sorted({_ocasiao(c) for c in lista if _ocasiao(c)})
    meses = sorted({c["evento"][:7] for c in lista if c.get("evento")})
    OPC_EVENTO = ["Todas", "Próximos 15 dias", "Próximos 30 dias", "Próximos 60 dias"] + [_nome_mes(m) for m in meses]
    cols_g = st.columns([2, 2, 2, 3] if gestora else [2, 2, 3])
    filtro_oc = cols_g[0].selectbox("Ocasião", ["Todas"] + ocasioes)
    filtro_ev = cols_g[1].selectbox("Data do evento", OPC_EVENTO)
    if gestora:
        ordem = cols_g[2].selectbox("Ordenar por", ORDENS)
    busca = cols_g[-1].text_input("Buscar nome ou telefone").strip().lower()
    mes_ev = {_nome_mes(m): m for m in meses}
    dias_ev = {"Próximos 15 dias": 15, "Próximos 30 dias": 30, "Próximos 60 dias": 60}

    def passa(c):
        ult = c.get("ultimo") or ""
        if filtro_per == PERIODOS[0] and ult < semana_ini: return False
        if filtro_per == PERIODOS[1] and ult >= semana_ini: return False
        if filtro_status == "Retorno vencido":
            if not c["_vencido"]: return False
        elif filtro_status != "Todos" and c["_status"] != filtro_status: return False
        if filtro_sit != "Todas" and c["_sit"] != filtro_sit: return False
        if filtro_vend != "Todas" and c.get("vend_atend") != filtro_vend: return False
        if filtro_oc != "Todas" and _ocasiao(c) != filtro_oc: return False
        ev = c.get("evento") or ""
        if filtro_ev in dias_ev and not (ev and ev <= (date.today() + timedelta(days=dias_ev[filtro_ev])).isoformat()):
            return False
        if filtro_ev in mes_ev and ev[:7] != mes_ev[filtro_ev]: return False
        if busca:
            dig = "".join(ch for ch in busca if ch.isdigit())
            if busca not in (c.get("nome") or "").lower() and not (dig and dig in (c.get("tel") or "")): return False
        return True

    # mais recente primeiro: quem esteve na agenda por último é quem pede retorno antes
    if ordem == ORDENS[1]:  # evento mais próximo primeiro
        filtrada = sorted(filter(passa, lista), key=lambda c: (c.get("evento") or "9999", c.get("nome") or ""))
    else:
        filtrada = sorted(filter(passa, lista), key=lambda c: (c.get("ultimo") or "", c.get("nome") or ""), reverse=True)
    st.caption(f"{len(filtrada)} clientes nesta lista · marcou, salvou: vale na hora para toda a equipe.")
    cartoes_followup(filtrada, gestora, agrupar=(ordem == ORDENS[0]))


LIMITE_TABELA = 300
COR_FU = {"Por fazer": "#8a8590", "Tentei, sem resposta": "#b5761b", "Em conversa": "#2f5f9e", "Reagendou": "#5b4a8a",
          "Dados para contrato": "#0f7a76", "Fechou": "#1a7f4b", "Não vai fechar": "#8a2f3b"}
SIT_CURTA = {"Veio e não fechou": "Não fechou", "Veio, conferir se fechou": "Conferir"}


def _salvar_card(cid):
    """Salva na hora qualquer mudança do cartão (status, retorno, motivo, anotação)."""
    ss = st.session_state
    status = ss.get(f"s_{cid}") or "Por fazer"
    base = ss.get("_fu_atual", {}).get(cid, {})
    motivo = (ss.get(f"m_{cid}") if f"m_{cid}" in ss else base.get("motivo")) or "" if status == "Não vai fechar" else ""
    prox = ss.get(f"p_{cid}") if f"p_{cid}" in ss else (date.fromisoformat(base["proximo"]) if base.get("proximo") else None)
    try:
        salvar(cid, status, prox, motivo, ss.get(f"n_{cid}") or "")
        st.toast("Escolha o motivo no cartão." if status == "Não vai fechar" and not motivo else "Salvo para toda a equipe.")
    except Exception:
        st.toast("Não consegui salvar. Tente de novo.")


def dia_curto(agendado):
    """'2026-11-27' -> ('sexta, 27/11', 'hoje')"""
    if not agendado:
        return "Sem data na agenda", "sem"
    d = date.fromisoformat(agendado)
    return f"{SEMANA[d.weekday()]}, {d:%d/%m}", ("hoje" if d == hoje_local() else "")


def cartoes_followup(clientes, gestora, agrupar=True):
    if not clientes:
        st.info("Nenhuma cliente com esses filtros.")
        return
    mostrar = st.session_state.get("fu_mostrar", POR_PAGINA)
    st.session_state._fu_atual = {c["id"]: c["_f"] for c in clientes[:mostrar]}
    grupo_atual = None
    for c in clientes[:mostrar]:
        if agrupar:
            titulo, cls = dia_curto(c.get("ultimo"))
            if titulo != grupo_atual:
                grupo_atual = titulo
                n = sum(1 for x in clientes if dia_curto(x.get("ultimo"))[0] == titulo)
                st.markdown(f'<div class="dia {cls}"><b>{titulo}</b><span>{n} cliente{"s" if n != 1 else ""}</span></div>',
                            unsafe_allow_html=True)
        cartao_slim(c, gestora)
    if len(clientes) > mostrar:
        if st.button(f"Mostrar mais {min(POR_PAGINA, len(clientes) - mostrar)} (de {len(clientes) - mostrar} restantes)",
                     use_container_width=True):
            st.session_state.fu_mostrar = mostrar + POR_PAGINA
            st.rerun()


def cartao_slim(c, gestora):
    f, cid = c["_f"], c["id"]
    stt = c["_status"] if c["_status"] in STATUS else "Por fazer"
    sit = c["_sit"]
    with st.container(border=True):
        partes = [f"agenda {ddmm(c.get('ultimo'))[:5]}" if c.get("ultimo") else "", _ocasiao(c)]
        if c.get("evento"):
            dias = (date.fromisoformat(c["evento"]) - date.today()).days
            partes.append(f"evento {ddmm(c['evento'])}" + (f" · <b>faltam {dias} dias</b>" if 0 <= dias <= 21 else ""))
        if c.get("vend_atend"):
            partes.append(f"<b>{c['vend_atend'].split()[0]}</b>")
        # linha de cima: cliente à esquerda, bolinhas de status à direita
        esq, dir_ = st.columns([3.3, 6.7], vertical_alignment="center")
        esq.markdown(f'<div class="cab"><span class="cli-nome">{c.get("nome") or ""}</span>'
                     f'<span class="pill" style="background:{COR_SIT.get(sit, "#555")}">{SIT_CURTA.get(sit, sit)}</span></div>'
                     f'<div class="cli-meta">{" · ".join(p for p in partes if p)}</div>', unsafe_allow_html=True)
        dir_.radio("Follow-up", STATUS, index=STATUS.index(stt), horizontal=True, label_visibility="collapsed",
                   key=f"s_{cid}", on_change=_salvar_card, args=(cid,))
        # linha de baixo: WhatsApp + anotação aberta + retorno (ou motivo, se não vai fechar)
        nao_vai = st.session_state.get(f"s_{cid}", stt) == "Não vai fechar"
        b, nota, ult = st.columns([1.3, 6.9, 1.8], vertical_alignment="center")
        if c.get("tel"):
            b.link_button("📲 WhatsApp", f"https://wa.me/55{c['tel']}", use_container_width=True)
        else:
            b.markdown('<span class="stamp">Sem telefone</span>', unsafe_allow_html=True)
        nota.text_input("Anotação", value=f.get("nota") or "", label_visibility="collapsed",
                        placeholder="📝 Anotação: ex.: pediu fotos de vestidos azuis, retornar sexta",
                        key=f"n_{cid}", on_change=_salvar_card, args=(cid,))
        if nao_vai:
            mot = f.get("motivo") or ""
            ult.selectbox("Motivo", MOTIVOS, index=MOTIVOS.index(mot) if mot in MOTIVOS else 0,
                          label_visibility="collapsed", format_func=lambda m: m or "Escolha o motivo",
                          key=f"m_{cid}", on_change=_salvar_card, args=(cid,))
        else:
            prox = date.fromisoformat(f["proximo"]) if f.get("proximo") else None
            with ult.popover(f"🔁 Retorno {prox:%d/%m}" if prox else "🔁 Retorno", use_container_width=True):
                st.date_input("Dia de falar com ela de novo", value=prox, format="DD/MM/YYYY",
                              key=f"p_{cid}", on_change=_salvar_card, args=(cid,))
        if nao_vai and not f.get("motivo"):
            st.markdown('<span class="falta">Falta o motivo: escolha ao lado da anotação.</span>', unsafe_allow_html=True)
        if c["_auto"]:
            st.markdown(f'<span class="stamp">Atualizado pela agenda em {ddmm((c.get("auto_em") or "")[:10])}</span>',
                        unsafe_allow_html=True)
        elif f.get("em"):
            st.markdown(f'<span class="stamp">Atualizado por {carimbo(f)}</span>', unsafe_allow_html=True)
ORDENS = ["Agenda mais recente", "Evento mais próximo"]
_MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _ocasiao(c):
    return (c.get("ocasiao") or c.get("grupo") or "").strip()


def _nome_mes(aaaa_mm):
    """'2026-12' -> 'Evento em dez/2026'"""
    return f"Evento em {_MESES[int(aaaa_mm[5:7]) - 1]}/{aaaa_mm[:4]}"


def _salvar_tabela():
    """Chamado quando alguém edita uma célula: grava a linha inteira e recarrega a tabela."""
    ed = st.session_state.get(f"tab_fu_{st.session_state.get('fu_ver', 0)}") or {}
    base = st.session_state.get("_fu_base") or []
    avisos = []
    for idx, mud in (ed.get("edited_rows") or {}).items():
        if idx >= len(base):
            continue
        linha = {**base[idx], **mud}
        status = linha.get("Follow-up") or "Por fazer"
        prox = linha.get("Próximo contato")
        if isinstance(prox, str) and prox:
            prox = date.fromisoformat(prox[:10])
        motivo = linha.get("Motivo") or ""
        try:
            salvar(linha["_id"], status, prox or None, motivo, linha.get("Anotação") or "")
        except Exception:
            avisos.append(f"Não consegui salvar {linha.get('Cliente')}. Tente de novo.")
            continue
        if status == "Não vai fechar" and not motivo:
            avisos.append(f"{linha.get('Cliente')}: escolha o Motivo na mesma linha.")
    st.session_state.fu_ver = st.session_state.get("fu_ver", 0) + 1
    st.session_state._fu_avisos = avisos or ["Salvo para toda a equipe."]


def tabela_followup(clientes, gestora):
    import pandas as pd
    for msg in st.session_state.pop("_fu_avisos", []):
        st.toast(msg)
    base = []
    for c in clientes:
        f = c["_f"]
        tel = c.get("tel") or ""
        linha = {"_id": c["id"], "Agenda": ddmm(c.get("ultimo"))[:5], "Cliente": c.get("nome") or "",
                 "Ocasião": _ocasiao(c), "Evento": ddmm(c.get("evento")),
                 "Situação": {"Veio e não fechou": "Não fechou", "Veio, conferir se fechou": "Conferir"}.get(c["_sit"], c["_sit"])}
        if gestora:
            linha["Vendedora"] = (c.get("vend_atend") or "").split(" ")[0]
        linha.update({"Follow-up": c["_status"] if c["_status"] in STATUS else "Por fazer",
                      "Próximo contato": date.fromisoformat(f["proximo"]) if f.get("proximo") else None,
                      "Motivo": f.get("motivo") or "", "Anotação": f.get("nota") or "",
                      "WhatsApp": f"https://wa.me/55{tel}" if tel else None})
        base.append(linha)
    st.session_state._fu_base = base
    if not base:
        st.info("Nenhuma cliente com esses filtros.")
        return
    df = pd.DataFrame(base)
    travadas = ["Agenda", "Cliente", "Ocasião", "Evento", "Situação", "Vendedora", "WhatsApp"]
    st.data_editor(
        df, key=f"tab_fu_{st.session_state.get('fu_ver', 0)}", on_change=_salvar_tabela,
        hide_index=True, use_container_width=True, num_rows="fixed",
        height=min(36 * (len(base) + 1) + 4, 720),
        disabled=[c for c in travadas if c in df.columns],
        column_order=[c for c in ["Agenda", "Cliente", "WhatsApp", "Ocasião", "Evento", "Situação", "Vendedora",
                                  "Follow-up", "Próximo contato", "Motivo", "Anotação"] if c in df.columns],
        column_config={
            "Agenda": st.column_config.TextColumn("Agenda", width="small", help="Dia em que a cliente estava na agenda"),
            "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
            "Ocasião": st.column_config.TextColumn("Ocasião", width="small"),
            "Evento": st.column_config.TextColumn("Evento", width="small"),
            "Situação": st.column_config.TextColumn("Situação", width="small"),
            "Vendedora": st.column_config.TextColumn("Vendedora", width="small"),
            "Follow-up": st.column_config.SelectboxColumn("Follow-up", options=STATUS, required=True, width="medium"),
            "Próximo contato": st.column_config.DateColumn("Retorno", format="DD/MM", width="small",
                                                           help="Dia em que vai falar com a cliente de novo"),
            "Motivo": st.column_config.SelectboxColumn("Motivo", options=[""] + list(MOTIVOS), width="medium",
                                                        help="Só quando a cliente não vai fechar"),
            "Anotação": st.column_config.TextColumn("Anotação", width="medium"),
            "WhatsApp": st.column_config.LinkColumn("Chamar", display_text="WhatsApp", width="small"),
        },
    )

def resumo_semana(lista, semana_ini):
    """Resumo da Tamires: o que cada vendedora atendeu na semana e quanto já teve follow-up."""
    st.markdown(f"**Resumo da semana por vendedora** · atendimentos de {ddmm(semana_ini)} até hoje")
    cols = ["Atendidas", "Follow-up feito", "Pendentes", "% feito", "Fecharam", "Retorno vencido"]
    linhas, tot = [], {k: 0 for k in cols}
    for v in EQUIPE_VENDAS:
        todas = [c for c in lista if c.get("vend_atend") == v]
        sem = [c for c in todas if (c.get("ultimo") or "") >= semana_ini]
        feito = sum(1 for c in sem if c["_status"] != "Por fazer")
        cont = {"Atendidas": len(sem), "Follow-up feito": feito, "Pendentes": len(sem) - feito,
                "Fecharam": sum(1 for c in sem if c["_status"] == "Fechou"),
                "Retorno vencido": sum(1 for c in todas if c["_vencido"])}
        for k in cont: tot[k] += cont[k]
        cont["% feito"] = f"{round(100 * feito / len(sem))}%" if sem else "–"
        linhas.append((v.split()[0], cont))
    tot["% feito"] = f"{round(100 * tot['Follow-up feito'] / tot['Atendidas'])}%" if tot["Atendidas"] else "–"
    linhas.append(("Total", tot))
    tabela_resumo(linhas, cols, alerta=("Pendentes", "Retorno vencido"))
    st.caption("Follow-up feito = qualquer status diferente de \"Por fazer\". "
               "Retorno vencido = tinha próximo contato marcado para uma data que já passou e a cliente não fechou nem desistiu.")

    antigas = sum(1 for c in lista if (c.get("ultimo") or "") < semana_ini and c["_status"] == "Por fazer")
    if antigas:
        st.caption(f"📦 **Fila antiga:** {antigas} clientes de antes de {ddmm(semana_ini)} ainda sem follow-up. "
                   "Para ver, escolha Período → Fila antiga.")

    # último acesso de cada uma
    try:
        acessos = cliente_supabase().rpc("acessos_equipe").execute().data or []
    except Exception:
        acessos = []
    partes = []
    for a in acessos:
        if a.get("papel") != "vendedora":
            continue
        u = a.get("ultimo_acesso")
        if not u:
            partes.append(f"**{a['nome'].split()[0]}**: nunca entrou")
            continue
        quando = datetime.fromisoformat(u.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Sao_Paulo"))
        dif = (hoje_local() - quando.date()).days
        dia = "hoje" if dif == 0 else "ontem" if dif == 1 else f"{quando:%d/%m}"
        partes.append(f"**{a['nome'].split()[0]}**: {dia} às {quando:%H:%M}")
    if partes:
        st.caption("👤 Último acesso ao app · " + " · ".join(partes))


def cartao(c):
    f = c["_f"]
    with st.container(border=True):
        dias = None
        if c.get("evento"):
            dias = (date.fromisoformat(c["evento"]) - date.today()).days
        prazo = f" (em {dias} dias)" if dias and dias > 0 else " (hoje)" if dias == 0 else ""
        cor = COR_SIT.get(c["_sit"], "#555")
        # linha 1: nome + situação
        cab = (f'<div class="cab"><span class="cli-nome">{c.get("nome") or ""}</span>'
               f'<span class="pill" style="background:{cor}">{c["_sit"]}</span>'
               + ('<span class="pill" style="background:#6e2a4f">evento próximo</span>' if dias is not None and dias <= 21 else "")
               + '</div>')
        # linha 2: dados + WhatsApp
        partes = [c.get("ocasiao") or c.get("grupo") or "", f"evento {ddmm(c.get('evento'))}{prazo}"]
        if c["_vend"]:
            partes.append(c["_vend"])
        if c.get("confirmou"):
            partes.append("✅")
        if c.get("proxima"):
            partes.append(f"<b>prova {ddmm(c['proxima'])}</b>")
        if c.get("tel"):
            partes.append(fone_html(c["tel"]))
        auto = f'<div class="auto">📅 {c["auto_texto"]}</div>' if c.get("auto_texto") else ""
        st.markdown(f'{cab}<div class="cli-meta">{" · ".join(p for p in partes if p)}</div>{auto}<div style="height:8px"></div>', unsafe_allow_html=True)

        # linha 3: follow-up + próximo contato + salvar
        with st.form(f"f_{c['id']}", border=False):
            a, b, s = st.columns([4, 4, 2.4], vertical_alignment="bottom")
            status = a.selectbox("Follow-up", STATUS, index=STATUS.index(c["_status"]) if c["_status"] in STATUS else 0, key=f"s_{c['id']}")
            prox_val = date.fromisoformat(f["proximo"]) if f.get("proximo") else None
            proximo = b.date_input("Próximo contato", value=prox_val, format="DD/MM/YYYY", key=f"p_{c['id']}")
            enviar = s.form_submit_button("Salvar", use_container_width=True)
            nota_atual = f.get("nota") or ""
            rotulo = f"📝 {nota_atual[:45]}{'…' if len(nota_atual) > 45 else ''}" if nota_atual else "＋ Anotação / motivo"
            with st.expander(rotulo):
                nota = st.text_input("Anotação", value=nota_atual,
                                     placeholder="Ex.: pediu fotos de vestidos azuis, retornar sexta", key=f"n_{c['id']}")
                motivo = st.selectbox("Motivo (só se não vai fechar)", MOTIVOS,
                                      index=MOTIVOS.index(f.get("motivo") or "") if (f.get("motivo") or "") in MOTIVOS else 0,
                                      key=f"m_{c['id']}")
            if enviar:
                if status == "Não vai fechar" and not motivo:
                    st.error("Abra o ＋ Anotação e escolha o motivo antes de salvar.")
                else:
                    salvar(c["id"], status, proximo, motivo, nota)
                    st.success("Salvo para toda a equipe.")
                    st.rerun()
        if c["_auto"]:
            st.markdown(f'<span class="stamp">Atualizado pela agenda em {ddmm((c.get("auto_em") or "")[:10])}</span>', unsafe_allow_html=True)
        elif f.get("em"):
            st.markdown(f'<span class="stamp">Atualizado por {f.get("por") or "alguém da equipe"} em {ddmm(f["em"][:10])}</span>',
                        unsafe_allow_html=True)


# ---------- confirmar agendamentos ----------
# Mensagens de confirmação. Para mudar o texto, edite aqui.
# {saudacao} {vendedora} {frase} {quando} {hora} são preenchidos sozinhos.
MSG = ("{saudacao} Tudo bem? Aqui é a {vendedora}, da DRESS ME UP.\n\n"
       "Passando para lembrar que {frase} para {quando}, às {hora}. Posso confirmar?\n\n"
       "{salto}\n\n"
       "Se precisar trocar o horário, é só me avisar por aqui. 💛")
FRASE = {"Primeiro": "seu horário para provar os vestidos está marcado",
         "Retorno": "sua prova está marcada",
         "Troca": "seu horário para trocar o vestido está marcado"}
SALTO = {"Primeiro": "Traga o salto que você vai usar na festa, tá? Ele muda o caimento e o comprimento do vestido, "
                     "e é essencial nas duas provas.",
         "Retorno": "Não esquece o salto que você vai usar na festa, tá? É com ele que a gente acerta o comprimento.",
         "Troca": "Traga o salto que você vai usar na festa, tá? Assim a gente já confere o comprimento do novo vestido."}
TIPO_ROTULO = {"Primeiro": "1º atendimento", "Retorno": "Prova/retorno", "Troca": "Troca"}
CONF = ["A confirmar", "Mensagem enviada", "Confirmou", "Vai remarcar", "Não respondeu"]
COR_CONF = {"A confirmar": "#8a8590", "Mensagem enviada": "#2f5f9e", "Confirmou": "#1a7f4b", "Vai remarcar": "#b5761b", "Não respondeu": "#8a2f3b"}
NAO_E_NOME = {"filha", "mae", "mãe", "irma", "irmã", "amiga", "prima", "sobrinha", "cliente"}


def hoje_local():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).date()


def quando_txt(d):
    dif = (d - hoje_local()).days
    base = f"{SEMANA[d.weekday()]} ({d:%d/%m})"
    return "hoje" if dif == 0 else f"amanhã, {base}" if dif == 1 else base


def hora_txt(h):
    hh, mm = (h or "00:00").split(":")[:2]
    return f"{int(hh)}h" + ("" if mm == "00" else mm)


def mensagem(a, vendedora):
    primeiro = (a.get("nome") or "").split()[0] if a.get("nome") else ""
    saudacao = "Oi!" if not primeiro or primeiro.lower() in NAO_E_NOME else f"Oi, {primeiro}!"
    tipo = a.get("tipo") if a.get("tipo") in FRASE else "Primeiro"
    return MSG.format(saudacao=saudacao, vendedora=vendedora or "equipe", frase=FRASE[tipo],
                      quando=quando_txt(date.fromisoformat(a["dia"])), hora=hora_txt(a.get("hora")), salto=SALTO[tipo])


def link_whats(tel, texto):
    return f"https://wa.me/55{tel}?text={quote(texto)}"


def carimbo(c):
    """'natalya', '2026-11-27T21:40:00+00:00' -> 'Natalya, 27/11 às 18h40'"""
    quem = (c.get("por") or "alguém da equipe").split("@")[0].capitalize()
    try:
        em = datetime.fromisoformat(c["em"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Sao_Paulo"))
        return f"{quem}, {em:%d/%m} às {em.hour}h{em:%M}"
    except Exception:
        return quem


def salvar_conf(agenda_id):
    novo = st.session_state.get(f"c_{agenda_id}")
    if not novo:
        return
    try:
        if novo == "A confirmar":  # desfaz uma marcação feita por engano
            cliente_supabase().table("confirmacoes").delete().eq("agenda_id", agenda_id).execute()
            st.toast("Marcação desfeita: voltou para A confirmar")
            return
        cliente_supabase().table("confirmacoes").upsert({
            "agenda_id": agenda_id, "status": novo, "por": st.session_state.get("user_email"),
            "em": datetime.now(timezone.utc).isoformat()}).execute()
        st.toast(f"Salvo: {novo}")
    except Exception:
        st.toast("Não consegui salvar. Tente de novo.")


def tela_confirmar(nome, gestora):
    sb = cliente_supabase()
    hoje = hoje_local()
    try:
        ag = sb.table("agenda").select("*").gte("dia", hoje.isoformat()).order("dia").order("hora").execute().data or []
        confs = {c["agenda_id"]: c for c in (sb.table("confirmacoes").select("*").execute().data or [])}
    except Exception:
        st.warning("Não consegui carregar a agenda. Atualize a página.")
        return
    if not ag:
        st.info("Nenhum agendamento nos próximos dias. A lista vem sozinha da agenda da loja.")
        return

    dias = sorted({a["dia"] for a in ag})
    padrao = next((i for i, d in enumerate(dias) if d > hoje.isoformat()), 0)

    def rot(d):
        dd = date.fromisoformat(d)
        dif = (dd - hoje).days
        pre = "Hoje" if dif == 0 else "Amanhã" if dif == 1 else SEMANA[dd.weekday()].capitalize()
        return f"{pre} · {dd:%d/%m}"

    c1, c2 = st.columns(2)
    dia = c1.selectbox("Dia", dias, index=padrao, format_func=rot)
    vend = c2.selectbox("Vendedora", ["Todas"] + EQUIPE_VENDAS)
    lista = [a for a in ag if a["dia"] == dia and (vend == "Todas" or a.get("vend_atend") == vend)]

    def status(a):
        c = confs.get(a["id"])
        if c: return c["status"]
        return "Confirmou" if a.get("confirmou_agenda") else "A confirmar"

    if gestora:
        do_dia = [a for a in ag if a["dia"] == dia]
        linhas = []
        for v in EQUIPE_VENDAS:
            g = [a for a in do_dia if a.get("vend_atend") == v]
            cont = {c: sum(1 for a in g if status(a) == c) for c in CONF}
            cont["Total"] = len(g)
            linhas.append((v.split()[0], cont))
        linhas.append(("Total", {k: sum(l[1][k] for l in linhas) for k in CONF + ["Total"]}))
        st.markdown(f"**Confirmações por vendedora · {rot(dia)}**")
        tabela_resumo(linhas, CONF + ["Total"], alerta=("A confirmar", "Não respondeu"))

    n_ok = sum(1 for a in lista if status(a) == "Confirmou")
    n_env = sum(1 for a in lista if status(a) == "Mensagem enviada")
    falta = sum(1 for a in lista if status(a) == "A confirmar")
    st.markdown(f'<div class="dia hoje"><b>{rot(dia)}</b><span>{len(lista)} agendamento{"s" if len(lista) != 1 else ""} · '
                f'{falta} sem mensagem · {n_env} aguardando resposta · '
                f'{n_ok} confirmada{"s" if n_ok != 1 else ""}</span></div>', unsafe_allow_html=True)
    if not lista:
        st.info("Nenhum agendamento neste dia com esse filtro.")
        return
    st.caption("Toque em **Enviar no WhatsApp** e envie → marque **Mensagem enviada** (as outras veem e ninguém "
               "manda duas vezes) → quando a cliente responder, marque Confirmou, Vai remarcar ou Não respondeu.")

    for a in lista:
        stt = status(a)
        c = confs.get(a["id"])
        with st.container(border=True):
            partes = [TIPO_ROTULO.get(a.get("tipo"), "")]
            if a.get("ocasiao"): partes.append(a["ocasiao"])
            if a.get("evento"): partes.append(f"evento {ddmm(a['evento'])}")
            if a.get("vend_atend"): partes.append(f"<b>{a['vend_atend'].split()[0]}</b>")
            st.markdown(f'<div class="cab"><span class="hora">{hora_txt(a.get("hora"))}</span>'
                        f'<span class="cli-nome nc">{a.get("nome") or ""}</span>'
                        f'<span class="pill" style="background:{COR_CONF[stt]}">{stt}</span></div>'
                        f'<div class="cli-meta" style="padding-bottom:10px">{" · ".join(p for p in partes if p)}</div>', unsafe_allow_html=True)
            b, r = st.columns([2, 5], vertical_alignment="center")
            if a.get("tel") and stt == "A confirmar":
                b.link_button("📲 Enviar no WhatsApp", link_whats(a["tel"], mensagem(a, nome)), use_container_width=True)
            elif a.get("tel"):
                b.link_button("Já enviada · abrir conversa" if stt in ("Mensagem enviada", "Não respondeu") else "Abrir conversa", f"https://wa.me/55{a['tel']}", use_container_width=True,
                              help="A mensagem já foi enviada. Isto só abre a conversa, sem texto pronto.")
            else:
                b.markdown('<span class="stamp">Sem telefone na agenda</span>', unsafe_allow_html=True)
            r.radio("Resposta", CONF, index=CONF.index(stt), horizontal=True, label_visibility="collapsed",
                    key=f"c_{a['id']}", on_change=salvar_conf, args=(a["id"],))
            if c and c.get("status") == "Mensagem enviada":
                st.markdown(f'<span class="enviada">✉️ Mensagem enviada por {carimbo(c)}. Não envie de novo.</span>',
                            unsafe_allow_html=True)
            elif c:
                st.markdown(f'<span class="stamp">Marcado por {carimbo(c)}</span>', unsafe_allow_html=True)
            elif a.get("confirmou_agenda"):
                st.markdown('<span class="stamp">✅ já estava confirmada na agenda</span>', unsafe_allow_html=True)


@st.fragment(run_every=30)
def vigia_inatividade():
    """Confere a cada 30 s se a tela está parada há mais tempo que o limite e, se estiver, sai."""
    if time.time() - st.session_state.get("ultima_atividade", time.time()) > INATIVIDADE_MIN * 60:
        st.session_state.msg_saida = True
        sair()


if st.session_state.get("user_email"):
    agora = time.time()
    if agora - st.session_state.get("ultima_atividade", agora) > INATIVIDADE_MIN * 60:
        st.session_state.msg_saida = True
        sair()
    st.session_state.ultima_atividade = agora
    vigia_inatividade()
    tela_lista()
else:
    tela_login()
