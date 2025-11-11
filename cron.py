from datetime import *
from portal.models import *
from portal.task import WorkoutRemainderPushFCM



def daily_workout_remainder():
    print('---')
    tomorrow = date.today() + timedelta(days=1)
    tomorrow = tomorrow.strftime('%A')
    user_list = User.objects.all()
    for user in user_list:
        workout_list = Workout.objects.filter(user=user, day=tomorrow)
        for workout in workout_list:
            infos = {
                'type': 'Workout remainder',
                'action': 'remainder',
                'workout_id': workout.id,
            }
            Notification.objects.create(
                message="Time to Sweat it Out! Don't Miss Your " + workout.title + " Workout !",
                message_ar = "حان الوقت للتعرق! لا تفوت "+ workout.title +" التمرين!",
                info=infos,
                user_to=user,
                category='remainder'
            )
            remainder_data = {
                'user_id': user.id,
                'title': 'Workout Reminder',
                'message': "Time to Sweat it Out! Don't Miss Your " + workout.title + " Workout !",
                'message_ar': "حان الوقت للتعرق! لا تفوت "+ workout.title +" التمرين!",
                'info': {
                    'type': 'Workout remainder',
                    'action': 'remainder',
                    'workout_id': workout.id,
                    'user': user.id
                }
            }
            WorkoutRemainderPushFCM.delay(remainder_data)