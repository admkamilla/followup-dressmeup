# FOLLOW UP - DRESS ME UP GOIANIA

App da equipe de vendas, no mesmo esquema do Dress Finance (Streamlit + Supabase).
As vendedoras entram com e-mail e senha próprios, sem conta no Claude, e veem só a lista de follow-up. Nenhum valor aparece.

## O que tem aqui

| Arquivo | Para que serve |
|---|---|
| `app.py` | O app |
| `requirements.txt` | Bibliotecas que o Streamlit instala |
| `.streamlit/config.toml` | Cores (cinza claro, branco, burgundy) |
| `schema.sql` | Tabelas do banco. **O Claude roda isso para você** pelo conector do Supabase |

---

## Passo a passo (faça um de cada vez e marque ✅)

### ☐ 1. Conectar o Supabase no Claude
No Claude: Configurações → Conectores → Supabase → Conectar.
Depois avise o Claude. Ele cria um **projeto novo e separado do Dress Finance**, monta as tabelas e carrega a lista de clientes.

> Por que separado: as vendedoras vão ter login nesse banco. Num projeto à parte, não existe nenhum caminho até os dados financeiros.

### ☐ 2. Cadastrar as vendedoras
No site do Supabase, no projeto novo:
**Authentication → Users → Add user → Create new user**
- E-mail de cada vendedora + uma senha provisória
- Marque **Auto Confirm User**

Passe para cada uma o e-mail e a senha dela.

### ☐ 3. Colocar o código no GitHub
Do mesmo jeito que você fez com o Dress Finance:
- Crie um repositório novo (ex.: `followup-dressmeup`), **privado**
- Suba os arquivos desta pasta (incluindo a pasta `.streamlit`)

### ☐ 4. Publicar no Streamlit Cloud
- share.streamlit.io → **Create app** → escolha o repositório → arquivo `app.py`
- Em **Advanced settings → Secrets**, cole:

```
SUPABASE_URL = "cole aqui a Project URL"
SUPABASE_ANON_KEY = "cole aqui a anon public key"
```

Os dois ficam no Supabase, em **Project Settings → API**.
⚠️ Use a chave **anon public**. A `service_role` nunca vai no app.

### ☐ 5. Mandar o link para a equipe
O link do Streamlit é o app. No celular, elas podem abrir e "Adicionar à tela inicial".

---

## Como a lista se atualiza
Três vezes por dia (7h45, 12h45 e 18h45), a tarefa agendada do Claude:
1. lê a Google Agenda da loja;
2. atualiza a lista de clientes no app (quem faltou, quem remarcou, quem veio);
3. traz para o seu CRM o que a equipe preencheu.

Nada disso exige que alguém deixe o computador ligado.
