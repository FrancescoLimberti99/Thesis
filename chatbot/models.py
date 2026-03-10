from django.db import models

class Artwork(models.Model):
    name = models.CharField(max_length=200)
    period = models.CharField(max_length=100)
    author = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    style = models.CharField(max_length=100)
    context = models.TextField()
    aliases = models.TextField(blank=True, default='')
    embedding = models.BinaryField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.author}"

class ArtworkImage(models.Model):
    artwork = models.ForeignKey(Artwork, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='artworks/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.artwork.name} - immagine {self.id}"
    
class Conversation(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    input_text = models.TextField(null=True, blank=True)
    input_image = models.ImageField(upload_to='chat/', null=True, blank=True)
    recognized_artwork = models.CharField(max_length=200)
    similarity_score = models.FloatField()
    model_response = models.TextField()

    def __str__(self):
        return f"{self.timestamp} - {self.recognized_artwork}"
