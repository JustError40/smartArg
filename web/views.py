from django.db.models import Avg, Count, Q
from django.shortcuts import render

from analysis.models import AnalysisResult, KnowledgeEntry
from core.models import Chat, Message
from .utils import generate_bar_chart, generate_pie_chart

def dashboard(request):
    total_messages = Message.objects.count()
    total_knowledge = KnowledgeEntry.objects.count()
    avg_importance = (
        AnalysisResult.objects.aggregate(avg=Avg("importance_score")).get("avg") or 0
    )

    recent_alerts = (
        AnalysisResult.objects.select_related("message", "message__chat")
        .filter(Q(importance_score__gte=6) | Q(category__in=["deadline", "announcement"]))
        .order_by("-message__sent_at")[:6]
    )

    category_counts = (
        AnalysisResult.objects.values("category")
        .annotate(total=Count("id"))
        .order_by()
    )
    category_labels = [item["category"] for item in category_counts]
    category_values = [item["total"] for item in category_counts]

    chat_counts = (
        Message.objects.values("chat__title", "chat__tg_chat_id")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )
    chat_labels = [
        item["chat__title"] or f"Чат {item['chat__tg_chat_id']}" for item in chat_counts
    ]
    chat_values = [item["total"] for item in chat_counts]

    pie_chart = generate_pie_chart(
        category_labels, category_values, "Распределение категорий сообщений"
    )
    bar_chart = generate_bar_chart(
        chat_labels, chat_values, "Активность по чатам"
    )

    context = {
        "total_messages": total_messages,
        "total_knowledge": total_knowledge,
        "avg_importance": round(avg_importance, 2),
        "recent_alerts": recent_alerts,
        "pie_chart": pie_chart,
        "bar_chart": bar_chart,
    }
    return render(request, "dashboard.html", context)


def chat_list(request):
    chats = (
        Chat.objects.annotate(message_count=Count("messages"))
        .order_by("-message_count", "title")
    )
    context = {"chats": chats}
    return render(request, "chat_list.html", context)


def knowledge_base(request):
    entry_type = request.GET.get("entry_type", "")
    chat_id = request.GET.get("chat", "")

    entries = KnowledgeEntry.objects.select_related("source_message__chat").order_by("-created_at")
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    if chat_id:
        entries = entries.filter(source_message__chat_id=chat_id)

    context = {
        "entries": entries,
        "entry_types": KnowledgeEntry.ENTRY_TYPES,
        "chats": Chat.objects.all().order_by("title"),
        "selected_entry_type": entry_type,
        "selected_chat": chat_id,
    }
    return render(request, "knowledge_base.html", context)
