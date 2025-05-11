from djoser import email


class ActivationEmail(email.ActivationEmail):
    template_name = 'school_user/activation.html'


class ConfirmationEmail(email.ConfirmationEmail):
    template_name = 'school_user/confirmation.html'


class PasswordResetEmail(email.PasswordResetEmail):
    template_name = 'school_user/password_reset.html'


class PasswordChangedConfirmationEmail(email.PasswordChangedConfirmationEmail):
    template_name = 'school_user/password_changed_confirmation.html'