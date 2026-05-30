import contextvars

# Context variables to hold active request's request object and IP address
_current_request = contextvars.ContextVar("current_request", default=None)
_current_ip = contextvars.ContextVar("current_ip", default=None)

def get_current_request():
    """Helper to fetch the active request from context."""
    return _current_request.get()

def get_current_user():
    """Helper function to fetch the active user in the signals layer."""
    request = get_current_request()
    if request:
        if hasattr(request, "user") and request.user.is_authenticated:
            return request.user
    return None

def get_current_ip():
    """Helper function to fetch the active IP address in the signals layer."""
    return _current_ip.get()

class AuditLogMiddleware:
    """
    Middleware that captures request context (request and IP address)
    and saves them in thread-safe context variables.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Set context variables for the duration of this request
        request_token = _current_request.set(request)
        ip_token = _current_ip.set(ip)
        
        try:
            response = self.get_response(request)
        finally:
            # Clean up context after request processing
            _current_request.reset(request_token)
            _current_ip.reset(ip_token)
            
        return response
