from django.http import JsonResponse


def home_page(request):
    return JsonResponse(
        {
            "message": "This is the django implementation of the Question Generation Project"
        }
    )
