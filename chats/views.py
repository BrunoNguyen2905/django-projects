from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ChatForm
from .models import ChatSession, ChatMessage
from .utils import generate_response


@login_required
def home(request):
  return render(request, 'chats/home.html')


@login_required
def new_chat(request):
  session = ChatSession.objects.create()
  return redirect('chats:chat', id=str(session.id))


@login_required
def chat_view(request, id):
  session = get_object_or_404(ChatSession, id=id)
  if request.method == 'POST':
    form = ChatForm(request.POST)
    if form.is_valid():
      user_input = form.cleaned_data['user_input']

      recent_messages = session.messages.all().order_by('-created_at')[:3][::-1]
      response = generate_response(user_input, recent_messages)
      ChatMessage.objects.create(chat_session=session, sender='human', text=user_input)
      ChatMessage.objects.create(chat_session=session, sender='ai', text=response)
      # form = ChatForm()
      chat_history = session.messages.all().order_by('created_at')
      # After successful processing, redirect with fresh form
      return redirect('chats:chat', id=str(session.id))
      # return render(request, "chats/_messages.html", {
      #   "chat_history": chat_history
      # })
  else:
    form = ChatForm()
    
  chat_history = session.messages.all().order_by('created_at')
  context = {
    'session': session,
    'form': form,
    'chat_history': chat_history
  }
  return render(request, 'chats/chat.html', context)
