from django.contrib import admin
from .models import Task, Goal, TimeBlock, Note, Event, CalendarTask

admin.site.register(Task)
admin.site.register(Goal)
admin.site.register(TimeBlock)
admin.site.register(Note)
admin.site.register(Event)
admin.site.register(CalendarTask)