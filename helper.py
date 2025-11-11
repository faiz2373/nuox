import requests
from django.conf import settings
from portal.models import *
from django.template import loader
from portal.constant_ids import *
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
import pdb
import itertools

def HelperSendSMS(mobile_to, message, action, user):
    query = {'action':'sendsms', 'user':settings.SMS_USERNAME,'password':settings.SMS_PASSWORD,'from':'ELEMENT8','to':mobile_to,'text':message}
    response = requests.get('https://api.smsglobal.com/http-api.php', params=query)
       
    # sms_db=SMSLog()
    # sms_db.user= user
    # sms_db.mobile= mobile_to
    # sms_db.action= action
    # sms_db.status= response.text
    # sms_db.save()
    return True

def emailhelper(request, subject=None, template_id=None, contentreplace=None, to_email=None, action=None,cc=None):
    if template_id:
        mail_subject = subject
        email_content_template = EmailTemplate.objects.get(pk=template_id)
        # print(email_content_template.content,'@emailtempalte')
        templatecontent = email_content_template.content
        for k, v in contentreplace.items():
            if k == 'ENQUIRY':
                if v != None:
                    v =  '<p style="display:show;color: #242a38; font-family: Rubik, Helvetica Neue, Helvetica, Roboto, Arial, sans-serif; line-height: 20px; font-size: 13px; margin-top: 25px;">Enquiry : ' +v+ '</p>'
                    templatecontent = templatecontent.replace(k, v)
                else:
                    del v
            else:
                templatecontent = templatecontent.replace(k, v)
        html = templatecontent
        # print(html,'@emailtempalte')
        c_template = loader.get_template(
            'email-layout/common_email_layout.html')
        html_c_template = c_template.render({
        'content': html, }, request)
        html = html_c_template
        to_email = to_email
        if action == 'signup':
            from_mail = FROM_EMAIL
        else:
            from_mail = FROM_EMAIL
        if cc:
            cc = list(itertools.chain(*cc)) if cc else None
            msg = EmailMultiAlternatives(mail_subject, '', from_mail, [to_email[0]], cc=cc)
        else:
            msg = EmailMultiAlternatives(mail_subject, '', from_mail, [to_email])
        msg.attach_alternative(html, 'text/html')
        if msg.send(fail_silently=False):
            return True
        else:
            return False
    else:
        return False