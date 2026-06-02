import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import re
import pandas as pd

st.set_page_config(page_title="E-ZAK Scanner", layout="wide")
st.title("🛡️ E-ZAK Scanner")
st.markdown("**Aktivní zakázky do 50 km od Vřesové (356 01)**")

# Seznam seřazený podle vzdálenosti
urls_text = st.text_area(
    "Seznam E-ZAK URL (seřazeno od nejbližších)",
    height=420,
    value="https://ezak.sokolov.cz/contract_index.html\n"
          "https://qcm.ezak.cz/profile_display_206.html\n"
          "https://qcm.ezak.cz/profile_display_27.html?state=all&archive=ACTUAL&otype=all&contract_place=\n"
          "https://qcm.ezak.cz/profile_display_98.html\n"
          "https://ezak.kr-karlovarsky.cz/contract_index.html\n"
          "https://ezak.mmkv.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://qcm.ezak.cz/contract_index.html?type=all&state=active&archive=ACTUAL&contract_place=CZ041\n"
          "https://zakazky.ostrov.cz/contract_index.html\n"
          "https://zakazky.nejdek.cz/contract_index.html?type=all&state=all\n"
          "https://ezak.marianskelazne.cz/contract_index.html"
)

# Tabulka zadavatelů
st.subheader("📋 Seznam prohledávaných zadavatelů")
zadavatele = []
for url in urls_text.split("\n"):
    if url.strip():
        nazev = url.split("//")[1].split("/")[0].replace("www.", "").replace(".cz", "").upper()
        zadavatele.append({"Zadavatel": nazev, "URL": url.strip()})

df = pd.DataFrame(zadavatele)
st.dataframe(df, use_container_width=True, hide_index=True)

if st.button("🔄 Načíst aktivní zakázky", type="primary"):
    urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
    now = datetime.now()
    total_active = 0

    with st.spinner("Prohledávám zadavatele..."):
        progress_bar = st.progress(0)

        for idx, base_url in enumerate(urls):
            progress_bar.progress((idx + 1) / len(urls))
            
            try:
                instance_name = base_url.split("//")[1].split("/")[0].replace("www.", "").upper()

                active = []
                pages = [base_url]

                if "contract_index.html" in base_url:
                    for p in range(2, 6):
                        page_url = base_url + ("&" if "?" in base_url else "?") + f"page={p}"
                        pages.append(page_url)

                for page_url in pages:
                    try:
                        resp = requests.get(page_url, timeout=12)
                        soup = BeautifulSoup(resp.text, "lxml")

                        # Robustnější hledání zakázek
                        for a in soup.find_all("a", href=re.compile(r"contract_display_")):
                            name = a.text.strip()
                            if not name or len(name) < 5: 
                                continue
                            link = urljoin(page_url, a["href"])

                            tr = a.find_parent("tr")
                            if not tr: 
                                continue

                            tds = tr.find_all("td")
                            if len(tds) < 4: 
                                continue

                            deadline_str = tds[-1].text.strip().replace("\xa0", " ").strip()

                            if not deadline_str or deadline_str in ["-", ""]:
                                continue

                            try:
                                if ":" in deadline_str:
                                    dl = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
                                else:
                                    dl = datetime.strptime(deadline_str, "%d.%m.%Y")
                                if dl > now:
                                    active.append(f"[{name}]({link}) — lhůta {deadline_str}")
                            except:
                                continue
                    except:
                        continue

                if active:
                    st.markdown(f"### {instance_name}")
                    for item in active:
                        st.markdown(f"- {item}", unsafe_allow_html=True)
                    total_active += len(active)

            except:
                st.warning(f"{instance_name} — nepodařilo se načíst")

        progress_bar.progress(1.0)

    if total_active == 0:
        st.info("Momentálně nejsou žádné aktivní zakázky v monitorovaných zadavatelích.")
    else:
        st.success(f"Celkem nalezeno {total_active} aktivních zakázek")

st.caption("E-ZAK Scanner • Okolí Vřesové (do 50 km)")
