import time
from django.shortcuts import redirect

class PerformanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()

        response = self.get_response(request)

        duration = time.time() - start
        print("---------------------------")
        print(f"{request.path} took {duration:.2f}sec")
        print("---------------------------")

        return response 


class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and request.path != '/login/':
            return redirect('login')

        return self.get_response(request)

