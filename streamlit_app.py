import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin
import re

st.title("E-ZAK Scanner – aktivní zakázky")

urls_text = st.text_area(
    "Zadej URL E-ZAK seznamů (jedna na řádek)",
    height=200,
    value="https://ezak.sokolov.cz/contract_index.html\n"
          "https://qcm.ezak.cz/profile_display_206.html\n"
          "https://qcm.ezak.cz/profile_display_27.html?state=all&archive=ACTUAL&otype=all&contract_place=\n"
          "https://qcm.ezak.cz/profile_display_98.html\n"
          "https://ezak.kr-karlovarsky.cz/contract_index.html\n"
          "https://ezak.mmkv.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://qcm.ezak.cz/contract_index.html?type=all&state=active&archive=ACTUAL&contract_place=CZ041"
)

if st.button("Načíst čerstvá data"):
    urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
    if not urls:
        st.error("Zadej alespoň jednu URL!")
        st.stop()

    data = []
    now = datetime.now()

    with st.spinner("Načítám data..."):
        for url in urls:
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                # Fallback zadavatel z title stránky
                page_title = soup.title.text.strip() if soup.title else ""
                fallback_zadavatel = page_title.split(" - ")[0].strip() if " - " in page_title else url.split("//")[1].split("/")[0]

                # Najdi všechny odkazy na zakázky
                contract_links = soup.find_all("a", href=re.compile(r"contract_display_"))

                for a in contract_links:
                    name = a.text.strip()
                    if not name:
                        continue
                    link = urljoin(url, a["href"])

                    # Najdi řádek (tr) s touto zakázkou
                    tr = a.find_parent("tr")
                    if not tr:
                        continue

                    tds = tr.find_all("td")
                    if len(tds) < 4:  # minimálně potřebujeme sloupce s daty
                        continue

                    # Lhůta: vždy poslední sloupec
                    deadline_str = tds[-1].text.strip()
                    deadline_str = re.sub(r"\s+", " ", deadline_str)  # vyčistit mezery

                    if not deadline_str or deadline_str == "-" or " " not in deadline_str:
                        continue

                    # Datum zahájení: předposlední sloupec
                    start_str = tds[-2].text.strip() if len(tds) >= 5 else "Neuvedeno"

                    # Zadavatel: druhý sloupec, pokud existuje
                    zadavatel = tds[1].text.strip() if len(tds) >= 2 else fallback_zadavatel

                    # Parsování lhůty pro filtr
                    try:
                        if ":" in deadline_str:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                        else:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
                        if deadline <= now:
                            continue
                    except ValueError:
                        continue

                    data.append({
                        "Zadavatel": zadavatel,
                        "Název zakázky": name,
                        "Datum zahájení": start_str,
                        "Lhůta pro nabídky": deadline_str,
                        "Odkaz": link
                    })

            except Exception as e:
                st.warning(f"Chyba na {url}: {e}")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")  # nejblížší lhůty nahoře

        # Vytvoř klikatelný název
        df["Název zakázky"] = df.apply(lambda row: f'<a href="{row["Odkaz"]}">{row["Název zakázky"]}</a>', axis=1)

        # Odstraníme sloupec s holým odkazem
        df = df.drop(columns=["Odkaz"])

        st.success(f"Načteno {len(df)} aktivních zakázek!")
        st.dataframe(
            df,
            column_config={
                "Název zakázky": st.column_config.TextColumn(
                    "Název zakázky",
                    help="Klikni pro otevření detailu zakázky",
                    unsafe_allow_html=True
                )
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny z zadaných URL.")
