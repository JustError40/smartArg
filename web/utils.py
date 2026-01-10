import base64
from io import BytesIO
from typing import List

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt


def _figure_to_base64(fig) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    plt.close(fig)
    return encoded


def generate_pie_chart(labels: List[str], values: List[int], title: str) -> str:
    fig, ax = plt.subplots(figsize=(5, 4))
    if not labels or not values:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
        ax.axis("off")
        ax.set_title(title)
        return _figure_to_base64(fig)

    ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=140)
    ax.axis("equal")
    ax.set_title(title)
    return _figure_to_base64(fig)


def generate_bar_chart(labels: List[str], values: List[int], title: str) -> str:
    fig, ax = plt.subplots(figsize=(6, 4))
    if not labels or not values:
        ax.text(0.5, 0.5, "Нет данных", ha="center", va="center")
        ax.axis("off")
        ax.set_title(title)
        return _figure_to_base64(fig)

    ax.bar(labels, values, color="#0ea5a1")
    ax.set_title(title)
    ax.set_ylabel("Сообщения")
    ax.tick_params(axis="x", rotation=30)
    return _figure_to_base64(fig)
