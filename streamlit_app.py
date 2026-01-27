import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs
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
    total_active = 0
    now = datetime.now()

    with st.spinner("Načítám data..."):
        for base_url in urls:
            pages_to_scrape = [base_url]

            if "contract_index.html" in base_url:
                try:
                    response = requests.get(base_url, timeout=15)
                    soup = BeautifulSoup(response.text, "lxml")
                    pagination = soup.find("div", class_=re.compile(r"pagination", re.I))
                    if pagination:
                        links = pagination.find_all("a", href=True)
                        max_page = 1
                        for link in links:
                            href = link["href"]
                            if "page=" in href:
                                try:
                                    page_num = int(parse_qs(urlparse(href).query)["page"][0])
                                    max_page = max(max_page, page_num)
                                except:
                                    pass
                        if max_page > 1:
                            for p in range(2, max_page + 1):
                                page_url = re.sub(r"page=\d+", f"page={p}", base_url)
                                if "page=" not in page_url:
                                    page_url = base_url + ("&" if "?" in base_url else "?") + f"page={p}"
                                pages_to_scrape.append(page_url)
                except:
                    pass

            url_active = 0

            for page_url in pages_to_scrape:
                try:
                    response = requests.get(page_url, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "lxml")

                    contract_links = soup.find_all("a", href=re.compile(r"contract_display_"))

                    for a in contract_links:
                        name = a.text.strip()
                        if not name:
                            continue
                        link = urljoin(page_url, a["href"])

                        current_tr = a.find_parent("tr")
                        if not current_tr:
                            continue

                        next_trs = current_tr.find_next_siblings("tr", limit=2)
                        if len(next_trs) < 2:
                            continue

                        zadavatel_tr = next_trs[0]
                        details_tr = next_trs[1]

                        zadavatel = zadavatel_tr.get_text(separator=" ", strip=True).strip("_ ").strip()

                        details_tds = details_tr.find_all("td")
                        if len(details_tds) < 4:
                            continue

                        start_str = details_tds[-2].text.strip()
                        deadline_str = details_tds[-1].text.strip().replace("\xa0", " ")

                        if not deadline_str or deadline_str in ["-", ""]:
                            continue

                        try:
                            deadline_clean = re.sub(r"\s+", " ", deadline_str).strip()
                            if ":" in deadline_clean:
                                deadline = datetime.strptime(deadline_clean, "%d.%m.%Y %H:%M")
                            else:
                                deadline = datetime.strptime(deadline_clean, "%d.%m.%Y")
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

                except Exception as e:
                    st.warning(f"Chyba na {page_url}: {e}")

            if url_active > 0:
                st.info(f"Na {base_url}: Aktivních {url_active} zakázek.")

            total_active += url_active

        if total_active > 0:
            st.info(f"Celkem aktivních: {total_active} zakázek.")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")

        # Klikatelný název markdownem
        df["Název zakázky"] = df.apply(lambda row: f'<a href="{row["Odkaz"]}">{row["Název zakázky"]}</a>', axis=1)

        st.success(f"Zobrazeno {len(df)} aktivních zakázek!")
        st.dataframe(
            df.drop(columns=["Odkaz"]),
            column_config={
                "Název zakázky": st.column_config.TextColumn(
                    "Název zakázky",
                    help="Klikni na název pro detail",
                    unsafe_allow_html=True
                )
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.drop(columns=["Odkaz"]).to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny.")
