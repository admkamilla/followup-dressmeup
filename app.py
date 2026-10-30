"""FOLLOW UP - DRESS ME UP GOIANIA

App da equipe de vendas: lista de clientes para follow-up, atualizada com a agenda da loja.
Não mostra valores, pedidos ou faturamento.
"""
from datetime import date, datetime, timezone
from html import escape
import re
import unicodedata

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="FOLLOW UP - DRESS ME UP GOIANIA", page_icon="📋", layout="centered")

STATUS = ["Por fazer", "Tentei, sem resposta", "Em conversa", "Reagendou", "Fechou", "Não vai fechar"]
MOTIVOS = ["", "Preço", "Alugou em outro lugar", "Não encontrou o vestido", "Desistiu do evento", "Comprou vestido", "Outro"]
SITUACAO = {"Não compareceu": "Faltou", "Atendida, não fechou": "Veio e não fechou", "Em aberto": "Veio, conferir se fechou"}
COR_SIT = {"Faltou": "#8a2f3b", "Veio e não fechou": "#9a5a2b", "Veio, conferir se fechou": "#2d3f5f"}
VENDEDORAS = ["Todas", "Natalya", "Raquel", "Jéssica Martins", "Sem vendedora"]
POR_PAGINA = 25


def _ate(dias):
    return lambda ev: bool(ev) and 0 <= (date.fromisoformat(ev) - date.today()).days <= dias


MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def tipo_evento(c):
    """Tipo de evento a partir da ocasião que a cliente informou."""
    o = unicodedata.normalize("NFKD", (c.get("ocasiao") or "")).encode("ascii", "ignore").decode().lower()
    if not o.strip(): return "Não informado"
    if re.search(r"\bmae\b|\bpai\b|\bavo\b|madrasta|sogra", o): return "Mãe/família"
    if "madrinha" in o: return "Madrinha"
    if "meio med" in o or "1/2 med" in o: return "Meio médico"
    if re.search(r"forma[nt]|baile|gala", o): return "Formatura"
    if re.search(r"noiv|casam", o): return "Casamento/convidada"
    if re.search(r"15|debut", o): return "15 anos"
    return "Outro"


def periodos(lista):
    """Opções do filtro de data: atalhos + cada mês que tem evento na lista (ex.: julho de 2027)."""
    op = {
        "Qualquer data": lambda ev: True,
        "Nos próximos 7 dias": _ate(7),
        "Nos próximos 15 dias": _ate(15),
        "Nos próximos 30 dias": _ate(30),
        "Nos próximos 60 dias": _ate(60),
    }
    for ym in sorted({c["evento"][:7] for c in lista if c.get("evento")}):
        op[f"{MESES[int(ym[5:7]) - 1]} de {ym[:4]}"] = lambda ev, ym=ym: bool(ev) and ev[:7] == ym
    op["Sem data informada"] = lambda ev: not ev
    return op
DOMINIO = "followup.dressmeup.com.br"  # e-mail interno: usuario@DOMINIO (não recebe mensagens)

st.markdown("""
<style>
.block-container{max-width:860px;padding-top:1.5rem}
.cli-nome{font-size:1.05rem;font-weight:600;margin:0}
.cli-meta{color:#6b6570;font-size:.85rem;margin:2px 0}
.pill{display:inline-block;font-size:.75rem;font-weight:600;border-radius:999px;padding:2px 10px;color:#fff;margin-right:6px}
.auto{color:#6e2a4f;font-size:.85rem;margin:4px 0}
.stamp{color:#8a8590;font-size:.75rem}
.dia{display:flex;justify-content:space-between;align-items:baseline;gap:8px;background:#2b2a2e;color:#fff;
 border-radius:10px;padding:10px 14px;margin:22px 0 8px}
.dia b{font-size:1.05rem}.dia span{font-size:.8rem;opacity:.8}
.dia.hoje{background:#6e2a4f}.dia.sem{background:#6b6570}
/* barra padrão do Streamlit escondida: ela cobria o botão Sair */
header[data-testid="stHeader"]{display:none}
.block-container{padding-top:2rem}
/* contadores em cartões com sombra (3 por linha, também no celular) */
.conts{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:6px 0 16px}
.cont{background:#fff;border-radius:12px;padding:10px 14px;
 box-shadow:0 1px 2px rgba(43,42,46,.06),0 4px 14px rgba(43,42,46,.08)}
.cont span{display:block;font-size:.78rem;color:#6b6570;line-height:1.2}
.cont b{display:block;font-size:1.9rem;font-weight:600;color:#2b2a2e;line-height:1.2;margin-top:4px;
 text-shadow:0 2px 4px rgba(110,42,79,.18)}
@media (max-width:640px){.cont{padding:8px 10px}.cont b{font-size:1.5rem}.cont span{font-size:.72rem}}
/* cartão de cada cliente mais compacto */
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"]{gap:.35rem}
[data-testid="stForm"] [data-testid="stWidgetLabel"] p{font-size:.78rem;color:#6b6570}
[data-testid="stForm"] [data-testid="stVerticalBlock"]{gap:.4rem}
[data-testid="stForm"] textarea{height:52px!important;min-height:52px!important;padding-top:.5rem}
.cli-topo{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.cli-topo .pills{display:flex;flex-wrap:wrap;justify-content:flex-end;gap:4px}
.cli-topo .pill{margin:0;white-space:nowrap}
.cli-info{display:grid;grid-template-columns:max-content 1fr;column-gap:10px;row-gap:3px;margin:8px 0 4px;
 font-size:.9rem;line-height:1.35}
.cli-info .r{color:#6b6570}.cli-info .v{color:#2b2a2e}
.cli-info a{color:#6e2a4f;font-weight:600}
.cli-meta{margin:4px 0 10px}
</style>
""", unsafe_allow_html=True)


# ---------- conexão e login ----------
def cliente_supabase():
    if "sb" not in st.session_state:
        st.session_state.sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return st.session_state.sb


def tela_login():
    st.title("Follow up · Dress Me Up Goiânia")
    st.caption("Entre com o usuário e a senha que a Kami cadastrou para você.")
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
    for k in ("sb", "user_email", "nome_vendedora", "gestora"):
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


def fone_link(t):
    if not t:
        return ""
    vis = f"({t[:2]}) {t[2:-4]}-{t[-4:]}" if len(t) >= 10 else t
    return f'<a href="https://wa.me/55{t}" target="_blank">{vis}</a>'


def fone(t):
    if not t:
        return ""
    vis = f"({t[:2]}) {t[2:-4]}-{t[-4:]}" if len(t) >= 10 else t
    return f"[WhatsApp {vis}](https://wa.me/55{t})"


# ---------- tela principal ----------
def tela_lista():
    topo, botao = st.columns([5, 1], vertical_alignment="center")
    topo.title("Follow up · Dress Me Up Goiânia")
    if botao.button("Sair"):
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
    st.caption((f"Olá, {nome}! Você vê as clientes de toda a equipe, " if gestora else
                f"Olá, {nome}! Estas são as suas clientes (pela cor da agenda) " if nome else "Clientes ")
               + "que faltaram ou vieram e ainda não fecharam, com evento por vir. "
               "Separadas pelo dia em que estavam na agenda, das mais recentes para as mais antigas. "
               "A lista se atualiza sozinha com a agenda.")

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
        c["_tipo"] = tipo_evento(c)
        lista.append(c)

    if not lista:
        st.info("A lista está vazia. Ela é preenchida automaticamente com a agenda da loja.")
        return

    # contadores
    cont = {s: sum(1 for c in lista if c["_status"] == s) for s in STATUS}
    st.markdown('<div class="conts">' + "".join(f'<div class="cont"><span>{s}</span><b>{cont[s]}</b></div>' for s in STATUS)
                + "</div>", unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    filtro_status = f1.selectbox("Follow-up", ["Todos"] + STATUS, index=1)
    filtro_sit = f2.selectbox("Situação", ["Todas"] + list(SITUACAO.values()))
    f3, f4 = st.columns(2)
    tipos = sorted({c["_tipo"] for c in lista}, key=lambda g: (g in ("Outro", "Não informado"), g))
    filtro_tipo = f3.selectbox("Tipo de evento", ["Todos"] + tipos)
    per = periodos(lista)
    filtro_data = f4.selectbox("Data do evento", list(per))
    filtro_vend = st.selectbox("Vendedora", ["Todas", "Natalya", "Raquel", "Jéssica Martins"]) if gestora else "Todas"
    busca = st.text_input("Buscar nome ou telefone").strip().lower()

    def passa(c):
        if filtro_status != "Todos" and c["_status"] != filtro_status: return False
        if filtro_sit != "Todas" and c["_sit"] != filtro_sit: return False
        if filtro_vend != "Todas" and c.get("vend_atend") != filtro_vend: return False
        if filtro_tipo != "Todos" and c["_tipo"] != filtro_tipo: return False
        if not per[filtro_data](c.get("evento")): return False
        if busca:
            dig = "".join(ch for ch in busca if ch.isdigit())
            if busca not in (c.get("nome") or "").lower() and not (dig and dig in (c.get("tel") or "")): return False
        return True

    # mais recente primeiro: quem esteve na agenda por último é quem pede retorno antes
    filtrada = sorted(filter(passa, lista), key=lambda c: (c.get("ultimo") or "", c.get("nome") or ""), reverse=True)
    st.caption(f"{len(filtrada)} clientes nesta lista")
    pag = st.session_state.get("pag", 1)
    por_dia = {}
    for c in filtrada:
        por_dia[c.get("ultimo")] = por_dia.get(c.get("ultimo"), 0) + 1
    atual = object()
    for c in filtrada[: pag * POR_PAGINA]:
        if c.get("ultimo") != atual:
            atual = c.get("ultimo")
            txt, cls = titulo_dia(atual)
            n = por_dia[atual]
            st.markdown(f'<div class="dia {cls}"><b>{txt}</b><span>{n} cliente{"s" if n > 1 else ""}</span></div>',
                        unsafe_allow_html=True)
        cartao(c)
    if len(filtrada) > pag * POR_PAGINA and st.button("Mostrar mais"):
        st.session_state.pag = pag + 1
        st.rerun()


def cartao(c):
    f = c["_f"]
    with st.container(border=True):
        dias = None
        if c.get("evento"):
            dias = (date.fromisoformat(c["evento"]) - date.today()).days
        prazo = f" (em {dias} dias)" if dias and dias > 0 else " (hoje)" if dias == 0 else ""
        cor_sit = COR_SIT.get(c["_sit"], "#555")
        pills = f'<span class="pill" style="background:{cor_sit}">{c["_sit"]}</span>'
        if dias is not None and dias <= 21:
            pills += '<span class="pill" style="background:#6e2a4f">evento próximo</span>'
        txt = lambda v: escape((v or "").strip()) or "—"
        evento = txt(c.get("ocasiao") or c.get("grupo")) + (f' · {ddmm(c["evento"])}{prazo}' if c.get("evento") else "")
        whats = fone_link(c.get("tel")) or "—"
        extra = (f'atendimento {ddmm(c.get("ultimo"))}{" · " + escape(c["_vend"]) if c["_vend"] else ""}'
                 f'{" · ✅ tinha confirmado" if c.get("confirmou") else ""}'
                 f'{" · <b>próxima prova " + ddmm(c["proxima"]) + "</b>" if c.get("proxima") else ""}')
        st.markdown(f'<div class="cli-topo"><p class="cli-nome">{txt(c.get("nome"))}</p><div class="pills">{pills}</div></div>'
                    f'<div class="cli-info"><span class="r">Tamanho:</span><span class="v">{txt(c.get("tamanho"))}</span>'
                    f'<span class="r">Cor:</span><span class="v">{txt(c.get("cor"))}</span>'
                    f'<span class="r">Evento:</span><span class="v">{evento}</span>'
                    f'<span class="r">WhatsApp:</span><span class="v">{whats}</span></div>'
                    f'<p class="cli-meta">{extra}</p>', unsafe_allow_html=True)
        if c.get("auto_texto"):
            st.markdown(f'<p class="auto">📅 {c["auto_texto"]}</p>', unsafe_allow_html=True)

        with st.form(f"f_{c['id']}", border=False):
            a, b, m = st.columns(3)
            status = a.selectbox("Follow-up", STATUS, index=STATUS.index(c["_status"]) if c["_status"] in STATUS else 0, key=f"s_{c['id']}")
            prox_val = date.fromisoformat(f["proximo"]) if f.get("proximo") else None
            proximo = b.date_input("Próximo contato", value=prox_val, format="DD/MM/YYYY", key=f"p_{c['id']}")
            motivo = m.selectbox("Motivo (se não fechar)", MOTIVOS,
                                 index=MOTIVOS.index(f.get("motivo") or "") if (f.get("motivo") or "") in MOTIVOS else 0,
                                 key=f"m_{c['id']}")
            n_col, s_col = st.columns([5, 1], vertical_alignment="bottom")
            nota = n_col.text_area("Anotação", value=f.get("nota") or "", height=68,
                                   placeholder="Ex.: pediu fotos de vestidos azuis, retornar sexta", key=f"n_{c['id']}")
            if s_col.form_submit_button("Salvar", use_container_width=True):
                if status == "Não vai fechar" and not motivo:
                    st.error("Escolha o motivo antes de salvar.")
                else:
                    salvar(c["id"], status, proximo, motivo, nota)
                    st.success("Salvo para toda a equipe.")
                    st.rerun()
        if c["_auto"]:
            st.markdown(f'<span class="stamp">Atualizado pela agenda em {ddmm((c.get("auto_em") or "")[:10])}</span>', unsafe_allow_html=True)
        elif f.get("em"):
            st.markdown(f'<span class="stamp">Atualizado por {f.get("por") or "alguém da equipe"} em {ddmm(f["em"][:10])}</span>',
                        unsafe_allow_html=True)


if st.session_state.get("user_email"):
    tela_lista()
else:
    tela_login()
