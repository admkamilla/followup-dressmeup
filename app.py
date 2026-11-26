"""FOLLOW UP - DRESS ME UP GOIANIA

App da equipe de vendas: lista de clientes para follow-up, atualizada com a agenda da loja.
Não mostra valores, pedidos ou faturamento.
"""
import time
from datetime import date, datetime, timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

st.set_page_config(page_title="FOLLOW UP - DRESS ME UP GOIANIA", page_icon="📋", layout="centered")

STATUS = ["Por fazer", "Tentei, sem resposta", "Em conversa", "Reagendou", "Fechou", "Não vai fechar"]
MOTIVOS = ["", "Preço", "Alugou em outro lugar", "Não encontrou o vestido", "Desistiu do evento", "Comprou vestido", "Outro"]
SITUACAO = {"Não compareceu": "Faltou", "Atendida, não fechou": "Veio e não fechou", "Em aberto": "Veio, conferir se fechou"}
COR_SIT = {"Faltou": "#8a2f3b", "Veio e não fechou": "#9a5a2b", "Veio, conferir se fechou": "#2d3f5f"}
VENDEDORAS = ["Todas", "Natalya", "Raquel", "Jéssica Martins", "Sem vendedora"]
POR_PAGINA = 25
INATIVIDADE_MIN = 5  # desconecta depois de 5 minutos sem uso
DOMINIO = "followup.dressmeup.com.br"  # e-mail interno: usuario@DOMINIO (não recebe mensagens)

st.markdown("""
<style>
.block-container{max-width:860px;padding-top:1.5rem}
.cab{display:flex;flex-wrap:wrap;align-items:center;gap:6px;line-height:1.6;padding-bottom:2px}
.cli-nome{font-size:.98rem;font-weight:600;margin:0;text-transform:capitalize}
.cli-meta{color:#6b6570;font-size:.8rem;margin:0;line-height:1.45}
.cli-meta a{color:#1a7f4b;font-weight:600;text-decoration:none}
.pill{display:inline-block;font-size:.68rem;font-weight:600;border-radius:999px;padding:1px 8px;color:#fff}
.auto{color:#6e2a4f;font-size:.78rem;margin:0}
.stamp{color:#8a8590;font-size:.7rem}
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
    st.title("Follow up · Dress Me Up Goiânia")
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


# ---------- tela principal ----------
def tela_lista():
    topo, botao = st.columns([5, 1])
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
    aba = st.radio("Tela", ["📲 Confirmar agendamentos", "📋 Follow-up"], horizontal=True,
                   label_visibility="collapsed", key="aba")
    if aba.startswith("📲"):
        tela_confirmar(nome, gestora)
    else:
        tela_followup(nome, gestora)


def tela_followup(nome, gestora):
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
        lista.append(c)

    if not lista:
        st.info("A lista está vazia. Ela é preenchida automaticamente com a agenda da loja.")
        return

    # retorno vencido: tinha próximo contato marcado para antes de hoje e não foi resolvida
    for c in lista:
        prox = c["_f"].get("proximo")
        c["_vencido"] = bool(prox and prox < hoje and c["_status"] not in ("Fechou", "Não vai fechar"))

    if gestora:
        st.markdown("**Resumo por vendedora**")
        cols_r = STATUS + ["Retorno vencido", "Total"]
        linhas = []
        for v in ["Natalya", "Raquel", "Jéssica Martins", ""]:
            grupo = [c for c in lista if (c.get("vend_atend") or "") == v]
            if not grupo and not v:
                continue
            cont = {s: sum(1 for c in grupo if c["_status"] == s) for s in STATUS}
            cont["Retorno vencido"] = sum(1 for c in grupo if c["_vencido"])
            cont["Total"] = len(grupo)
            linhas.append((v.split()[0] if v else "Sem vendedora", cont))
        tot = {k: sum(l[1][k] for l in linhas) for k in cols_r}
        linhas.append(("Total", tot))
        tabela_resumo(linhas, cols_r, alerta=("Por fazer", "Retorno vencido"))
        st.caption("Retorno vencido = a vendedora marcou um próximo contato que já passou e a cliente ainda não fechou nem desistiu.")
    else:
        cont = {s: sum(1 for c in lista if c["_status"] == s) for s in STATUS}
        cols = st.columns(3)
        for i, s in enumerate(STATUS):
            cols[i % 3].metric(s, cont[s])

    f1, f2 = st.columns(2)
    filtro_status = f1.selectbox("Follow-up", ["Todos"] + STATUS + ["Retorno vencido"], index=1)
    filtro_sit = f2.selectbox("Situação", ["Todas"] + list(SITUACAO.values()))
    filtro_vend = st.selectbox("Vendedora", ["Todas", "Natalya", "Raquel", "Jéssica Martins"]) if gestora else "Todas"
    busca = st.text_input("Buscar nome ou telefone").strip().lower()

    def passa(c):
        if filtro_status == "Retorno vencido":
            if not c["_vencido"]: return False
        elif filtro_status != "Todos" and c["_status"] != filtro_status: return False
        if filtro_sit != "Todas" and c["_sit"] != filtro_sit: return False
        if filtro_vend != "Todas" and c.get("vend_atend") != filtro_vend: return False
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
CONF = ["A confirmar", "Confirmou", "Vai remarcar", "Não respondeu"]
COR_CONF = {"A confirmar": "#8a8590", "Confirmou": "#1a7f4b", "Vai remarcar": "#b5761b", "Não respondeu": "#8a2f3b"}
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


def salvar_conf(agenda_id):
    novo = st.session_state.get(f"c_{agenda_id}")
    if not novo or novo == "A confirmar":
        return
    try:
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
    vend = c2.selectbox("Vendedora", ["Todas", "Natalya", "Raquel", "Jéssica Martins"]) if gestora else "Todas"
    lista = [a for a in ag if a["dia"] == dia and (vend == "Todas" or a.get("vend_atend") == vend)]

    def status(a):
        c = confs.get(a["id"])
        if c: return c["status"]
        return "Confirmou" if a.get("confirmou_agenda") else "A confirmar"

    if gestora:
        do_dia = [a for a in ag if a["dia"] == dia]
        linhas = []
        for v in ["Natalya", "Raquel", "Jéssica Martins"]:
            g = [a for a in do_dia if a.get("vend_atend") == v]
            cont = {c: sum(1 for a in g if status(a) == c) for c in CONF}
            cont["Total"] = len(g)
            linhas.append((v.split()[0], cont))
        linhas.append(("Total", {k: sum(l[1][k] for l in linhas) for k in CONF + ["Total"]}))
        st.markdown(f"**Confirmações por vendedora · {rot(dia)}**")
        tabela_resumo(linhas, CONF + ["Total"], alerta=("A confirmar", "Não respondeu"))

    n_ok = sum(1 for a in lista if status(a) == "Confirmou")
    falta = sum(1 for a in lista if status(a) == "A confirmar")
    st.markdown(f'<div class="dia hoje"><b>{rot(dia)}</b><span>{len(lista)} agendamento{"s" if len(lista) != 1 else ""} · '
                f'{n_ok} confirmada{"s" if n_ok != 1 else ""} · {falta} a confirmar</span></div>', unsafe_allow_html=True)
    if not lista:
        st.info("Nenhum agendamento seu neste dia.")
        return
    st.caption("Toque em **Enviar no WhatsApp**: a mensagem abre pronta, é só enviar. "
               "Quando a cliente responder, marque aqui embaixo.")

    for a in lista:
        stt = status(a)
        c = confs.get(a["id"])
        with st.container(border=True):
            partes = [TIPO_ROTULO.get(a.get("tipo"), "")]
            if a.get("ocasiao"): partes.append(a["ocasiao"])
            if a.get("evento"): partes.append(f"evento {ddmm(a['evento'])}")
            if gestora and a.get("vend_atend"): partes.append(a["vend_atend"])
            st.markdown(f'<div class="cab"><span class="hora">{hora_txt(a.get("hora"))}</span>'
                        f'<span class="cli-nome nc">{a.get("nome") or ""}</span>'
                        f'<span class="pill" style="background:{COR_CONF[stt]}">{stt}</span></div>'
                        f'<div class="cli-meta" style="padding-bottom:10px">{" · ".join(p for p in partes if p)}</div>', unsafe_allow_html=True)
            b, r = st.columns([2, 5], vertical_alignment="center")
            if a.get("tel"):
                b.link_button("📲 Enviar no WhatsApp", link_whats(a["tel"], mensagem(a, nome)), use_container_width=True)
            else:
                b.markdown('<span class="stamp">Sem telefone na agenda</span>', unsafe_allow_html=True)
            r.radio("Resposta", CONF, index=CONF.index(stt), horizontal=True, label_visibility="collapsed",
                    key=f"c_{a['id']}", on_change=salvar_conf, args=(a["id"],))
            if c:
                st.markdown(f'<span class="stamp">Marcado por {c.get("por") or "alguém da equipe"} em '
                            f'{ddmm((c.get("em") or "")[:10])}</span>', unsafe_allow_html=True)
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
