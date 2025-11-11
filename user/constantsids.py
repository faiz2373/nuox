def notification_msg_arabic(name,message):
    if message == 'like':
        return "أُعجب {0} بمشاركتك".format(name)
    elif message == 'comment':
        return "علق {0} على مشاركتك".format(name)
    elif message == 'follow':
        return "طلب {0} متابعتك".format(name)
    elif message == 'following':
        return "بدأ {0} في متابعتك".format(name)
    elif message == 'acceptfollowrequest':
        return "{0} قبل طلبك".format(name)
    elif message == 'helprequest_send':
        return "{} أرسل طلب مساعدة".format(name)
    elif message == 'helprequest_accepted':
        return "وافق {} على طلب المساعدة الخاص بك".format(name)
    elif message == 'gymconnection_request':
        return "أرسل {} استفسارًا".format(name)
    elif message == 'gym_joined':
        return "انضم {} إلى صالة الألعاب الرياضية الخاصة بك"
    
FOLLOW = 'يتبع'
FOLLOWING = 'التالي'
REQUESTED = 'مطلوب'

HR = 'ساعة' #hour
MIN = 'دقيقة' #minute
SEC = 'ثانية' #second

KG = 'كلغ'

HOUR_AGO = 'منذ ساعة'
MINUTE_AGO = 'منذ دقيقة'
HOURS_AGO = 'منذ ساعات'
MINUTES_AGO = 'دقائق مضت'
JUST_NOW = 'الآن'

month_translations_arabic = {
    "Jan": "يناير",
    "Feb": "فبراير",
    "Mar": "مارس",
    "Apr": "أبريل",
    "May": "مايو",
    "Jun": "يونيو",
    "Jul": "يوليو",
    "Aug": "أغسطس",
    "Sep": "سبتمبر",
    "Oct": "أكتوبر",
    "Nov": "نوفمبر",
    "Dec": "ديسمبر",
}

MONDAY = 'الاثنين'
TUESDAY = 'يوم الثلاثاء'
WEDNESDAY = 'الأربعاء'
THURSDAY = 'يوم الخميس'
FRIDAY = 'جمعة'
SATURDAY = 'السبت'
SUNDAY = 'الأحد'

#Sender and receiver do not belong to the same gym
SENDER_RECEIVER_MSG = 'المرسل والمتلقي لا ينتميان إلى نفس صالة الألعاب الرياضية'

#Sender and receiver are same
SENDER_RECEIVER_SAME = 'المرسل والمتلقي متماثلان'

#Sender does not have a gym
SENDER_NO_GYM = 'المرسل ليس لديه صالة رياضية'

#Recipient does not have a gym
RECEIVER_NO_GYM = 'ليس لدى المستلم صالة رياضية'

#Recipient not found
RECEIVER_NOT_FOUND = 'المستلم غير موجود'

#Male
MALE = 'ذكر'

#Female
FEMALE = 'أنثى'

#cm
CM = 'سم'

#ft
FT = 'قدم'

#lbs
LBS = 'رطل'

#Primary
PRIMARY = 'الأساسي'

#Secondary
SECONDARY = 'ثانوي'

#workout is in progress
WORKOUT_INPROGRESS = 'التمرين قيد التقدم'