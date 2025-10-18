# app.py
import streamlit as st
import pandas as pd
from pipeline import analyze_texts  # pipeline.py içindeki fonksiyonlar

st.set_page_config(page_title="BIST Text Analyzer", layout="wide")

st.title("📊 BIST Text Analyzer")

st.markdown("""
Bu uygulama metinlerden BIST hisselerini, miktarını, eylemi ve sentiment'i çıkarır.
""")

user_input = st.text_area("Metinleri girin (her satır bir metin)", height=200)

company_to_ticker_map = {
    "Garanti Bankası": "GARAN",
    "Türk Hava Yolları": "THYAO",
    "Aselsan": "ASELS",
    "Sasa": "SASA",
    "Avisa": "AVISA"
}

if st.button("Analiz Et"):
    if user_input.strip() == "":
        st.warning("Lütfen analiz edilecek metinleri girin.")
    else:
        texts = [line.strip() for line in user_input.strip().split("\n") if line.strip()]
        df_results = analyze_texts(texts, company_to_ticker=company_to_ticker_map)
        if df_results.empty:
            st.info("Metinlerde ticker bulunamadı.")
        else:
            st.subheader("📈 Analiz Sonuçları")
            st.dataframe(df_results)

            # Sentiment grafiği
            st.subheader("Sentiment Dağılımı")
            sentiment_counts = df_results['sentiment'].value_counts()
            st.bar_chart(sentiment_counts)
