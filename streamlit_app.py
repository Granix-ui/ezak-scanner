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

                table = soup.find("table")
                if not table:
                    st.warning(f"Na {url} nebyla nalezena tabulka zakázek.")
                    continue

                rows = table.find_all("tr")[1:]  # přeskočit hlavičku

                # Fallback zadavatel z title nebo URL
                page_title = soup.title.text.strip() if soup.title else ""
                fallback_zadavatel = page_title.split("-")[-1].strip() if "-" in page_title else url.split("//")[1].split("/")[0].split(".")[1] if len(url.split("//")[1].split("/")[0].split(".")) > 1 else "Neznámý zadavatel"

                found_any = False
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) not in [5, 6]:
                        continue

                    name_tag = cols[0].find("a", href=re.compile("contract_display_"))
                    if not name_tag:
                        continue
                    name = name_tag.text.strip()
                    link = urljoin(url, name_tag["href"])

                    # Datum zahájení: předposlední sloupec
                    start_str = cols[-2].text.strip()

                    # Lhůta: poslední sloupec
                    deadline_str = cols[-1].text.strip()
                    if not deadline_str or deadline_str == "-":
                        continue

                    # Zadavatel
                    zadavatel = cols[1].text.strip() if len(cols) == 6 else fallback_zadavatel

                    # Parsování lhůty
                    try:
                        deadline_clean = re.sub(r"\s+", " ", deadline_str).strip()
                        if ":" in deadline_clean:
                            deadline = datetime.strptime(deadline_clean, "%d.%m.%Y %H:%M")
                        else:
                            deadline = datetime.strptime(deadline_clean, "%d.%m.%Y")
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
                    found_any = True

                if not found_any:
                    st.info(f"Na {url} žádné aktivní zakázky (nebo jen staré).")

            except Exception as e:
                st.warning(f"Chyba na {url}: {e}")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")
        st.success(f"Načteno {len(df)} aktivních zakázek!")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Celkově žádné aktivní zakázky nenalezeny z zadaných URL.")
