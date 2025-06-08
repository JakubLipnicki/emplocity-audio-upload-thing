from django.contrib import admin
from .models import Comment

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'audio_file_id', 'content', 'created_at')
    search_fields = ('user__email', 'content')
    list_filter = ('created_at',)
