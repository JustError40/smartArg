from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Count, Q

from analysis.models import AnalysisResult, KnowledgeEntry, CourseTask
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
    status = request.GET.get("status", "active")
    task_type = request.GET.get("type", "")

    tasks = CourseTask.objects.order_by("-updated_at")
    
    if status == 'active':
        tasks = tasks.filter(status='active')
    elif status == 'completed':
        tasks = tasks.filter(status='completed')
    elif status == 'cancelled':
        tasks = tasks.filter(status='cancelled')
    
    if task_type:
        tasks = tasks.filter(task_type=task_type)

    context = {
        "tasks": tasks,
        "selected_status": status,
        "selected_type": task_type,
        "task_types": CourseTask.TASK_TYPES,
        "statuses": CourseTask.STATUSES,
    }
    return render(request, "knowledge_base.html", context)

def task_detail(request, task_id):
    task = get_object_or_404(CourseTask, id=task_id)
    
    # Get all entries related to this task
    entries = task.entries.select_related('source_message__chat').order_by('created_at')
    
    deadlines = entries.filter(entry_type='deadline')
    links = entries.filter(entry_type='link')
    explanations = entries.filter(entry_type='explanation')
    generic_info = entries.filter(entry_type__in=['generic', 'info'])
    
    context = {
        "task": task,
        "deadlines": deadlines,
        "links": links,
        "explanations": explanations,
        "generic_info": generic_info
    }
    return render(request, "task_detail.html", context)
