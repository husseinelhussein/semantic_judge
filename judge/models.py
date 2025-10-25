from django.db import models

class Judgment(models.Model):
    # Store original and normalized forms for uniqueness
    sentence1 = models.TextField()
    sentence2 = models.TextField()
    sentence1_norm = models.TextField()  # normalized lower/trim
    sentence2_norm = models.TextField()
    similarity = models.FloatField()
    label = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # ensure no duplicates for semantically identical pair
        unique_together = (("sentence1_norm", "sentence2_norm"),)

    def __str__(self):
        return f"{self.label} ({self.similarity})"
