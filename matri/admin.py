# admin.py
from django.contrib import admin
from .models import Profile, UserProfile, PartnerPreference, UserPost, InterestRequest # Add UserPost
from django.utils.html import mark_safe


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'gender', 'age', 'religion', 'is_profile_in_index')
    list_filter = ('gender', 'religion', 'category', 'marital_status', 'is_profile_in_index')
    search_fields = ('full_name', 'user__username', 'religion', 'category')
    readonly_fields = ('religion', 'category')

@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ('user_profile_name', 'caption_snippet', 'created_at', 'image_preview')
    list_filter = ('user_profile__user__username', 'created_at')
    search_fields = ('user_profile__full_name', 'user_profile__user__username', 'caption')
    readonly_fields = ('image_preview',)

    def user_profile_name(self, obj):
        return obj.user_profile.full_name or obj.user_profile.user.username
    user_profile_name.short_description = 'User'

    def caption_snippet(self, obj):
        return (obj.caption[:50] + '...') if obj.caption and len(obj.caption) > 50 else obj.caption
    caption_snippet.short_description = 'Caption'

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="100" height="auto" />')
        return "No Image"
    image_preview.short_description = 'Image'


admin.site.register(Profile)
# admin.site.register(UserProfile) # Already registered with custom admin
admin.site.register(PartnerPreference)
admin.site.register(InterestRequest)
# admin.site.register(UserPost) # Already registered with custom admin