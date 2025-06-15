import os
from django.core.asgi import get_asgi_application

# This line MUST be at the top
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrimonial.settings')

# This line is the KEY. It initializes Django *before* other imports.
django_asgi_app = get_asgi_application() 

# Now that Django is ready, we can safely import our app's code.
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import matri.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app, # Use the app instance we already created
    "websocket": AuthMiddlewareStack(
        URLRouter(
            matri.routing.websocket_urlpatterns
        )
    ),
})