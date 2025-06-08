from django.contrib import admin
from .models import AudioFile, Tag, Like

@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_public', 'uploaded_at', 'views')
    list_filter = ('is_public', 'uploaded_at')
    search_fields = ('title', 'description', 'user__email')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'audio_file', 'is_liked', 'created_at')
    list_filter = ('is_liked', 'created_at')
