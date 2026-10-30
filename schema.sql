-- FOLLOW UP - DRESS ME UP GOIANIA: tabelas e regras de acesso
create table if not exists clientes (
  id text primary key,
  nome text, tel text, ocasiao text, grupo text,
  evento date, ultimo date, proxima date,
  etapa text, vend_atend text, confirmou boolean default false,
  auto_status text, auto_texto text, auto_em timestamptz,
  atualizado_em timestamptz default now()
);
create table if not exists followups (
  cliente_id text primary key,
  status text not null default 'Por fazer',
  proximo date, motivo text, nota text,
  por text, em timestamptz default now()
);
alter table clientes enable row level security;
alter table followups enable row level security;
-- equipe logada lê a lista; só a sincronização (Claude) escreve nela
drop policy if exists "equipe le clientes" on clientes;
create policy "equipe le clientes" on clientes for select to authenticated using (true);
-- equipe logada lê e grava follow-ups (sem apagar)
drop policy if exists "equipe le followups" on followups;
create policy "equipe le followups" on followups for select to authenticated using (true);
drop policy if exists "equipe cria followups" on followups;
create policy "equipe cria followups" on followups for insert to authenticated with check (true);
drop policy if exists "equipe edita followups" on followups;
create policy "equipe edita followups" on followups for update to authenticated using (true) with check (true);
