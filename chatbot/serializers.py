from rest_framework import serializers
from .models import Artwork, ArtworkImage, Conversation

class ArtworkImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtworkImage
        fields = '__all__'

class ArtworkSerializer(serializers.ModelSerializer):
    images = ArtworkImageSerializer(many=True, read_only=True)

    class Meta:
        model = Artwork
        fields = '__all__'

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = '__all__'