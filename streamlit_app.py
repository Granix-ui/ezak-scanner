import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin

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
    total_found = 0
    total_processed = 0
    total_active = 0
    now = datetime.now()

    with st.spinner("Načítám data..."):
        for url in urls:
            url_found = 0
            url_processed = 0
            url_active = 0
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                table = soup.find("table")
                if not table:
                    st.warning(f"Na {url}: Nebyla nalezena tabulka zakázek.")
                    continue

                rows = table.find_all("tr")[1:]  # přeskočit hlavičku
                st.info(f"Na {url}: Načteno {len(rows)} řádků v tabulce.")

                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) < 6:
                        continue

                    url_found += 1

                    name_tag = cols[0].find("a")
                    if not name_tag or "contract_display_" not in name_tag.get("href", ""):
                        continue

                    name = name_tag.text.strip()
                    link = urljoin(url, name_tag["href"])

                    zadavatel = cols[1].get_text(separator=" ", strip=True)

                    start_str = cols[4].text.strip()

                    deadline_str = cols[5].get_text(separator=" ", strip=True)
                    deadline_str = deadline_str.replace("\xa0", " ").strip()

                    if not deadline_str or deadline_str in ["-", ""]:
                        continue

                    url_processed += 1

                    try:
                        if ":" in deadline_str.split()[-1]:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                        else:
                            deadline = datetime.strptime(deadline_str, "%d.%m.%Y")
                        if deadline > now:
                            url_active += 1
                            data.append({
                                "Zadavatel": zadavatel,
                                "Název zakázky": name,
                                "Datum zahájení": start_str,
                                "Lhůta pro nabídky": deadline_str,
                                "Odkaz": link
                            })
                    except ValueError:
                        continue

                st.info(f"Na {url}: Celkem zakázek {url_found}, zpracováno {url_processed}, aktivních {url_active}.")

                total_found += url_found
                total_processed += url_processed
                total_active += url_active

            except Exception as e:
                st.warning(f"Chyba na {url}: {e}")

        st.info(f"Celkem přes všechny URL: Zakázek {total_found}, zpracováno {total_processed}, aktivních {total_active}.")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")  # nejblížší nahoře

        st.success(f"Zobrazeno {len(df)} aktivních zakázek!")
        st.dataframe(
            df,
            column_config={
                "Název zakázky": st.column_config.LinkColumn(
                    "Název zakázky",
                    display_text=df["Název zakázky"],
                    validate=None
                ),
                "Odkaz": None  # schovat sloupec s odkazem
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny (ale viz výše počty pro kontrolu).")
