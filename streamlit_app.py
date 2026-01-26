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

                contract_links = soup.find_all("a", href=re.compile("contract_display_"))

                for a in contract_links:
                    name = a.text.strip()
                    if not name:
                        continue
                    link = urljoin(response.url, a["href"])

                    tr = a.find_parent("tr")
                    if not tr:
                        continue

                    tr_text = tr.get_text(separator=" ", strip=True)

                    start_match = re.search(r"Datum zahájení.*?(\d{2}\.\d{2}\.\d{4})", tr_text)
                    start_date_str = start_match.group(1) if start_match else "Neuvedeno"

                    deadline_match = re.search(r"(?:Lhůta|Lhota|Lh[ůo]ta).*?(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)", tr_text, re.IGNORECASE)
                    if not deadline_match:
                        continue
                    deadline_str = deadline_match.group(1).strip()

                    zadavatel_match = re.search(r"\*([^*]+)\*", tr_text)
                    zadavatel = zadavatel_match.group(1).strip() if zadavatel_match else url.split("//")[1].split("/")[0]

                    try:
                        if ":" in deadline_str:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                        else:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
                        if deadline <= now:
                            continue
                    except:
                        continue

                    data.append({
                        "Zadavatel": zadavatel,
                        "Název zakázky": name,
                        "Datum zahájení": start_date_str,
                        "Lhůta pro nabídky": deadline_str,
                        "Odkaz": link
                    })

            except Exception as e:
                st.warning(f"Chyba na {url}: {e}")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")
        st.success(f"Načteno {len(df)} aktivních zakázek!")
        st.dataframe(df, use_container_width=True)
        csv = df.to_csv(index=False).encode()
        st.download_button("Stáhnout CSV", csv, "zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny.")
