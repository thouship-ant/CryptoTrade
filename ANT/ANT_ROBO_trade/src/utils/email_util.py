import smtplib
import config

def email_alert(to, subject, body):
    lst_to = [to]
    email_text = """\
    From: %s
    To: %s
    MIME-Version:1.0
    Content-type:text/html
    Subject: %s

    %s
    """ % (config.SUPPORT_EMAIL, ", ".join(lst_to), subject, body)

    try:
        smtp_server = smtplib.SMTP(config.SMTP_HOSTNAME, config.SMTP_PORT)
        smtp_server.starttls()
        smtp_server.login(config.SUPPORT_EMAIL, config.SUPPORT_PWD)
        smtp_server.sendmail(config.SUPPORT_EMAIL, lst_to, email_text)
        smtp_server.close()
        print("Email sent successfully!")
    except Exception as ex:
        print("Something went wrong….", ex)


if __name__ == "__main__":
    to = 'mdthouship1988@gmail.com'
    subject = 'ANT Test email'
    body = '<h1>Ant test</h1>'
    email_alert(to, subject, body)
