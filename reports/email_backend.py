from django.core.mail.backends.smtp import EmailBackend

class HighPriorityEmailBackend(EmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            # Force the email client (Gmail, Outlook, Apple Mail) to flag it as important
            message.extra_headers['Importance'] = 'High'
            message.extra_headers['X-Priority'] = '1'
            message.extra_headers['X-MSMail-Priority'] = 'High'
            
        # Send the messages normally using Django's core SMTP engine
        return super().send_messages(email_messages)
