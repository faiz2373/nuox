import pdb
from portal.models import Notification
from user.constantsids import *

def notifications(user_from,user_to,message,message_ar,info,category,is_active,updated_at=None):
    notification = Notification()
    if user_from:
        notification.user_from = user_from
    if user_to:
        notification.user_to = user_to
    if message:
        notification.message = message
        notification.message_en = message
    if message_ar:
        notification.message_ar = message_ar
    if info:
        notification.info = info
    if category:
        notification.category = category
    if is_active == False:
        notification.is_active = is_active
    if is_active == True:
        notification.is_active = is_active
    if updated_at != None:
        notification.updated_at = updated_at
    notification.save()
    return notification

def translate_duration(duration_total,accepted_language):
    hours, remainder = divmod(duration_total, 3600)
    minutes, seconds = divmod(remainder, 60)

    # if int(seconds)/10 > 3:
    #     minutes = int(minutes)+1

    # if int(minutes)/10 > 3:
    #     hours = int(hours)+1

    if accepted_language == 'ar':
        if hours > 0:
            duration_str = f"{int(hours)} "+HR
        elif minutes > 0:
            duration_str = f"{int(minutes)} "+MIN
        else:
            duration_str = f"{int(seconds)} "+SEC
    else:
        if hours > 0:
            duration_str = f"{int(hours)} Hr"
        elif minutes > 0:
            duration_str = f"{int(minutes)} Min"
        else:
            duration_str = f"{int(seconds)} Sec"
    return duration_str

def translate_complete_duration(duration_total,accepted_language):
    hours, remainder = divmod(duration_total, 3600)
    minutes, seconds = divmod(remainder, 60)

    # if int(seconds)/10 > 3:
    #     minutes = int(minutes)+1

    # if int(minutes)/10 > 3:
    #     hours = int(hours)+1

    if accepted_language == 'ar':
        if hours > 0:
            duration_str = f"{int(hours)} "+HR+ f" {int(minutes)} "+MIN
        elif minutes > 0:
            duration_str = f"{int(minutes)} "+MIN+ f" {int(seconds)} "+SEC
        else:
            duration_str = f"{int(seconds)} "+SEC
    else:
        if hours > 0:
            duration_str = f"{int(hours)} Hrs {int(minutes)} min"
        elif minutes > 0:
            duration_str = f"{int(minutes)} Mins {int(seconds)} sec"
        else:
            duration_str = f"{int(seconds)} Sec"
    return duration_str

def translate_day(day):
    if day == 'Monday':
        return MONDAY
    elif day == 'Tuesday':
        return TUESDAY
    elif day == 'Wednesday':
        return WEDNESDAY
    elif day == 'Thursday':
        return THURSDAY
    elif day == 'Friday':
        return FRIDAY
    elif day == 'Saturday':
        return SATURDAY
    elif day == 'Sunday':
        return SUNDAY

def translate_date(date):
    abbreviated_month = date.split()[1]
    translated_month = month_translations_arabic.get(abbreviated_month, abbreviated_month)
    translated_date_string = date.replace(abbreviated_month, translated_month)
    return translated_date_string

def translate_timebefore(attr,current_time,accepted_language):
    if attr:
        if accepted_language == 'ar':
            if attr.created_at.strftime("%Y-%m-%d") == current_time.strftime("%Y-%m-%d"):
                difference = current_time-attr.created_at  
                hours = difference.days * 24 + difference.seconds // 3600
                minutes = (difference.seconds % 3600) // 60
                if difference.days == 0 and hours == 1:
                    return "قبل {0} ساعة".format(hours) #hour ago
                elif difference.days == 0 and hours >= 1:
                    return "قبل {0} ساعة".format(hours) #hours ago
                elif difference.days == 0 and hours < 1 and minutes == 1:
                    return "قبل {0} دقيقة".format(minutes) 
                elif difference.days == 0 and hours < 1 and minutes != 0:
                    return "قبل {0} دقيقة".format(minutes) 
                elif difference.days == 0 and hours == 0 and minutes == 0:
                    return "الآن"
                else:
                    return translate_date(attr.created_at.strftime("%d %b %Y"))
            else:
                return translate_date(attr.created_at.strftime("%d %b %Y"))
        else:
            if attr.created_at.strftime("%Y-%m-%d") == current_time.strftime("%Y-%m-%d"):
                difference = current_time-attr.created_at  
                hours = difference.days * 24 + difference.seconds // 3600
                minutes = (difference.seconds % 3600) // 60
                if difference.days == 0 and hours == 1:
                    return "{0} hour ago".format(hours) 
                elif difference.days == 0 and hours >= 1:
                    return "{0} hours ago".format(hours) 
                elif difference.days == 0 and hours < 1 and minutes == 1:
                    return "{0} minute ago".format(minutes) 
                elif difference.days == 0 and hours < 1 and minutes != 0:
                    return "{0} minutes ago".format(minutes) 
                elif difference.days == 0 and hours == 0 and minutes == 0:
                    return "Just now"
                else:
                    return attr.created_at.strftime("%d %b %Y")
            else:
                return attr.created_at.strftime("%d %b %Y")
            
def process_set_data(request_data_set):
    rcrds_reps = 0.0
    rcrds_weight = 0.0
    for set_data in request_data_set:
        rcrds_reps += float(set_data['reps'])
        rcrds_weight += float(set_data['weight'])
        # if reps_value in reps_dict:
        #     rcrds_reps += reps_value
        # if weight_value in weights_dict:
        #     rcrds_weight += weight_value
    # rcrds_reps = sum(reps_dict.get(set_data['reps'], 0) for set_data in request_data_set)
    # rcrds_weight = sum(weights_dict.get(set_data['weight'], 0) for set_data in request_data_set)
    return rcrds_reps, rcrds_weight


def convert_float_values(value):
    return float(f"{value:.2f}")