import logging
import time
from django.utils.deprecation import MiddlewareMixin
import json

logger = logging.getLogger("judge.request")


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Logs each request with timing, client IP, path, method, query params,
    body info, and response status code.
    """

    def process_request(self, request):
        request._start_time = time.time()

        # Read and store the body content for logging before it gets consumed
        # But only do this for methods that typically have bodies
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                # Store the raw body for later use in process_response
                request._raw_body = request.body
            except Exception:
                # If we can't read the body, set it to empty
                request._raw_body = b""

    def process_response(self, request, response):
        duration = (time.time() - getattr(request, "_start_time", time.time()))
        client_ip = request.META.get("REMOTE_ADDR", "unknown")
        method = request.method
        path = request.path
        qs = request.META.get("QUERY_STRING", "")
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:200]

        # Handle body info carefully to avoid accessing consumed streams
        body_info = {}
        try:
            # Try to get data from request (already parsed)
            data = {}
            if hasattr(request, 'data'):
                data = request.data
            elif request.method == 'POST':
                # For form data
                data = request.POST.dict() if request.POST else {}

            # Check for sentence1/sentence2 in the parsed data
            s1 = data.get("sentence1")
            s2 = data.get("sentence2")

            if s1 or s2:
                body_info = {"s1": s1, "s2": s2}
            else:
                # For other cases, use the raw body we stored earlier
                raw_body = getattr(request, '_raw_body', b"")
                if raw_body:
                    try:
                        # Try to parse as JSON to see if it contains our expected fields
                        json_data = json.loads(raw_body.decode('utf-8'))
                        if 'sentence1' in json_data or 'sentence2' in json_data:
                            s1 = json_data.get("sentence1")
                            s2 = json_data.get("sentence2")
                            body_info = {'s1': s1, 's2': s2}
                        else:
                            body_info = {"body_present": True, "body_len": len(raw_body)}
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body_info = {"body_present": True, "body_len": len(raw_body)}
                else:
                    body_info = {"body_present": False, "body_len": 0}

        except Exception as e:
            # Fallback: try to use the stored raw body
            try:
                raw_body = getattr(request, '_raw_body', b"")
                body_info = {"body_present": bool(raw_body), "body_len": len(raw_body), "error": str(e)}
            except Exception:
                body_info = {"body_error": "Could not process body"}

        status_code = getattr(response, "status_code", None)
        log_entry = {
            "client_ip": client_ip,
            "method": method,
            "path": path,
            "query": qs,
            "status": status_code,
            "duration_s": round(duration, 4),
            "user_agent": user_agent,
            "body_info": body_info,
        }
        logger.info(log_entry)
        return response