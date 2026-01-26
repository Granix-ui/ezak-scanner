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
    total_contracts = 0
    total_active = 0
    now = datetime.now()

    with st.spinner("Načítám data (včetně paginace)..."):
        for base_url in urls:
            pages_to_scrape = [base_url]

            # Detekce a přidání paginace pro contract_index
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
                            st.info(f"Na {base_url}: Paginace na {max_page} stránek – načtu všechny.")
                            for p in range(2, max_page + 1):
                                page_url = re.sub(r"page=\d+", f"page={p}", base_url)
                                if "page=" not in page_url:
                                    page_url = base_url + ("&" if "?" in base_url else "?") + f"page={p}"
                                pages_to_scrape.append(page_url)
                except:
                    pass

            url_contracts = 0
            url_active = 0

            for page_url in pages_to_scrape:
                try:
                    response = requests.get(page_url, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "lxml")

                    # Najdi všechny odkazy na zakázky
                    contract_links = soup.find_all("a", href=re.compile(r"contract_display_"))

                    st.info(f"Na {page_url}: Nalezeno {len(contract_links)} zakázek (odkazů).")

                    for a in contract_links:
                        name = a.text.strip()
                        if not name:
                            continue
                        link = urljoin(page_url, a["href"])

                        # Najdi rodičovský tr a následující 2 tr pro zadavatele a detaily
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

                        url_contracts += 1

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

            st.info(f"Na {base_url} (celkem): Zpracováno {url_contracts} zakázek, aktivních {url_active}.")

            total_contracts += url_contracts
            total_active += url_active

        st.info(f"Celkem přes všechny: Zpracováno {total_contracts} zakázek, aktivních {total_active}.")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")

        st.success(f"Zobrazeno {len(df)} aktivních zakázek!")
        st.dataframe(
            df,
            column_config={
                "Název zakázky": st.column_config.LinkColumn("Název zakázky"),
                "Odkaz": None
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky nenalezeny.")
