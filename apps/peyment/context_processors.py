def membership_status_context(request):
    is_pay = False

    if request.user.is_authenticated:
        from apps.user.models import UserSecurity

        is_pay = (
            UserSecurity.objects
            .filter(user=request.user)
            .values_list("isPeymentuser", flat=True)
            .first()
            or False
        )

    return {
        "is_pay": bool(is_pay),
    }