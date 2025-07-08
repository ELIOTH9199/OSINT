#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import sqlite3
import time
import requests
import threading
from termcolor import colored
from duckduckgo_search import DDGS

# Optional OpenAI GPT integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ===== CONFIGURATION =====
API_NUMVERIFY_KEY = "fb2cfh78ae7d085656ff6b70801c"  # Change if needed
OPENAI_API_KEY = "sk-projAnvS3KV-lZNH_3rokGCIGu7479J0xIJTjP271BCWtcyIflfiSRA9lhBZBMQSRbsERYET3BlbkFJlPXaa2XVeOPlFvY97glAG5f6lcKy8abfyvNLFWkyGNhZ1C5gzpvDiWESFjPwE_3UOsXhXLFdYA"

IMEI_BLACKLIST = {
    # Sample stolen IMEIs (add yours)
    "123456789012345",
    "357951456123789",
}

NUMERO_BLACKLIST = {
    # Sample suspicious numbers
    "+24206600000",
    "+1234567890",
}

DB_FILE = "enquete_data.db"

# ===== INITIALISATION BASE DE DONNEES =====
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS enquete (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            valeur TEXT UNIQUE,
            donnees TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

# ===== UTILITAIRES =====
def titre(msg):
    print(colored(f"\n=== {msg} ===", "cyan", attrs=["bold"]))

def pause():
    input(colored("\nAppuyez sur Entrée pour revenir au menu...", "yellow"))

def save_to_db(conn, typ, valeur, donnees):
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO enquete (type, valeur, donnees) VALUES (?, ?, ?)",
                  (typ, valeur, json.dumps(donnees, ensure_ascii=False)))
        conn.commit()
    except Exception as e:
        print(colored(f"[!] Erreur DB: {e}", "red"))

# ===== FONCTION TRACKER EMAIL =====
def tracker_email(conn):
    os.system("clear")
    titre("Suivi d'un email (Infoga simulé + Sherlock + GPT)")
    email = input("Entrez l'adresse email à tracker : ").strip()
    if not email:
        print(colored("[!] Email vide.", "red"))
        pause()
        return

    print(colored(f"[*] Recherche d'informations sur l'email : {email}", "green"))
    # Infoga simulation
    infoga_res = {
        "email": email,
        "found": True,
        "infos": {
            "domain": email.split("@")[-1],
            "possible_leaks": True
        }
    }
    print(colored("[+] Infoga (simulé) terminé.", "green"))

    # Sherlock réel (simple simulation ici, tu peux remplacer par un appel système)
    print(colored("[*] Recherche pseudo/réseaux sociaux avec Sherlock (simulation)...", "yellow"))
    sherlock_res = {
        "twitter": f"https://twitter.com/{email.split('@')[0]}",
        "facebook": f"https://facebook.com/{email.split('@')[0]}",
        "instagram": f"https://instagram.com/{email.split('@')[0]}"
    }
    print(colored("[+] Sherlock simulation terminée.", "green"))

    # Résumé GPT (si dispo et clé valide)
    gpt_summary = ""
    if OPENAI_AVAILABLE:
        openai.api_key = OPENAI_API_KEY
        prompt = f"Donne un résumé OSINT pour l'email {email} avec infos Infoga et Sherlock : {json.dumps({'infoga': infoga_res, 'sherlock': sherlock_res}, ensure_ascii=False)}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=250
            )
            gpt_summary = response.choices[0].message.content.strip()
        except Exception as e:
            gpt_summary = f"Erreur GPT : {e}"
    else:
        gpt_summary = "Module OpenAI non installé ou clé manquante."

    print(colored("\n=== Résumé GPT ===", "cyan"))
    print(gpt_summary)

    # Sauvegarde en DB
    save_to_db(conn, "email", email, {
        "infoga": infoga_res,
        "sherlock": sherlock_res,
        "gpt_summary": gpt_summary
    })

    pause()

# ===== FONCTION SCANNER NUMERO =====
def scanner_numero(conn):
    os.system("clear")
    titre("Scan de numéro (Numverify + DuckDuckGo + blacklist)")
    numero = input("Entrez le numéro (avec indicatif, ex : +242...) : ").strip()
    if not numero:
        print(colored("[!] Numéro vide.", "red"))
        pause()
        return

    print(colored("[*] Recherche Numverify...", "green"))
    url = f"http://apilayer.net/api/validate?access_key={API_NUMVERIFY_KEY}&number={numero}&country_code=&format=1"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(colored(f"[!] Erreur API Numverify: {e}", "red"))
        pause()
        return

    if not data.get("valid", False):
        print(colored("[!] Numéro invalide.", "red"))
        pause()
        return

    # Affichage simple
    for k in ["valid", "number", "local_format", "international_format", "country_prefix",
              "country_code", "country_name", "location", "carrier", "line_type"]:
        print(f"{k}: {data.get(k, '')}")

    # Vérification blacklist
    if numero in NUMERO_BLACKLIST:
        print(colored("[!] Attention : numéro dans blacklist suspecte !", "red"))

    print(colored("[*] Recherche DuckDuckGo...", "green"))
    results = []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(numero, max_results=5)
    except Exception as e:
        print(colored(f"[!] Erreur DuckDuckGo: {e}", "red"))

    if results:
        print(colored("[+] Résultats DuckDuckGo :", "green"))
        for r in results:
            print(f"- {r.get('title')} | {r.get('href')}")
    else:
        print(colored("[!] Aucun résultat DuckDuckGo.", "yellow"))

    # Résumé GPT (optionnel)
    gpt_summary = ""
    if OPENAI_AVAILABLE:
        openai.api_key = OPENAI_API_KEY
        prompt = f"Donne un résumé OSINT sur le numéro de téléphone {numero} avec données Numverify et DuckDuckGo : {json.dumps({'numverify': data, 'duckduckgo': results}, ensure_ascii=False)}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=250
            )
            gpt_summary = response.choices[0].message.content.strip()
        except Exception as e:
            gpt_summary = f"Erreur GPT : {e}"
    else:
        gpt_summary = "Module OpenAI non installé ou clé manquante."

    print(colored("\n=== Résumé GPT ===", "cyan"))
    print(gpt_summary)

    save_to_db(conn, "numero", numero, {
        "numverify": data,
        "duckduckgo": results,
        "gpt_summary": gpt_summary
    })

    pause()

# ===== FONCTION TRAQUER IMEI =====
def traquer_imei(conn):
    import re
    from bs4 import BeautifulSoup

    os.system("clear")
    titre("Traquer un IMEI (imei24.com + blacklist)")

    imei = input("Entrez l'IMEI (15 chiffres) : ").strip()
    if not re.match(r"^\d{15}$", imei):
        print(colored("[!] IMEI invalide, doit faire 15 chiffres.", "red"))
        pause()
        return

    # Vérification blacklist
    if imei in IMEI_BLACKLIST:
        print(colored("[!] IMEI signalé volé/suspect dans base noire !", "red"))

    # Scraping imei24.com (exemple)
    url = f"https://imei24.com/?imei={imei}"
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        # Extraction simplifiée: récupère titre page
        title = soup.title.string.strip() if soup.title else "N/A"
    except Exception as e:
        print(colored(f"[!] Erreur scraping imei24.com: {e}", "red"))
        pause()
        return

    print(colored(f"[+] Données imei24.com : {title}", "green"))

    # Résumé GPT (optionnel)
    gpt_summary = ""
    if OPENAI_AVAILABLE:
        openai.api_key = OPENAI_API_KEY
        prompt = f"Analyse et résumé OSINT pour IMEI {imei} avec info imei24.com: {title}"
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=200
            )
            gpt_summary = response.choices[0].message.content.strip()
        except Exception as e:
            gpt_summary = f"Erreur GPT : {e}"
    else:
        gpt_summary = "Module OpenAI non installé ou clé manquante."

    print(colored("\n=== Résumé GPT ===", "cyan"))
    print(gpt_summary)

    save_to_db(conn, "imei", imei, {
        "imei24_title": title,
        "gpt_summary": gpt_summary
    })

    pause()

# ===== FONCTION VERIFIER FUITES EMAIL (HaveIBeenPwned API) =====
def verifier_fuite_email(conn):
    os.system("clear")
    titre("Vérification fuites email (HaveIBeenPwned)")

    email = input("Entrez l'adresse email : ").strip()
    if not email:
        print(colored("[!] Email vide.", "red"))
        pause()
        return

    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    headers = {
        "User-Agent": "OSINT-Enquete-Tool",
        # Tu dois ajouter ta clé API HaveIBeenPwned ici si tu en as une, sinon ça peut bloquer.
        # "hibp-api-key": "VOTRE_CLE_API_HIBP"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            breaches = r.json()
            print(colored(f"[+] L'email {email} a été compromis dans {len(breaches)} fuite(s) :\n", "green"))
            for b in breaches:
                print(f"- {b.get('Title')} ({b.get('BreachDate')})")
        elif r.status_code == 404:
            print(colored(f"[+] L'email {email} n'a pas été trouvé dans les bases de fuites.", "green"))
        elif r.status_code == 401:
            print(colored("[!] Erreur API HaveIBeenPwned : accès non autorisé (clé API requise).", "red"))
        else:
            print(colored(f"[!] Erreur API HaveIBeenPwned : code {r.status_code}", "red"))
    except Exception as e:
        print(colored(f"[!] Exception API HaveIBeenPwned : {e}", "red"))

    pause()

# ===== MENU =====
def menu():
    conn = init_db()
    while True:
        os.system("clear")
        titre("MENU PRINCIPAL")
        print(colored("[1] Tracker un Email (Infoga + Sherlock + GPT)", "yellow"))
        print(colored("[2] Scanner un Numéro (Numverify + DuckDuckGo + GPT)", "yellow"))
        print(colored("[3] Traquer un IMEI (imei24.com + blacklist + GPT)", "yellow"))
        print(colored("[4] Vérifier si Email a fuité (HaveIBeenPwned)", "yellow"))
        print(colored("[0] Quitter", "red"))

        choix = input(colored("Choix > ", "cyan")).strip()
        if choix == "1":
            tracker_email(conn)
        elif choix == "2":
            scanner_numero(conn)
        elif choix == "3":
            traquer_imei(conn)
        elif choix == "4":
            verifier_fuite_email(conn)
        elif choix == "0":
            print(colored("Au revoir !", "green"))
            conn.close()
            sys.exit(0)
        else:
            print(colored("[!] Choix invalide.", "red"))
            time.sleep(1)

if __name__ == "__main__":
    menu()
