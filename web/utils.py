import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import pandas as pd
from analysis.models import AnalysisResult

def generate_category_chart():
    """
    Generates a base64 encoded pie chart of message categories.
    """
    # 1. Fetch data
    data = list(AnalysisResult.objects.values('category'))
    if not data:
        return None

    df = pd.DataFrame(data)
    category_counts = df['category'].value_counts()

    # 2. Create Plot
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title("Распределение категорий сообщений")

    # 3. Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)

    # 4. Encode
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return image_base64
