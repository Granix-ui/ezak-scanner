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

urls_text = st.text_area(
    "Seznam E-ZAK URL (seřazeno od nejbližších)",
    height=380,
    value="https://ezak.sokolov.cz/contract_index.html\n"
          "https://ezak.kr-karlovarsky.cz/contract_index.html\n"
          "https://ezak.mmkv.cz/contract_index.html?type=all&state=all&archive=ACTUAL&contract_place=CZ041\n"
          "https://qcm.ezak.cz/profile_display_206.html\n"
          "https://qcm.ezak.cz/profile_display_27.html?state=all&archive=ACTUAL&otype=all&contract_place=\n"
          "https://qcm.ezak.cz/profile_display_98.html"
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
            instance_name = base_url.split("//")[1].split("/")[0].replace("www.", "").upper()

            try:
                active = []
                pages = [base_url]

                if "contract_index.html" in base_url:
                    for p in range(2, 8):
                        page_url = base_url + ("&" if "?" in base_url else "?") + f"page={p}"
                        pages.append(page_url)

                for page_url in pages:
                    try:
                        resp = requests.get(page_url, timeout=15)
                        soup = BeautifulSoup(resp.text, "lxml")

                        # Nejrobustnější způsob - hledáme všechny contract_display
                        for a in soup.find_all("a", href=re.compile(r"contract_display_")):
                            name = a.text.strip()
                            if len(name) < 10: 
                                continue
                            link = urljoin(page_url, a["href"])

                            # Najdeme řádek s daty (lhůta je obvykle v posledním sloupci)
                            tr = a.find_parent("tr")
                            if tr:
                                tds = tr.find_all("td")
                                if len(tds) >= 4:
                                    deadline_str = tds[-1].text.strip().replace("\xa0", " ")

                                    if deadline_str and deadline_str != "-":
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

            except Exception:
                st.warning(f"{instance_name} — chyba načtení")

        progress_bar.progress(1.0)

    if total_active == 0:
        st.info("Momentálně nejsou žádné aktivní zakázky v monitorovaných zadavatelích.")
    else:
        st.success(f"Celkem nalezeno {total_active} aktivních zakázek")

st.caption("E-ZAK Scanner • Okolí Vřesové (do 50 km)")
