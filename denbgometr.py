# amazon_profit_app.py
import streamlit as st
import pandas as pd
import math
from io import StringIO

# --- Константы ---
CNY_TO_JPY = 22.15
MIN_KG = 1
MAX_KG = 20

st.set_page_config(page_title="Выгодностеметр", page_icon="💰", layout="wide")
st.title("💰 Выгодностеметр")

# ---- Sidebar: ввод ----
st.sidebar.header("Входные параметры")

is_electronic = st.sidebar.checkbox("Электронный товар", value=False,
                                    help="Отметь, если товар — электроника (другие тарифы доставки).")

amazon_price_jpy = st.sidebar.number_input("Цена продажи на Amazon (¥)", min_value=0.0, value=1980.0, step=10.0)
weight_per_item_g = st.sidebar.number_input("Вес одной единицы (г)", min_value=1.0, value=300.0, step=10.0)
amazon_fee_jpy = st.sidebar.number_input("Комиссия Amazon (¥)", min_value=0.0, value=300.0, step=10.0)
supplier_price_cny = st.sidebar.number_input("Цена у поставщика (CNY)", min_value=0.0, value=20.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.write(f"Курс: **1 CNY = {CNY_TO_JPY} ¥** (жёстко задано)")
st.sidebar.caption("Программа рассчитывает варианты для партий с общим весом от 1 до 20 кг.")

# ---- Преобразования ----
weight_per_item_kg = weight_per_item_g / 1000.0
supplier_price_jpy = supplier_price_cny * CNY_TO_JPY

# ---- Тариф доставки ----
def shipping_cny_for_kg(k_kg: int, electronic: bool) -> float:
    if k_kg < 1:
        k_kg = 1
    if electronic:
        return 190 + 40 * (k_kg - 1)
    else:
        return 75 + 20 * (k_kg - 1)

# ---- Расчёт ----
rows = []
for total_kg in range(MIN_KG, MAX_KG + 1):
    if weight_per_item_kg <= 0:
        quantity = 0
    else:
        quantity = math.floor(total_kg / weight_per_item_kg)

    ship_cny = shipping_cny_for_kg(total_kg, is_electronic)
    ship_jpy = ship_cny * CNY_TO_JPY

    if quantity >= 1:
        ship_jpy_per_item = ship_jpy / quantity
        cost_per_item = supplier_price_jpy + ship_jpy_per_item + amazon_fee_jpy
        profit_per_item = amazon_price_jpy - cost_per_item
        total_profit = profit_per_item * quantity
        profit_percent = (profit_per_item / amazon_price_jpy * 100.0) if amazon_price_jpy != 0 else 0.0
        status = "✅ Выгодно" if profit_per_item > 0 else "❌ Невыгодно"
    else:
        ship_jpy_per_item = None
        cost_per_item = None
        profit_per_item = None
        total_profit = None
        profit_percent = None
        status = "— Невозможно (0 шт)"

    rows.append({
        "Партия, кг": total_kg,
        "Кол-во шт": quantity,
        "Доставка (CNY)": ship_cny,
        "Доставка (¥)": round(ship_jpy, 2),
        "Доставка на 1 шт (¥)": round(ship_jpy_per_item, 2) if ship_jpy_per_item else "—",
        "Себестоимость 1 шт (¥)": round(cost_per_item, 2) if cost_per_item else "—",
        "Маржа (¥) на 1 шт": round(profit_per_item, 2) if profit_per_item else "—",
        "Маржа %": round(profit_percent, 2) if profit_percent else "—",
        "Общая маржа (¥)": round(total_profit, 2) if total_profit else "—",
        "Статус": status
    })

df = pd.DataFrame(rows)

# ---- Оптимальная партия ----
valid_df = df[df["Кол-во шт"] >= 1].copy()
if not valid_df.empty:
    optimal_idx = valid_df["Общая маржа (¥)"].astype(float).idxmax()
    optimal_row = df.loc[optimal_idx]
    optimal_kg = int(optimal_row["Партия, кг"])
else:
    optimal_row = None
    optimal_kg = None

# ---- Таблица ----
def highlight_optimal(row):
    if optimal_kg is not None and row["Партия, кг"] == optimal_kg:
        return ['background-color: #d7f4d7'] * len(row)
    return [''] * len(row)

styled = df.style.apply(highlight_optimal, axis=1)
st.dataframe(styled, use_container_width=True)

st.markdown("---")

# ---- Оптимальный вариант ----
if optimal_row is not None:
    st.markdown("## ✅ Оптимальный вариант (макс. общая маржа)")
    st.write(f"**Партия:** {optimal_row['Партия, кг']} kg")
    st.write(f"**Количество:** {int(optimal_row['Кол-во шт'])} шт")
    st.write(f"**Доставка (¥):** {optimal_row['Доставка (¥)']:.2f}")
    st.write(f"**Себестоимость 1 шт (¥):** {optimal_row['Себестоимость 1 шт (¥)']:.2f}")
    st.write(f"**Маржа на 1 шт (¥):** {optimal_row['Маржа (¥) на 1 шт']:.2f}")
    st.write(f"**Общая маржа (¥):** {optimal_row['Общая маржа (¥)']:.2f}")
else:
    st.info("Ни в одной партии не удалось разместить хотя бы одну единицу товара.")

# ---- CSV ----
csv_buffer = StringIO()
df.to_csv(csv_buffer, index=False)
csv_bytes = csv_buffer.getvalue().encode('utf-8')

st.download_button(
    label="⬇️ Скачать таблицу (CSV)",
    data=csv_bytes,
    file_name="amazon_profit_by_weight.csv",
    mime="text/csv"
)
