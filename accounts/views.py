from django.shortcuts import render

from .forms import LoginForm


def login_page(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)
        form.is_valid()
    else:
        form = LoginForm()

    return render(
        request,
        "registration/login.html",
        {"form": form},
    )