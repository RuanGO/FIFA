# gerenciador_fifa_grupos.py
import streamlit as st
import random
import math
import pandas as pd
import itertools
import json
import os

# ----------------- Paths -----------------
BASE_DIR = "dados"
os.makedirs(BASE_DIR, exist_ok=True)

def path(nome):
    return os.path.join(BASE_DIR, nome)

# --------- Utils JSON ---------
def load_json(file, default):
    try:
        with open(path(file), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(path(file), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --------- Funções auxiliares ---------
def formatar_nome(nome):
    return ' '.join(part.capitalize() for part in nome.strip().split())

# --------- Session State ---------
st.session_state.setdefault("jogadores", load_json("jogadores.json", []))
st.session_state.setdefault("fase", None)
st.session_state.setdefault("grupos", load_json("grupos.json", {}))
st.session_state.setdefault("resultados", load_json("resultados.json", []))
st.session_state.setdefault("eliminatorias", load_json("eliminatorias.json", []))
st.session_state.setdefault("fase_elim", 1)
st.session_state.setdefault("proximos_classificados", [])
st.session_state.setdefault("proximos_eliminados", [])
st.session_state.setdefault("finalistas", [])
st.session_state.setdefault("semifinalistas_eliminados", [])

# --------- Funções ---------
def dividir_em_grupos(jogadores):
    random.shuffle(jogadores)
    n = len(jogadores)
    for tamanho_ideal in range(5, 2, -1):
        num_grupos = math.ceil(n / tamanho_ideal)
        if 2 <= num_grupos <= n:
            break
    grupos = [[] for _ in range(num_grupos)]
    for i, jogador in enumerate(jogadores):
        grupos[i % num_grupos].append(jogador)
    return {f"Grupo {i+1}": g for i, g in enumerate(grupos)}

def gerar_partidas_grupo(grupo):
    return list(itertools.combinations(grupo, 2))

def classificar_grupo(grupo, resultados):
    stats = {j: {"Pts":0, "GP":0, "GC":0, "V":0, "J":0} for j in grupo}
    for r in resultados:
        if r["j1"] in grupo and r["j2"] in grupo:
            j1, j2, g1, g2 = r["j1"], r["j2"], r["g1"], r["g2"]
            stats[j1]["GP"] += g1
            stats[j1]["GC"] += g2
            stats[j2]["GP"] += g2
            stats[j2]["GC"] += g1
            stats[j1]["J"] += 1
            stats[j2]["J"] += 1
            if g1 > g2:
                stats[j1]["Pts"] += 3
                stats[j1]["V"] += 1
            elif g2 > g1:
                stats[j2]["Pts"] += 3
                stats[j2]["V"] += 1
            else:
                stats[j1]["Pts"] += 1
                stats[j2]["Pts"] += 1
    df = pd.DataFrame([{
        "Jogador": j,
        "Pontos": v["Pts"],
        "GP": v["GP"],
        "GC": v["GC"],
        "SG": v["GP"] - v["GC"],
        "% Aproveitamento": round((v["V"] / v["J"] * 100) if v["J"] > 0 else 0, 1)
    } for j,v in stats.items()])
    return df.sort_values(["Pontos","SG"], ascending=False).reset_index(drop=True)

def gerar_chave_eliminatoria(jogadores):
    if len(jogadores) == 2:
        return [tuple(jogadores)]
    random.shuffle(jogadores)
    if len(jogadores) % 2 == 1:
        jogadores.append(None)
    return [(jogadores[i], jogadores[i+1]) for i in range(0, len(jogadores), 2)]

def gerar_ranking_geral(resultados):
    stats = {}
    for r in resultados:
        for j in [r["j1"], r["j2"]]:
            if j not in stats:
                stats[j] = {"J": 0, "V": 0, "Pts": 0, "GP": 0, "GC": 0}
        stats[r["j1"]]["J"] += 1
        stats[r["j2"]]["J"] += 1
        stats[r["j1"]]["GP"] += r["g1"]
        stats[r["j1"]]["GC"] += r["g2"]
        stats[r["j2"]]["GP"] += r["g2"]
        stats[r["j2"]]["GC"] += r["g1"]
        if r["g1"] > r["g2"]:
            stats[r["j1"]]["V"] += 1
            stats[r["j1"]]["Pts"] += 3
        elif r["g2"] > r["g1"]:
            stats[r["j2"]]["V"] += 1
            stats[r["j2"]]["Pts"] += 3
        else:
            stats[r["j1"]]["Pts"] += 1
            stats[r["j2"]]["Pts"] += 1

    df = pd.DataFrame([{
        "Jogador": j,
        "Pontos": v["Pts"],
        "Vitórias": v["V"],
        "GP": v["GP"],
        "GC": v["GC"],
        "SG": v["GP"] - v["GC"],
        "% Aproveitamento": round((v["V"] / v["J"]) * 100, 1) if v["J"] > 0 else 0
    } for j, v in stats.items()])
    return df.sort_values(by=["Pontos", "SG", "GP"], ascending=False).reset_index(drop=True)

# --------- Layout ---------
st.title("⚽ Gerenciador de Partidas FIFA - Grupos + Eliminatórias")

# --------- Reset ---------
if st.sidebar.button("Reiniciar Campeonato"):
    for nome in ["jogadores.json", "grupos.json", "resultados.json", "eliminatorias.json"]:
        save_json(nome, [] if nome.endswith(".json") else {})
    st.session_state.clear()
    st.rerun()

# --------- Adicionar Jogadores ---------
st.subheader("👥 Adicionar Jogadores")

# Inicializa a variável somente se ainda não existir
if "input_jogador" not in st.session_state:
    st.session_state.input_jogador = ""

with st.form("adicionar_jogador_form"):
    novo_jogador = st.text_input("Nome do jogador", value=st.session_state.input_jogador, key="input_jogador")
    submitted = st.form_submit_button("Adicionar")
    if submitted:
        nome_formatado = formatar_nome(novo_jogador)
        if nome_formatado and nome_formatado not in st.session_state.jogadores:
            st.session_state.jogadores.append(nome_formatado)
            save_json("jogadores.json", st.session_state.jogadores)
        # Em vez de tentar limpar direto, só marca pra resetar
        st.session_state.pop("input_jogador")  # Força o reset do campo
        st.rerun()


st.write("Jogadores:", st.session_state.jogadores)



# --------- Criar Grupos ---------
if st.session_state.fase is None and len(st.session_state.jogadores) >= 4:
    if st.button("Iniciar Fase de Grupos"):
        grupos = dividir_em_grupos(st.session_state.jogadores)
        st.session_state.grupos = grupos
        st.session_state.fase = "grupos"
        save_json("grupos.json", grupos)
        st.rerun()

# --------- Fase de Grupos ---------
if st.session_state.fase == "grupos":
    st.header("🏟️ Fase de Grupos")
    for nome, grupo in st.session_state.grupos.items():
        st.subheader(nome)
        partidas = gerar_partidas_grupo(grupo)
        for p in partidas:
            if not any(r for r in st.session_state.resultados if (r["j1"], r["j2"]) == p or (r["j2"], r["j1"]) == p):
                col1, col2 = st.columns(2)
                with col1:
                    g1 = st.number_input(f"Gols {p[0]}", min_value=0, key=f"g1_{p}")
                with col2:
                    g2 = st.number_input(f"Gols {p[1]}", min_value=0, key=f"g2_{p}")
                if st.button(f"Salvar Resultado {p[0]} vs {p[1]}", key=f"btn_{p}"):
                    st.session_state.resultados.append({"j1": p[0], "j2": p[1], "g1": int(g1), "g2": int(g2)})
                    save_json("resultados.json", st.session_state.resultados)
                    st.rerun()
        df = classificar_grupo(grupo, st.session_state.resultados)
        st.dataframe(df, use_container_width=True)

    total_partidas = sum(len(gerar_partidas_grupo(g)) for g in st.session_state.grupos.values())
    if len(st.session_state.resultados) >= total_partidas:
        st.success("✅ Todas as partidas dos grupos foram registradas!")
        classificados = []
        for grupo in st.session_state.grupos.values():
            df = classificar_grupo(grupo, st.session_state.resultados)
            classificados.extend(df["Jogador"].head(2).tolist())
        chaves = gerar_chave_eliminatoria(classificados)
        st.session_state.eliminatorias = chaves
        st.session_state.fase = "eliminatorias"
        st.session_state.fase_elim = 1
        save_json("eliminatorias.json", chaves)
        st.rerun()

# --------- Fase Eliminatória ---------
if st.session_state.fase == "eliminatorias":
    fase = st.session_state.fase_elim
    if fase == 1:
        st.header("🏆 Partidas da Semifinal")
    elif fase == 2:
        st.header("🥉 Disputa de 3º Lugar")
    elif fase == 3:
        st.header("🏆 Final")

    todas_concluidas = True
    for i, par in enumerate(st.session_state.eliminatorias):
        if par is None:
            continue
        j1, j2 = par
        if j1 is None or j2 is None:
            vencedor = j1 or j2
            if vencedor:
                st.info(f"{vencedor} está classificado automaticamente (bye)")
                st.session_state.finalistas.append(vencedor)
            st.session_state.eliminatorias[i] = None
            continue

        st.subheader(f"{j1} vs {j2}")
        col1, col2 = st.columns(2)
        with col1:
            g1 = st.number_input(f"Gols {j1}", min_value=0, key=f"elim_g1_{i}")
        with col2:
            g2 = st.number_input(f"Gols {j2}", min_value=0, key=f"elim_g2_{i}")
        p1 = p2 = None
        if g1 == g2:
            st.warning("Empate! Insira o resultado dos pênaltis:")
            col1, col2 = st.columns(2)
            with col1:
                p1 = st.number_input(f"Pênaltis {j1}", min_value=0, key=f"pen1_{i}")
            with col2:
                p2 = st.number_input(f"Pênaltis {j2}", min_value=0, key=f"pen2_{i}")

        if st.button(f"Salvar Resultado {j1} vs {j2}", key=f"elim_btn_{i}"):
            if g1 > g2:
                vencedor, perdedor = j1, j2
            elif g2 > g1:
                vencedor, perdedor = j2, j1
            else:
                if p1 is not None and p2 is not None:
                    vencedor, perdedor = (j1, j2) if p1 > p2 else (j2, j1)
                else:
                    st.warning("Preencha os pênaltis.")
                    st.stop()

            if fase == 1:
                st.session_state.finalistas.append(vencedor)
                st.session_state.semifinalistas_eliminados.append(perdedor)
            elif fase == 2:
                st.session_state.proximos_classificados.append(vencedor)

            st.session_state.resultados.append({
                "j1": j1, "j2": j2,
                "g1": int(g1), "g2": int(g2),
                "pen1": p1, "pen2": p2
            })
            save_json("resultados.json", st.session_state.resultados)
            st.session_state.eliminatorias[i] = None
            st.rerun()
        else:
            todas_concluidas = False

    if todas_concluidas and all(p is None for p in st.session_state.eliminatorias):
        if fase == 1:
            st.session_state.eliminatorias = gerar_chave_eliminatoria(st.session_state.semifinalistas_eliminados)
            st.session_state.fase_elim = 2
        elif fase == 2:
            st.session_state.eliminatorias = gerar_chave_eliminatoria(st.session_state.finalistas)
            st.session_state.fase_elim = 3
        elif fase == 3:
            campeao = st.session_state.finalistas[0] if st.session_state.finalistas else "Erro"
            st.balloons()
            st.success(f"🏆 CAMPEÃO: {campeao}")
            st.session_state.fase = "fim"
        st.rerun()

# --------- Ranking Geral Final ---------
if st.session_state.fase == "fim":
    st.header("📊 Ranking Geral do Campeonato")
    df = gerar_ranking_geral(st.session_state.resultados)
    st.dataframe(df, use_container_width=True)

    # Determinar finalistas e 3º colocado corretamente
    resultados = st.session_state.resultados

    # Final: último resultado
    final = resultados[-1]
    if final["g1"] > final["g2"]:
        campeao = final["j1"]
        vice = final["j2"]
    elif final["g2"] > final["g1"]:
        campeao = final["j2"]
        vice = final["j1"]
    else:
        # Se empate, usa pênaltis
        campeao = final["j1"] if final["pen1"] > final["pen2"] else final["j2"]
        vice = final["j2"] if campeao == final["j1"] else final["j1"]

    # Disputa de 3º lugar: penúltimo resultado
    terceiro_lugar_match = resultados[-2]
    if terceiro_lugar_match["g1"] > terceiro_lugar_match["g2"]:
        terceiro = terceiro_lugar_match["j1"]
    elif terceiro_lugar_match["g2"] > terceiro_lugar_match["g1"]:
        terceiro = terceiro_lugar_match["j2"]
    else:
        terceiro = terceiro_lugar_match["j1"] if terceiro_lugar_match["pen1"] > terceiro_lugar_match["pen2"] else terceiro_lugar_match["j2"]

    st.subheader("🏅 Pódio Final")
    st.markdown(f"🥇 **1º Lugar:** {campeao}")
    st.markdown(f"🥈 **2º Lugar:** {vice}")
    st.markdown(f"🥉 **3º Lugar:** {terceiro}")

    # Destaques individuais
    destaque_ataque = df.sort_values("GP", ascending=False).iloc[0]
    destaque_defesa = df.sort_values("GC").iloc[0]
    destaque_furada = df.sort_values("GC", ascending=False).iloc[0]

    st.subheader("✨ Destaques Individuais")
    st.info(f"🔥 **Ataque Imparável:** {destaque_ataque['Jogador']} com {destaque_ataque['GP']} gols feitos.")
    st.info(f"🛡️ **Defesa Perfeita:** {destaque_defesa['Jogador']} com apenas {destaque_defesa['GC']} gols sofridos.")
    st.info(f"😬 **Defesa Furada:** {destaque_furada['Jogador']} com {destaque_furada['GC']} gols sofridos.")
