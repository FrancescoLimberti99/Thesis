from django.contrib import admin
from .models import Artwork, ArtworkImage, Conversation

admin.site.register(Artwork)
admin.site.register(ArtworkImage)
admin.site.register(Conversation)
