import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
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
          "https://qcm.ezak.cz/contract_index.html?type=all&state=active&archive=ACTUAL&contract_place=CZ041\n"
          "https://qcm.ezak.cz/profile_display_186.html\n"
          "https://qcm.ezak.cz/profile_display_12.html\n"
          "https://zakazky.cheb.cz/contract_index.html\n"
          "https://zakazky.ostrov.cz/contract_index.html\n"
          "https://qcm.ezak.cz/profile_display_13.html\n"
          "https://zakazky.nejdek.cz/contract_index.html?type=all&state=all\n"
          "https://zakazky.chomutov.cz/contract_index.html\n"
          "https://zakazky.muml.cz/contract_index.html\n"
          "https://qcm.ezak.cz/profile_display_18.html\n"
          "https://ezak.tendera.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.spravazeleznic.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.hornislavkov.cz/contract_index.html\n"
          "https://zakazky.kzcr.eu/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://mfcr.ezak.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.spucr.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://ezak.mzp.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.eagri.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://mpsv.ezak.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.rpa.cz/contract_index.html?type=all&state=active&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.zcu.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.tachov-mesto.cz/contract_index.html\n"
          "https://ezak.vscr.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://smart.ezak.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://ezak.marianskelazne.cz/contract_index.html\n"
          "https://ezak.as.cz/contract_index.html"
)

if st.button("Načíst čerstvá data"):
    urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
    if not urls:
        st.error("Zadej alespoň jednu URL!")
        st.stop()

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

            # Název instance z title base_url
            try:
                base_response = requests.get(base_url, timeout=15)
                base_soup = BeautifulSoup(base_response.text, "lxml")
                page_title = base_soup.title.text.strip() if base_soup.title else ""
                instance_name = page_title.split("-")[-1].strip() if "-" in page_title else base_url.split("//")[1].split("/")[0]
            except:
                instance_name = base_url.split("//")[1].split("/")[0]

            active_links = []

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

                        details_tr = next_trs[1]
                        details_tds = details_tr.find_all("td")
                        if len(details_tds) < 4:
                            continue

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
                                active_links.append(f"[{name}]({link})")
                        except ValueError:
                            continue

                except:
                    pass

            st.markdown(f"### {instance_name}")

            if active_links:
                for link in active_links:
                    st.markdown(f"- {link}", unsafe_allow_html=True)
            else:
                st.markdown("Nic nenalezeno")
