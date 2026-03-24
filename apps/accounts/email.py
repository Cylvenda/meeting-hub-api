from djoser import email


class CustomActivationEmail(email.ActivationEmail):
    template_name = "email/activation.html"

    def get_context_data(self):
        context = super().get_context_data()
        context["site_name"] = "Meeting Hub"
        return context
