from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta

app = Flask(__name__)

FICHIER = "mesures.xlsx"

# Définition des mesures pour chaque site
mesures_smp = [
    "Exhaure 1", "Exhaure 2", "Exhaure 3", "Exhaure 4", "Retour dessableur", "Retour Orage",
    "Rejet à l'Arc", "Surpresseur 4 pompes", "Surpresseur 7 pompes", "Entrée STE CAB",
    "Alimentation CAB", "Eau potable", "Forage", "Boue STE", "Boue STE CAB",
    "pH entrée", "pH sortie", "Température entrée", "Température sortie",
    "Conductivité sortie", "MES entrée", "MES sortie", "Coagulant", "Floculant", "CO2"
]

mesures_lpz = [
    "Exhaure 1", "Exhaure 2", "Retour dessableur", "Surpresseur BP", "Surpresseur HP",
    "Rejet à l'Arc", "Entrée STE CAB", "Alimentation CAB", "Eau de montagne", "Boue STE",
    "Boue STE CAB", "pH entrée", "pH sortie", "Température entrée", "Température sortie",
    "Conductivité sortie", "MES entrée", "MES sortie", "Coagulant", "Floculant", "CO2"
]

sites = {"SMP": mesures_smp, "LPZ": mesures_lpz}

# Paramètres différenciels
parametres_compteurs = {
    "SMP": [
        "Exhaure 1", "Exhaure 2", "Exhaure 3", "Exhaure 4", "Retour dessableur", "Retour Orage",
        "Rejet à l'Arc", "Surpresseur 4 pompes", "Surpresseur 7 pompes", "Entrée STE CAB",
        "Alimentation CAB", "Eau potable", "Forage"
    ],
    "LPZ": [
        "Exhaure 1", "Exhaure 2", "Retour dessableur", "Surpresseur BP", "Surpresseur HP",
        "Rejet à l'Arc", "Entrée STE CAB", "Alimentation CAB", "Eau de montagne"
    ]
}

# Paramètres directs
parametres_directs = {
    "SMP": [
        "Boue STE", "Boue STE CAB", "pH entrée", "pH sortie", "Température entrée", "Température sortie",
        "Conductivité sortie", "MES entrée", "MES sortie", "CO2"
    ],
    "LPZ": [
        "Boue STE", "Boue STE CAB", "pH entrée", "pH sortie", "Température entrée", "Température sortie",
        "Conductivité sortie", "MES entrée", "MES sortie", "CO2"
    ]
}

# Initialisation du fichier Excel
def initialiser_fichier():
    if not os.path.exists(FICHIER):
        with pd.ExcelWriter(FICHIER) as writer:
            for site, mesures in sites.items():
                pd.DataFrame(columns=["Date", "Statut"] + mesures).to_excel(writer, sheet_name=site, index=False)

def charger_donnees(site):
    if not os.path.exists(FICHIER):
        initialiser_fichier()
    try:
        return pd.read_excel(FICHIER, sheet_name=site, engine="openpyxl")
    except:
        return pd.DataFrame(columns=["Date", "Statut"] + sites[site])

def sauvegarder_donnees(df_modifie, site):
    dfs = {}
    if os.path.exists(FICHIER):
        with pd.ExcelFile(FICHIER, engine="openpyxl") as xls:
            for sheet in xls.sheet_names:
                dfs[sheet] = xls.parse(sheet)
    else:
        initialiser_fichier()
        for s in sites:
            dfs[s] = pd.DataFrame(columns=["Date", "Statut"] + sites[s])

    dfs[site] = df_modifie

    with pd.ExcelWriter(FICHIER, engine="openpyxl", mode="w") as writer:
        for sheet, data in dfs.items():
            data.to_excel(writer, sheet_name=sheet, index=False)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/saisie/<site>", methods=["GET", "POST"])
def saisie(site):
    mesures = sites[site]
    df = charger_donnees(site)
    today_date = datetime.now()
    today_str = today_date.strftime("%Y-%m-%d")

    yesterday = (today_date - timedelta(days=1)).strftime("%Y-%m-%d")
    veille = df[(df["Date"] == yesterday) & (df["Statut"] == "Validé")]

    valeurs_veille = {}
    for m in mesures:
        valeurs_veille[m] = ""
        if not veille.empty:
            valeurs_veille[m] = veille[m].iloc[-1]

    brouillon = df[(df["Date"] == today_str) & (df["Statut"] == "Brouillon")]
    valide = df[(df["Date"] == today_str) & (df["Statut"] == "Validé")]

    if request.method == "POST":
        if "choix" in request.form:
            choix = request.form["choix"]
            if choix == "annuler":
                return redirect("/")
            elif choix == "ecraser":
                valid_today = df[(df["Date"] == today_str) & (df["Statut"] == "Validé")]
                if not valid_today.empty:
                    last_idx = valid_today.index[-1]
                    df = df.drop(last_idx)
                sauvegarder_donnees(df, site)
                return redirect(url_for("saisie", site=site))
            elif choix == "nouveau":
                ligne = {"Date": today_str, "Statut": "Brouillon"}
                for m in mesures:
                    ligne[m] = ""
                df.loc[len(df)] = ligne
                sauvegarder_donnees(df, site)
                return redirect(url_for("saisie", site=site))

        ligne = {"Date": today_str, "Statut": "Brouillon"}
        for m in mesures:
            if m == "Coagulant" and today_date.weekday() != 0:
                ligne[m] = ""
            else:
                ligne[m] = request.form.get(m) or ""

        if not brouillon.empty:
            idx = brouillon.index[0]
            for k, v in ligne.items():
                df.loc[idx, k] = v
        else:
            df.loc[len(df)] = ligne

        if "finaliser" in request.form:
            df.loc[(df["Date"] == today_str) & (df["Statut"] == "Brouillon"), "Statut"] = "Validé"

        sauvegarder_donnees(df, site)
        message = "Mesure validée." if "finaliser" in request.form else "Brouillon sauvegardé."
        return render_template("confirmation.html", message=message)

    valeurs = {}
    if not brouillon.empty:
        valeurs = brouillon.iloc[0].fillna("").to_dict()
    elif not valide.empty:
        n = len(valide) + 1
        return render_template("alerte.html", site=site, n=n)

    is_monday = today_date.weekday() == 0
    return render_template("saisie.html", site=site, mesures=mesures, valeurs=valeurs, valeurs_veille=valeurs_veille, is_monday=is_monday)

@app.route("/visualisation", methods=["GET", "POST"])
def visualisation():
    sites_list = list(sites.keys())
    mesures_par_site = sites
    plot_url = None

    if request.method == "POST":
        site = request.form["site"]
        parametre = request.form["parametre"]

        df = charger_donnees(site)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df[df["Statut"] == "Validé"]
        df = df.sort_values("Date")

        if parametre == "Coagulant":
            df_lundi = df[df["Date"].dt.weekday == 0]
            df_lundi[parametre] = pd.to_numeric(df_lundi[parametre], errors="coerce").fillna(0)
            df_lundi["Semaine"] = df_lundi["Date"].dt.isocalendar().week
            df_lundi = df_lundi.groupby("Semaine").agg({parametre: "first"}).sort_index()
            df_lundi["Semaine_suivante"] = df_lundi[parametre].shift(-1)
            df_lundi["Consommation"] = df_lundi["Semaine_suivante"] - df_lundi[parametre]
            df_lundi.loc[df_lundi["Consommation"] < 0, "Consommation"] += 1000
            df_lundi = df_lundi.dropna(subset=["Consommation"])
            semaines = df_lundi.index.tolist()
            valeurs = df_lundi["Consommation"].tolist()
            titre = f"Consommation hebdomadaire de {parametre} - {site}"

            plt.figure(figsize=(10, 5))
            plt.bar(semaines, valeurs)
            plt.title(titre)
            plt.xlabel("Semaine")
            plt.ylabel("Consommation")
            plt.xticks(semaines)
            plt.tight_layout()

        elif parametre in parametres_compteurs.get(site, []):
            df[parametre] = pd.to_numeric(df[parametre], errors='coerce').fillna(0)
            df["Delta"] = df[parametre].diff().fillna(0)
            dates = df["Date"].dt.date.tolist()
            valeurs = df["Delta"].tolist()
            titre = f"Variation journalière de {parametre} - {site}"

            plt.figure(figsize=(10, 5))
            plt.plot(dates, valeurs, marker="o")
            plt.title(titre)
            plt.xticks(rotation=45)
            plt.tight_layout()

        else:
            dates = df["Date"].dt.date.tolist()
            valeurs = pd.to_numeric(df[parametre], errors="coerce").fillna(0).tolist()
            titre = f"Mesure de {parametre} - {site}"

            plt.figure(figsize=(10, 5))
            plt.plot(dates, valeurs, marker="o")
            plt.title(titre)
            plt.xticks(rotation=45)
            plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format="png")
        img.seek(0)
        plot_url = base64.b64encode(img.read()).decode()
        plt.close()

    return render_template("visualisation.html", 
                           sites=sites_list, 
                           mesures_par_site=mesures_par_site,
                           plot_url=plot_url)

if __name__ == "__main__":
    app.run(debug=True)
