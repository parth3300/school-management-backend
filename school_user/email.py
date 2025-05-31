from djoser import email
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives

class ActivationEmail(email.ActivationEmail):
    template_name = 'school_user/activation.html'
    def send(self, to):
        context = self.get_context_data()

        # ✅ Make sure all values are ready before rendering
        context['school_name'] = context['user'].school.name
        context['activation_url'] = f"{context['protocol']}://{context['domain']}/school_management/users{context['url']}/"

        subject = f"Activate your account at {context['school_name']}"
        html_message = render_to_string(self.template_name, context)
        plain_message = strip_tags(html_message)

        print("\n📨 Activation Email (HTML):\n", html_message)
        print("📄 Activation Email (Plain Text):\n", plain_message)
        print("✅ X Context:", context)

        # ✅ Actually send email using EmailMultiAlternatives
        email = EmailMultiAlternatives(subject, plain_message, to=to)
        email.attach_alternative(html_message, "text/html")
        email.send()

class ConfirmationEmail(email.ConfirmationEmail):
    template_name = 'school_user/confirmation.html'

    def send(self, to, *args, **kwargs):
        context = self.get_context_data()
        html_message = render_to_string(self.template_name, context)
        plain_message = strip_tags(html_message)

        print("\n✅ Confirmation Email (HTML):\n", html_message)
        print("🧾 Confirmation Email (Plain Text):\n", plain_message)

        super().send(to, *args, **kwargs)


class PasswordResetEmail(email.PasswordResetEmail):
    template_name = 'school_user/password_reset.html'

    def send(self, to, *args, **kwargs):
        context = self.get_context_data()
        html_message = render_to_string(self.template_name, context)
        plain_message = strip_tags(html_message)

        print("\n🔒 Password Reset Email (HTML):\n", html_message)
        print("🗒️ Password Reset Email (Plain Text):\n", plain_message)

        super().send(to, *args, **kwargs)


class PasswordChangedConfirmationEmail(email.PasswordChangedConfirmationEmail):
    template_name = 'school_user/password_changed_confirmation.html'

    def send(self, to, *args, **kwargs):
        context = self.get_context_data()
        html_message = render_to_string(self.template_name, context)
        plain_message = strip_tags(html_message)

        print("\n🔐 Password Changed Confirmation Email (HTML):\n", html_message)
        print("📘 Password Changed Confirmation Email (Plain Text):\n", plain_message)

        super().send(to, *args, **kwargs)
