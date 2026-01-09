from django.shortcuts import render
from core.models import Chat, Message
from analysis.models import KnowledgeEntry
from .utils import generate_category_chart

def dashboard(request):
    total_messages = Message.objects.count()
    total_chats = Chat.objects.count()
    total_entries = KnowledgeEntry.objects.count()

    # Recent important entries
    recent_entries = KnowledgeEntry.objects.order_by('-created_at')[:5]

    # Chart
    category_chart = generate_category_chart()

    context = {
        'total_messages': total_messages,
        'total_chats': total_chats,
        'total_entries': total_entries,
        'recent_entries': recent_entries,
        'category_chart': category_chart
    }
    return render(request, 'dashboard.html', context)

def chat_list(request):
    chats = Chat.objects.all().order_by('-created_at')
    return render(request, 'chat_list.html', {'chats': chats})

def knowledge_base(request):
    entries = KnowledgeEntry.objects.all().order_by('-created_at')

    # Filter
    entry_type = request.GET.get('type')
    if entry_type:
        entries = entries.filter(entry_type=entry_type)

    return render(request, 'knowledge_base.html', {'entries': entries})
