# web/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')

def get_websocket_application():
    from apps.chat.consumers import ChatConsumer  # <-- import اینجا انجام میشه
    return AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/', ChatConsumer.as_asgi()),
        ])
    )

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': get_websocket_application(),
})