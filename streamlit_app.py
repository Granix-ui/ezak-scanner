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
    now = datetime.now()

    with st.spinner("Načítám data..."):
        for url in urls:
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")

                table = soup.find("table")
                if not table:
                    st.warning(f"Na {url} nebyla nalezena tabulka.")
                    continue

                rows = table.find_all("tr")[1:]  # přeskočit hlavičku

                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) != 6:
                        continue  # jen standardní řádky

                    # Název a odkaz
                    name_tag = cols[0].find("a")
                    if not name_tag:
                        continue
                    name = name_tag.text.strip()
                    link = urljoin(url, name_tag["href"])

                    # Zadavatel (často s extra tagy, ale text vezmeme)
                    zadavatel = cols[1].get_text(separator=" ", strip=True)

                    # Datum zahájení
                    start_str = cols[4].text.strip()

                    # Lhůta
                    deadline_str = cols[5].text.strip()
                    if not deadline_str or deadline_str == "-" or deadline_str == "":
                        continue

                    # Parsování lhůty pro filtr (vyčistit neviditelné znaky)
                    deadline_clean = deadline_str.replace("\xa0", " ").strip()
                    try:
                        if ":" in deadline_clean:
                            deadline = datetime.strptime(deadline_clean, "%d.%m.%Y %H:%M")
                        else:
                            deadline = datetime.strptime(deadline_clean, "%d.%m.%Y")
                        if deadline <= now:
                            continue  # jen budoucí
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
        df = df.sort_values("Lhůta pro nabídky")  # nejblížší nahoře

        # Klikatelný název (markdown hyperlink)
        df["Název zakázky"] = df.apply(lambda row: f"[{row['Název zakázky']}]({row['Odkaz']})", axis=1)

        st.success(f"Načteno {len(df)} aktivních zakázek!")
        st.dataframe(
            df.drop(columns=["Odkaz"]),  # schovat holý odkaz
            column_config={
                "Název zakázky": st.column_config.TextColumn(
                    "Název zakázky",
                    help="Klikni na název pro detail zakázky",
                    unsafe_allow_html=True  # povolit hyperlink
                )
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.drop(columns=["Odkaz"]).to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny z zadaných URL.")
