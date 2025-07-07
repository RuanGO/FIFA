import streamlit as st
import json
import os
import random
import math
import pandas as pd
from itertools import combinations

# ----------------- Paths -----------------
PLAYERS_FILE      = "players.json"
LEAGUE_MATCHES    = "league_matches.json"
LEAGUE_RESULTS    = "league_results.json"
BRACKETS_FILE     = "brackets.json"
KNOCK_RESULTS     = "knock_results.json"

# ------------- Utils JSON -------------
def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --------- Compat rerun ---------
if hasattr(st, "experimental_rerun"):
    _rerun = st.experimental_rerun
elif hasattr(st, "script_request_rerun"):
    _rerun = st.script_request_rerun
else:
    _rerun = lambda: None

# ------- Inicializa session_state -------
st.session_state.setdefault("players",        load_json(PLAYERS_FILE, []))
st.session_state.setdefault("stage",          None)    # None, "league","semifinal","third","final"
st.session_state.setdefault("league_matches", load_json(LEAGUE_MATCHES, []))
st.session_state.setdefault("league_results", load_json(LEAGUE_RESULTS, []))
st.session_state.setdefault("brackets",       load_json(BRACKETS_FILE, {}))
st.session_state.setdefault("knock_results",  load_json(KNOCK_RESULTS, []))
st.session_state.setdefault("new_player",     "")

# --------- Streamlit Layout ---------
st.set_page_config(page_title="Campeonato Liga + Mata-Mata", layout="centered", page_icon="⚽")
st.title("⚽ Campeonato – Liga + Mata-Mata")
initial_sidebar_state="collapsed"

# … seu código de imports e st.set_page_config acima …

# ————— Botão de reset geral —————
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reiniciar Campeonato (limpar tudo)"):
    # limpa session_state
    st.session_state.players        = []
    st.session_state.stage          = None
    st.session_state.league_matches = []
    st.session_state.league_results = []
    st.session_state.brackets       = {}
    st.session_state.knock_results  = []
    st.session_state.new_player     = ""
    # grava JSONs zerados
    save_json(PLAYERS_FILE, [])
    save_json(LEAGUE_MATCHES, [])
    save_json(LEAGUE_RESULTS, [])
    save_json(BRACKETS_FILE, {})
    save_json(KNOCK_RESULTS, [])
    # recarrega a aplicação
    _rerun()

# … resto do seu código …

# ------------- Helpers -------------
def compute_league_ranking():
    """Retorna um DataFrame com a classificação da liga (round robin)."""
    players = st.session_state.players
    lr = st.session_state.league_results
    if not lr:
        return None

    stats = {p: {"Pts":0,"GP":0,"GC":0} for p in players}
    jogos_cnt = {p:0 for p in players}

    for r in lr:
        t1,t2 = r["time1"], r["time2"]
        g1,g2 = r["g1"], r["g2"]
        # gols
        stats[t1]["GP"] += g1; stats[t1]["GC"] += g2; jogos_cnt[t1] += 1
        stats[t2]["GP"] += g2; stats[t2]["GC"] += g1; jogos_cnt[t2] += 1
        # pontos
        if g1>g2:
            stats[t1]["Pts"] += 3
        elif g2>g1:
            stats[t2]["Pts"] += 3
        else:
            # empate na liga: 1 ponto cada
            stats[t1]["Pts"] += 1
            stats[t2]["Pts"] += 1

    data = []
    for p in players:
        pts = stats[p]["Pts"]
        gp  = stats[p]["GP"]
        gc  = stats[p]["GC"]
        sg  = gp - gc
        jogos = jogos_cnt[p]
        aproveit = round((pts/(jogos*3)*100) if jogos>0 else 0,2)
        data.append({
            "Time": p,
            "Pontos": pts,
            "Gols Pró": gp,
            "Gols Contra": gc,
            "Saldo de Gols": sg,
            "% Aproveitamento": aproveit
        })

    df = (
        pd.DataFrame(data)
          .sort_values(["Pontos","Saldo de Gols"], ascending=[False,False])
          .reset_index(drop=True)
    )
    return df

def build_history_with_pct():
    """Retorna lista de dicts para o histórico, incluindo % de aproveitamento daquela partida."""
    hist = []
    for r in st.session_state.league_results:
        t1,t2 = r["time1"], r["time2"]
        g1,g2 = r["g1"], r["g2"]
        # pontos daquele match
        if g1>g2:
            p1,p2 = 3,0
        elif g2>g1:
            p1,p2 = 0,3
        else:
            # empate na liga: 1 ponto cada
            p1,p2 = 1,1
        pct1 = round(p1/3*100,2); pct2 = round(p2/3*100,2)
        entry = {
            "fase":"Liga",
            "time1":t1, "time2":t2,
            "g1":g1, "g2":g2,
            "%Ap1":pct1, "%Ap2":pct2
        }
        hist.append(entry)
    for r in st.session_state.knock_results:
        t1,t2 = r["time1"], r["time2"]
        g1,g2 = r.get("g1"), r.get("g2")
        # penas
        if g1 is None or g2 is None:
            p1=p2=0
        else:
            if g1>g2:
                p1,p2 = 3,0
            elif g2>g1:
                p1,p2 = 0,3
            else:
                # desempate via p1/p2
                pp1,pp2 = r.get("p1",0), r.get("p2",0)
                if pp1>pp2:
                    p1,p2 = 3,0
                else:
                    p1,p2 = 0,3
        pct1 = round(p1/3*100,2); pct2 = round(p2/3*100,2)
        entry = {
            "fase": r["fase"].capitalize(),
            "time1":t1, "time2":t2,
            "g1":g1, "g2":g2,
            "p1": r.get("p1"), "p2": r.get("p2"),
            "%Ap1":pct1, "%Ap2":pct2
        }
        hist.append(entry)
    return hist

# --------- Histórico de Partidas na Sidebar ---------
st.sidebar.subheader("📖 Histórico de Partidas")
df_hist = pd.DataFrame(build_history_with_pct())
st.sidebar.dataframe(df_hist, use_container_width=True)

# --------- Adicionar Jogador ---------
st.subheader("Adicionar Jogador (pressione Enter)")
def add_player():
    nome = st.session_state.new_player.strip().title()
    if nome and nome not in st.session_state.players:
        st.session_state.players.append(nome)
        save_json(PLAYERS_FILE, st.session_state.players)
    st.session_state.new_player = ""
    _rerun()

st.text_input("", key="new_player", placeholder="Ex: Maria Clara", on_change=add_player)
with st.expander("📓 Jogadores cadastrados"):
    st.write(st.session_state.players)
players = st.session_state.players

# --------- 1) Liga (Round Robin) ---------
if st.session_state.stage is None:
    if len(players) >= 2 and st.button("▶️ Iniciar Liga (Round Robin)"):
        lm = list(combinations(players, 2))
        random.shuffle(lm)
        st.session_state.league_matches = lm
        st.session_state.league_results = []
        st.session_state.stage = "league"
        save_json(LEAGUE_MATCHES, lm)
        save_json(LEAGUE_RESULTS, [])
        _rerun()

if st.session_state.stage == "league":
    st.subheader("🔄 Fase de Liga – Registrar Resultados")
    lm = st.session_state.league_matches
    lr = st.session_state.league_results

    pend = [
        m for m in lm
        if not any(
            (r["time1"], r["time2"]) == m or (r["time2"], r["time1"]) == m
            for r in lr
        )
    ]

    if pend:
        sel = st.selectbox("Selecione partida:", pend, format_func=lambda x: f"{x[0]} vs {x[1]}")
        g1 = st.number_input(f"Gols {sel[0]}", 0, key="lg1")
        g2 = st.number_input(f"Gols {sel[1]}", 0, key="lg2")

        # empate → pênaltis
        p1=p2=None
        if g1 == g2:
            st.warning("🔔 Empate! Informe o placar de pênaltis:")
            p1 = st.number_input(f"Pênaltis {sel[0]}", 0, key="lp1")
            p2 = st.number_input(f"Pênaltis {sel[1]}", 0, key="lp2")

        if st.button("Salvar Resultado Liga"):
            entry = {"time1":sel[0],"time2":sel[1],"g1":int(g1),"g2":int(g2)}
            if p1 is not None:
                entry["p1"],entry["p2"] = int(p1),int(p2)
            lr.append(entry)
            save_json(LEAGUE_RESULTS, lr)
            _rerun()
    else:
        st.success("✅ Todos os resultados da liga registrados!")

    # mostra classificação da liga aqui mesmo
    st.subheader("📊 Classificação da Liga")
    df_league = compute_league_ranking()
    if df_league is not None:
        st.dataframe(df_league, use_container_width=True)
        st.download_button(
            "⬇️ Exportar Classificação (Liga)",
            df_league.to_csv(index=False),
            file_name="classificacao_liga.csv",
            mime="text/csv"
        )

    # botões para gerar mata-mata
    if df_league is not None and len(lr)==len(lm):
        if len(players)>=4 and st.button("⚔️ Gerar Semifinais (Top 4)"):
            top4 = df_league["Time"].tolist()[:4]
            st.session_state.brackets = {
                "semifinal":[(top4[0],top4[3]),(top4[1],top4[2])]
            }
            st.session_state.knock_results = []
            st.session_state.stage = "semifinal"
            save_json(BRACKETS_FILE, st.session_state.brackets)
            save_json(KNOCK_RESULTS, [])
            _rerun()
        elif len(players)==2 and st.button("🏆 Ir para Final Direta"):
            st.session_state.brackets={"final":[(players[0],players[1])]}
            st.session_state.knock_results=[]
            st.session_state.stage="final"
            save_json(BRACKETS_FILE, st.session_state.brackets)
            save_json(KNOCK_RESULTS, [])
            _rerun()

# --------- 2) Mata-Mata com Pênaltis ---------
if st.session_state.stage in ["semifinal","third","final"]:
    st.subheader("🎯 Fases Mata-Mata")
    brackets = st.session_state.brackets
    kres     = st.session_state.knock_results

    for ph in ["semifinal","third","final"]:
        if ph not in brackets:
            continue
        label = "Terceira Posição" if ph=="third" else ph.capitalize()
        st.markdown(f"## {label}")
        pairs = brackets[ph]
        done  = {(r["fase"],r["time1"],r["time2"]) for r in kres}
        pend  = [m for m in pairs if (ph,m[0],m[1]) not in done]

        if pend:
            sel = st.selectbox(f"{label} – selecione:", pend, key=ph,
                               format_func=lambda x: f"{x[0]} vs {x[1]}")
            a,b = sel
            g1 = st.number_input(f"Gols {a}", 0, key=f"{ph}_g1")
            g2 = st.number_input(f"Gols {b}", 0, key=f"{ph}_g2")

            p1=p2=None
            if g1==g2:
                st.warning("🔔 Empate! Informe o placar de pênaltis:")
                p1 = st.number_input(f"Pênaltis {a}",0, key=f"pen1_{ph}")
                p2 = st.number_input(f"Pênaltis {b}",0, key=f"pen2_{ph}")

            if st.button(f"Salvar Resultado {label}", key=f"btn_{ph}"):
                if g1>g2 or (g1==g2 and (p1 or 0)>(p2 or 0)):
                    w,l = a,b
                else:
                    w,l = b,a
                rec = {"fase":ph,"time1":a,"time2":b,"g1":g1,"g2":g2,"winner":w,"loser":l}
                if p1 is not None:
                    rec["p1"],rec["p2"] = p1,p2
                kres.append(rec)
                save_json(KNOCK_RESULTS, kres)

                if ph=="semifinal":
                    # gera third e final
                    if len([r for r in kres if r["fase"]=="semifinal"])\
                       == len(brackets["semifinal"]):
                        wins = [r["winner"] for r in kres if r["fase"]=="semifinal"]
                        lose = [r["loser"]  for r in kres if r["fase"]=="semifinal"]
                        brackets["third"] = [(lose[0],lose[1])]
                        brackets["final"] = [(wins[0],wins[1])]
                        save_json(BRACKETS_FILE, brackets)
                _rerun()
        else:
            st.success(f"✅ Todos resultados de **{label.lower()}** registrados!")
            if ph=="final":
                champ = [r["winner"] for r in kres if r["fase"]=="final"][0]
                st.balloons(); st.success(f"🏆 Campeão: **{champ}**")

# -------------------------------------------------
#  🚩 Sempre ao final, exibe de novo a classificação da Liga
# -------------------------------------------------
df_league = compute_league_ranking()
if df_league is not None:
    st.markdown("---")
    st.subheader("📊 Classificação Geral da Liga")
    st.dataframe(df_league, use_container_width=True)
    st.download_button(
        "⬇️ Exportar Classificação Geral",
        df_league.to_csv(index=False),
        file_name="classificacao_geral.csv",
        mime="text/csv"
    )
