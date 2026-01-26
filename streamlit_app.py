import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from urllib.parse import urljoin, urlparse, parse_qs

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
    total_rows = 0
    total_contracts = 0
    total_active = 0
    now = datetime.now()

    with st.spinner("Načítám data (včetně paginace, pokud je)..."):
        for base_url in urls:
            pages_to_scrape = [base_url]
            try:
                # Detekce paginace (jen pro contract_index varianty)
                if "contract_index.html" in base_url:
                    response = requests.get(base_url, timeout=15)
                    soup = BeautifulSoup(response.text, "lxml")
                    pagination_links = soup.find_all("a", href=True)
                    max_page = 1
                    for link in pagination_links:
                        href = link["href"]
                        if "page=" in href:
                            try:
                                page_num = int(parse_qs(urlparse(href).query).get("page", [1])[0])
                                max_page = max(max_page, page_num)
                            except:
                                pass
                    if max_page > 1:
                        st.info(f"Na {base_url}: Detekována paginace na {max_page} stránek – načtu všechny.")
                        for p in range(2, max_page + 1):
                            page_url = base_url + (("&" if "?" in base_url else "?") + f"page={p}")
                            pages_to_scrape.append(page_url)
            except:
                pass

            url_rows = 0
            url_contracts = 0
            url_active = 0

            for page_url in pages_to_scrape:
                try:
                    response = requests.get(page_url, timeout=15)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "lxml")

                    table = soup.find("table")
                    if not table:
                        continue

                    rows = table.find_all("tr")[1:]
                    url_rows += len(rows)
                    st.info(f"Na {page_url}: Načteno {len(rows)} řádků.")

                    for row in rows:
                        tds = row.find_all("td")
                        if len(tds) < 4:
                            continue

                        name_tag = tds[0].find("a", href=True)
                        if not name_tag or "contract_display_" not in name_tag["href"]:
                            continue

                        name = name_tag.text.strip()
                        link = urljoin(page_url, name_tag["href"])

                        zadavatel = tds[1].get_text(separator=" ", strip=True) if len(tds) > 1 else "Neznámý"

                        start_str = tds[-2].text.strip() if len(tds) >= 5 else "Neuvedeno"

                        deadline_str = tds[-1].get_text(separator=" ", strip=True).replace("\xa0", " ").strip()

                        if not deadline_str or deadline_str in ["-", ""]:
                            continue

                        url_contracts += 1

                        try:
                            if ":" in deadline_str:
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

                except Exception as e:
                    st.warning(f"Chyba na {page_url}: {e}")

            st.info(f"Na {base_url} (včetně stránek): Řádků {url_rows}, zakázek {url_contracts}, aktivních {url_active}.")

            total_rows += url_rows
            total_contracts += url_contracts
            total_active += url_active

        st.info(f"Celkem: Řádků {total_rows}, zakázek {total_contracts}, aktivních {total_active}.")

    if data:
        df = pd.DataFrame(data)
        df = df.sort_values("Lhůta pro nabídky")

        st.success(f"Zobrazeno {len(df)} aktivních zakázek!")
        st.dataframe(
            df,
            column_config={
                "Název zakázky": st.column_config.LinkColumn("Název zakázky", display_text=df["Název zakázky"]),
                "Odkaz": None
            },
            hide_index=True,
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Stáhnout jako CSV", csv, "aktivni_zakazky.csv", "text/csv")
    else:
        st.info("Žádné aktivní zakázky (viz debug výše).")
