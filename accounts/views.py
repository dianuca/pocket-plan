from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render

from .forms import LoginForm


def login_page(request):
    if request.method == "POST":
        form = LoginForm(data=request.POST)

        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )

            if user is not None:
                login(request, user)
                return redirect("monthly-summary")

            form.add_error(
                None,
                "Utilizator sau parolă incorectă.",
            )
    else:
        form = LoginForm()

    return render(
        request,
        "registration/login.html",
        {"form": form},
    )

@require_POST
def logout_page(request):
    logout(request)
    return redirect("login")