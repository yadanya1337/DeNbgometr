# amazon_profit_app.py
import streamlit as st
import pandas as pd
import math
from io import StringIO

# --- Константы ---
CNY_TO_JPY = 22.15
MIN_KG = 1
MAX_KG = 20

st.set_page_config(page_title="Amazon Profit & Optimal Weight", page_icon="💰", layout="wide")
st.title("💰 Калькулятор выгодности товара (Amazon Japan)")

# ---- Sidebar: ввод ----
st.sidebar.header("Входные параметры")

is_electronic = st.sidebar.checkbox("Электронный товар", value=False,
                                    help="Отметь, если товар — электроника (другие тарифы доставки).")

amazon_price_jpy = st.sidebar.number_input("Цена продажи на Amazon (¥)", min_value=0.0, value=1980.0, step=10.0)
weight_per_item_g = st.sidebar.number_input("Вес одной единицы (г)", min_value=1.0, value=300.0, step=10.0)
amazon_fee_percent = st.sidebar.number_input("Комиссия Amazon (%)", min_value=0.0, value=15.0, step=0.5)
supplier_price_cny = st.sidebar.number_input("Цена у поставщика (CNY)", min_value=0.0, value=20.0, step=0.1)

st.sidebar.markdown("---")
st.sidebar.write(f"Курс: **1 CNY = {CNY_TO_JPY} ¥** (жёстко задано)")
st.sidebar.caption("Программа рассчитывает варианты для партий с общим весом от 1 до 20 кг.")

# ---- Валидация / преобразования ----
weight_per_item_kg = weight_per_item_g / 1000.0
supplier_price_jpy = supplier_price_cny * CNY_TO_JPY
amazon_fee_jpy = amazon_price_jpy * (amazon_fee_percent / 100.0)

# ---- Функция расчёта тарифа доставки (в CNY) для заданного целого k кг ----
def shipping_cny_for_kg(k_kg: int, electronic: bool) -> float:
    if k_kg < 1:
        k_kg = 1
    if electronic:
        # электроника: 1 kg = 190, +40 за каждый следующий
        return 190 + 40 * (k_kg - 1)
    else:
        # неэлектроника: 1 kg = 75, +20 за каждый следующий
        return 75 + 20 * (k_kg - 1)

# ---- Собираем данные по партиям 1..20 kg ----
rows = []
for total_kg in range(MIN_KG, MAX_KG + 1):
    # сколько целых единиц товара поместится в партию этого веса?
    # используем floor(total_kg / weight_per_item_kg)
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
        status = "✅ Выгодно" if profit_per_item > 0 else "❌ Не выгодно"
    else:
        # партия слишком мала, чтобы положить хоть 1 товар
        ship_jpy_per_item = None
        cost_per_item = None
        profit_per_item = None
        total_profit = None
        profit_percent = None
        status = "— Невозможно (0 шт)"

    rows.append({
        "Партия, кг": total_kg,
        "Кол-во шт в партии": quantity,
        "Доставка (CNY)": ship_cny,
        "Доставка (¥)": round(ship_jpy, 0),
        "Доставка на 1 шт (¥)": (round(ship_jpy_per_item, 0) if ship_jpy_per_item is not None else "—"),
        "Себестоимость 1 шт (¥)": (round(cost_per_item, 0) if cost_per_item is not None else "—"),
        "Маржа (¥) на 1 шт": (round(profit_per_item, 0) if profit_per_item is not None else "—"),
        "Маржа %": (round(profit_percent, 2) if profit_percent is not None else "—"),
        "Общая маржа (¥)": (round(total_profit, 0) if total_profit is not None else "—"),
        "Статус": status
    })

df = pd.DataFrame(rows)

# ---- Находим оптимальную партию (максимальная общая маржа) ----
# Рассматриваем только те строки, где "Кол-во шт в партии" >= 1
valid_df = df[df["Кол-во шт в партии"] >= 1].copy()
if not valid_df.empty:
    # выбрать max по "Общая маржа (¥)"
    # превратим знак "—" в NaN заранее не нужно, потому что мы отфильтровали
    optimal_idx = valid_df["Общая маржа (¥)"].astype(float).idxmax()
    optimal_row = df.loc[optimal_idx]
    optimal_kg = int(optimal_row["Партия, кг"])
else:
    optimal_idx = None
    optimal_row = None
    optimal_kg = None

# ---- Отображение результатов ----
st.markdown("## Вводные данные")
col1, col2, col3 = st.columns([1,1,1])
with col1:
    st.write(f"**Цена на Amazon:** {amazon_price_jpy:.0f} ¥")
    st.write(f"**Комиссия Amazon:** {amazon_fee_percent:.2f} % → {amazon_fee_jpy:.0f} ¥")
with col2:
    st.write(f"**Цена поставщика:** {supplier_price_cny:.2f} CNY → {supplier_price_jpy:.0f} ¥")
    st.write(f"**Вес 1 шт:** {weight_per_item_g:.0f} г → {weight_per_item_kg:.3f} кг")
with col3:
    st.write(f"**Тип доставки:** {'Электронный (190+40)' if is_electronic else 'Неэлектронный (75+20)'}")
    st.write(f"**Курс:** 1 CNY = {CNY_TO_JPY} ¥")

st.markdown("---")

# ---- Показываем таблицу и подсветку оптимальной строки ----
st.markdown("## Результат: варианты по общей массе партии (1–20 kg)")

# Подготовим стили: подсветим оптимальную строку зелёным
def highlight_optimal(row):
    if optimal_kg is not None and row["Партия, кг"] == optimal_kg:
        return ['background-color: #d7f4d7'] * len(row)
    return [''] * len(row)

# Отобразим таблицу со стилями
styled = df.style.apply(highlight_optimal, axis=1)
# Ограничим ширину столбцов для читаемости
styled.format({
    "Доставка (CNY)": "{:.0f}",
    "Доставка (¥)": "{:.0f}",
    "Доставка на 1 шт (¥)": lambda v: v if v == "—" else f"{int(v):,}",
    "Себестоимость 1 шт (¥)": lambda v: v if v == "—" else f"{int(v):,}",
    "Маржа (¥) на 1 шт": lambda v: v if v == "—" else f"{int(v):,}",
    "Маржа %": lambda v: v if v == "—" else f"{v:.2f}%",
    "Общая маржа (¥)": lambda v: v if v == "—" else f"{int(v):,}",
})

st.dataframe(styled, use_container_width=True)

st.markdown("---")

# ---- Подробный блок с оптимальной партией ----
if optimal_row is not None:
    st.markdown("## ✅ Оптимальный вариант (максимальная общая маржа)")
    st.write(f"**Партия:** {optimal_row['Партия, кг']} kg")
    st.write(f"**Кол-во в партии:** {int(optimal_row['Кол-во шт в партии'])} шт")
    st.write(f"**Доставка (¥) за партию:** {int(optimal_row['Доставка (¥)']):,} ¥")
    st.write(f"**Доставка на 1 шт (¥):** {optimal_row['Доставка на 1 шт (¥)']:,} ¥")
    st.write(f"**Себестоимость 1 шт (¥):** {int(optimal_row['Себестоимость 1 шт (¥)']):,} ¥")
    st.write(f"**Маржа на 1 шт (¥):** {int(optimal_row['Маржа (¥) на 1 шт']):,} ¥")
    st.write(f"**Маржа %:** {optimal_row['Маржа %']} %")
    st.write(f"**Общая маржа (¥):** {int(optimal_row['Общая маржа (¥)']):,} ¥")
else:
    st.info("Ни в одной партии 1–20 kg не удалось разместить хотя бы одну единицу товара (введён слишком большой вес одной вещи).")

st.markdown("---")

# ---- Кнопка скачивания CSV ----
csv_buffer = StringIO()
df.to_csv(csv_buffer, index=False)
csv_bytes = csv_buffer.getvalue().encode('utf-8')

st.download_button(
    label="⬇️ Скачать таблицу (CSV)",
    data=csv_bytes,
    file_name="amazon_profit_by_weight.csv",
    mime="text/csv"
)

st.caption("Примечания: \
- Количество товаров в партии = floor(общий вес партии (kg) / вес одной единицы (kg)). \
- Стоимость доставки рассчитывается для всей партии (1..20 kg) и затем делится на количество единиц. \
- Если в партию не помещается ни одной единицы, строка помечена как невозможная.")
